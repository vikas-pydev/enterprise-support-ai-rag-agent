"""Controlled Tool-Calling Agent Foundation with Multi-Turn Conversational Memory, Reliability & Observability.

Implements an explicit, transparent agent loop that coordinates LLM tool selection,
argument validation, safe execution against approved LangChain tools, tool execution timing,
duplicate call protection, structured execution tracing, conversational session memory,
and grounded final answer synthesis.
"""

import json
import logging
import time
from typing import Any
from pydantic import BaseModel, Field
from openai import OpenAI
from langchain_core.utils.function_calling import convert_to_openai_tool

from app.config import LLM_MODEL
from app.llm import client as default_client
from app.tools import ALL_TOOLS
from app.agent.prompts import AGENT_SYSTEM_PROMPT
from app.agent.memory import InMemorySessionStore, default_session_store

logger = logging.getLogger(__name__)

# Derive tool registry and OpenAPI tool schemas dynamically from ALL_TOOLS
TOOLS_BY_NAME = {tool.name: tool for tool in ALL_TOOLS}
OPENAI_TOOL_SCHEMAS = [convert_to_openai_tool(t) for t in ALL_TOOLS]

DEFAULT_AGENT_MODEL = LLM_MODEL
MAX_AGENT_STEPS = 5


class AgentStep(BaseModel):
    """Represents a single tool invocation step within an agent execution."""

    step_number: int = 1
    tool_name: str
    tool_args: dict[str, Any] = Field(default_factory=dict)
    tool_result: dict[str, Any] = Field(default_factory=dict)
    status: str = "success"  # "success", "error", "rejected_duplicate"
    duration_ms: float = 0.0
    error: str | None = None


class AgentExecutionTrace(BaseModel):
    """Detailed structured trace of the agent execution lifecycle for observability and debugging."""

    session_id: str | None = None
    query: str
    total_steps: int = 0
    total_duration_ms: float = 0.0
    used_rag: bool = False
    status: str = "completed"  # "completed", "max_steps_reached", "error"
    tools_invoked: list[str] = Field(default_factory=list)
    steps: list[AgentStep] = Field(default_factory=list)


class AgentResponse(BaseModel):
    """Standardized response produced by the agent execution loop."""

    session_id: str | None = None
    query: str
    final_answer: str
    steps: list[AgentStep] = Field(default_factory=list)
    total_steps: int = 0
    duration_ms: float = 0.0
    status: str = "completed"  # "completed", "max_steps_reached", "error"
    used_rag: bool = False
    citations: list[dict[str, Any]] = Field(default_factory=list)
    trace: AgentExecutionTrace | None = None


def _extract_citations(steps: list[AgentStep]) -> list[dict[str, Any]]:
    """Extracts and deduplicates source citations produced by policy tools in agent steps."""
    citations: list[dict[str, Any]] = []
    seen_chunk_uids: set[str] = set()

    for step in steps:
        if step.tool_name == "ask_policy" and isinstance(step.tool_result, dict):
            sources = step.tool_result.get("sources", [])
            if isinstance(sources, list):
                for src in sources:
                    if isinstance(src, dict):
                        chunk_uid = src.get("chunk_uid")
                        if chunk_uid and chunk_uid not in seen_chunk_uids:
                            seen_chunk_uids.add(chunk_uid)
                            citations.append(src)
                        elif not chunk_uid:
                            citations.append(src)
    return citations


def _execute_tool_call(
    tool_name: str,
    raw_arguments: str | dict[str, Any],
    step_number: int = 1,
) -> tuple[dict[str, Any], dict[str, Any], AgentStep]:
    """Validates and executes a requested tool against the approved tool registry with timing.

    Returns:
        tuple of (validated_arguments, execution_result, agent_step)
    """
    t_start = time.perf_counter()

    # 1. Verify tool exists in allowlist
    if tool_name not in TOOLS_BY_NAME:
        duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
        err_msg = f"Tool '{tool_name}' is not recognized or permitted."
        error_result = {
            "error": err_msg,
            "status": "error",
            "found": False,
        }
        step = AgentStep(
            step_number=step_number,
            tool_name=tool_name,
            tool_args={},
            tool_result=error_result,
            status="error",
            duration_ms=duration_ms,
            error=err_msg,
        )
        return ({}, error_result, step)

    tool = TOOLS_BY_NAME[tool_name]

    # 2. Parse arguments
    if isinstance(raw_arguments, str):
        try:
            parsed_args = json.loads(raw_arguments) if raw_arguments.strip() else {}
        except Exception as e:
            duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
            err_msg = f"Failed to parse tool arguments as JSON: {str(e)}"
            error_result = {
                "error": err_msg,
                "status": "error",
                "found": False,
            }
            step = AgentStep(
                step_number=step_number,
                tool_name=tool_name,
                tool_args={},
                tool_result=error_result,
                status="error",
                duration_ms=duration_ms,
                error=err_msg,
            )
            return ({}, error_result, step)
    elif isinstance(raw_arguments, dict):
        parsed_args = raw_arguments
    else:
        parsed_args = {}

    # 3. Validate arguments against Pydantic schema
    if tool.args_schema is not None:
        try:
            validated_model = tool.args_schema(**parsed_args)
            validated_args = validated_model.model_dump()
        except Exception as e:
            duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
            err_msg = f"Invalid tool arguments provided for '{tool_name}': {str(e)}"
            error_result = {
                "error": err_msg,
                "status": "error",
                "found": False,
            }
            step = AgentStep(
                step_number=step_number,
                tool_name=tool_name,
                tool_args=parsed_args if isinstance(parsed_args, dict) else {},
                tool_result=error_result,
                status="error",
                duration_ms=duration_ms,
                error=err_msg,
            )
            return (parsed_args, error_result, step)
    else:
        validated_args = parsed_args

    # 4. Execute tool safely with timing
    try:
        result = tool.invoke(validated_args)
        duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
        if not isinstance(result, dict):
            result = {"result": result}

        # Check if the tool returned an error dictionary
        is_error = result.get("status") == "error" or ("error" in result and not result.get("found", True))
        step_status = "error" if is_error else "success"
        step_error = result.get("error") if is_error else None

        step = AgentStep(
            step_number=step_number,
            tool_name=tool_name,
            tool_args=validated_args,
            tool_result=result,
            status=step_status,
            duration_ms=duration_ms,
            error=step_error,
        )
        return (validated_args, result, step)
    except Exception as e:
        duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
        logger.error("Execution error in tool '%s': %s", tool_name, e)
        err_msg = f"Tool execution failed for '{tool_name}'."
        error_result = {
            "error": err_msg,
            "status": "error",
            "found": False,
        }
        step = AgentStep(
            step_number=step_number,
            tool_name=tool_name,
            tool_args=validated_args,
            tool_result=error_result,
            status="error",
            duration_ms=duration_ms,
            error=err_msg,
        )
        return (validated_args, error_result, step)


def _build_agent_response(
    clean_session_id: str | None,
    clean_query: str,
    final_answer: str,
    steps: list[AgentStep],
    status: str,
    start_time: float,
) -> AgentResponse:
    """Constructs a fully populated AgentResponse and associated AgentExecutionTrace."""
    total_duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    used_rag = any(s.tool_name == "ask_policy" for s in steps)
    citations = _extract_citations(steps)
    tools_invoked = [s.tool_name for s in steps]

    trace = AgentExecutionTrace(
        session_id=clean_session_id,
        query=clean_query,
        total_steps=len(steps),
        total_duration_ms=total_duration_ms,
        used_rag=used_rag,
        status=status,
        tools_invoked=tools_invoked,
        steps=steps,
    )

    logger.info(
        "Agent run finished | session_id=%s | status=%s | steps=%d | used_rag=%s | duration_ms=%.2f",
        clean_session_id,
        status,
        len(steps),
        used_rag,
        total_duration_ms,
    )

    return AgentResponse(
        session_id=clean_session_id,
        query=clean_query,
        final_answer=final_answer,
        steps=steps,
        total_steps=len(steps),
        duration_ms=total_duration_ms,
        status=status,
        used_rag=used_rag,
        citations=citations,
        trace=trace,
    )


def run_agent(
    user_query: str,
    session_id: str | None = None,
    session_store: InMemorySessionStore | None = None,
    max_steps: int = MAX_AGENT_STEPS,
    model: str = DEFAULT_AGENT_MODEL,
    client: OpenAI | None = None,
    system_prompt: str = AGENT_SYSTEM_PROMPT,
) -> AgentResponse:
    """Executes a transparent, reliable, multi-turn tool-calling agent loop.

    Args:
        user_query: The natural language question or instruction from the user.
        session_id: Optional unique identifier for multi-turn session tracking.
        session_store: Optional session store instance (defaults to default_session_store).
        max_steps: Maximum tool iteration cycles before terminating.
        model: The LLM model identifier supporting native OpenAI tool calling.
        client: Optional OpenAI client instance (defaults to preconfigured Groq client).
        system_prompt: System prompt defining agent behavior and routing rules.

    Returns:
        AgentResponse containing the final answer, step history, citations, timing, and trace.
    """
    start_time = time.perf_counter()

    clean_session_id = str(session_id).strip() if session_id is not None else None
    if clean_session_id == "":
        clean_session_id = None

    if not user_query or not str(user_query).strip():
        return _build_agent_response(
            clean_session_id=clean_session_id,
            clean_query=user_query,
            final_answer="Please provide a valid question or request.",
            steps=[],
            status="completed",
            start_time=start_time,
        )

    llm_client = client or default_client
    clean_query = str(user_query).strip()

    logger.info("Agent run started | session_id=%s | query=%s", clean_session_id, clean_query[:80])

    # Resolve session store and conversation history
    store = session_store or default_session_store
    history_messages: list[dict[str, Any]] = []
    if clean_session_id:
        history_messages = store.get_session(clean_session_id)

    # Construct conversation payload for the LLM
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
    ]
    messages.extend(history_messages)
    messages.append({"role": "user", "content": clean_query})

    # Track newly generated messages for this turn
    turn_messages: list[dict[str, Any]] = [
        {"role": "user", "content": clean_query},
    ]

    steps: list[AgentStep] = []
    # In-run cache of executed tool calls for duplicate protection: (tool_name, serialized_args) -> tool_result
    executed_calls: dict[tuple[str, str], dict[str, Any]] = {}

    for step_idx in range(max_steps):
        try:
            response = llm_client.chat.completions.create(
                model=model,
                messages=messages,
                tools=OPENAI_TOOL_SCHEMAS,
                tool_choice="auto",
            )
        except Exception as e:
            logger.error("LLM call failed at step %d: %s", step_idx + 1, e)
            return _build_agent_response(
                clean_session_id=clean_session_id,
                clean_query=clean_query,
                final_answer="An error occurred while contacting the language model service.",
                steps=steps,
                status="error",
                start_time=start_time,
            )

        if not response or not getattr(response, "choices", None):
            logger.error("LLM returned empty or malformed completion response at step %d", step_idx + 1)
            return _build_agent_response(
                clean_session_id=clean_session_id,
                clean_query=clean_query,
                final_answer="An error occurred while contacting the language model service.",
                steps=steps,
                status="error",
                start_time=start_time,
            )

        choice = response.choices[0]
        message = choice.message

        # Check if the LLM made any tool calls
        tool_calls = getattr(message, "tool_calls", None)

        if not tool_calls:
            # Final text response reached
            final_text = (message.content or "").strip()
            turn_messages.append({"role": "assistant", "content": final_text})

            # Save turn to session store if session is active
            if clean_session_id:
                store.append_messages(clean_session_id, turn_messages)

            return _build_agent_response(
                clean_session_id=clean_session_id,
                clean_query=clean_query,
                final_answer=final_text,
                steps=steps,
                status="completed",
                start_time=start_time,
            )

        # Log LLM tool decision
        logger.info(
            "LLM decision at step %d | tool_calls=%s",
            step_idx + 1,
            [getattr(getattr(tc, "function", None), "name", "unknown") for tc in tool_calls],
        )

        # Record assistant tool-call message in conversation history
        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                {
                    "id": getattr(tc, "id", f"call_{i}"),
                    "type": "function",
                    "function": {
                        "name": getattr(getattr(tc, "function", None), "name", ""),
                        "arguments": getattr(getattr(tc, "function", None), "arguments", "{}"),
                    },
                }
                for i, tc in enumerate(tool_calls)
            ],
        }
        messages.append(assistant_msg)
        turn_messages.append(assistant_msg)

        # Execute each requested tool call
        for tc in tool_calls:
            step_num = len(steps) + 1
            tool_name = getattr(getattr(tc, "function", None), "name", "") or ""
            raw_args = getattr(getattr(tc, "function", None), "arguments", "{}") or "{}"
            call_id = getattr(tc, "id", None) or f"call_{step_num}"

            # Parse args for canonical duplicate-checking key
            if isinstance(raw_args, str):
                try:
                    parsed_args = json.loads(raw_args) if raw_args.strip() else {}
                except Exception:
                    parsed_args = {}
            elif isinstance(raw_args, dict):
                parsed_args = raw_args
            else:
                parsed_args = {}

            call_key = (tool_name, json.dumps(parsed_args, sort_keys=True, default=str))

            # Check duplicate tool call protection
            if call_key in executed_calls and tool_name in TOOLS_BY_NAME:
                previous_result = executed_calls[call_key]
                dup_result = {
                    "status": "duplicate_rejected",
                    "message": (
                        f"Tool '{tool_name}' with identical arguments was already executed in this session. "
                        "Use the prior observation to formulate your answer or select a different tool."
                    ),
                    "previous_result": previous_result,
                }
                step = AgentStep(
                    step_number=step_num,
                    tool_name=tool_name,
                    tool_args=parsed_args,
                    tool_result=dup_result,
                    status="rejected_duplicate",
                    duration_ms=0.0,
                    error="Duplicate tool call rejected.",
                )
                steps.append(step)
                logger.info("Duplicate tool call rejected | step=%d | tool=%s", step_num, tool_name)

                tool_obs_msg = {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps(dup_result),
                }
                messages.append(tool_obs_msg)
                turn_messages.append(tool_obs_msg)
                continue

            # Execute tool call
            val_args, tool_result, step = _execute_tool_call(tool_name, raw_args, step_number=step_num)
            steps.append(step)

            if tool_name in TOOLS_BY_NAME:
                executed_calls[call_key] = tool_result

            logger.info(
                "Tool executed | step=%d | tool=%s | status=%s | duration_ms=%.2f",
                step_num,
                tool_name,
                step.status,
                step.duration_ms,
            )

            # Append tool observation message
            tool_obs_msg = {
                "role": "tool",
                "tool_call_id": call_id,
                "content": json.dumps(tool_result),
            }
            messages.append(tool_obs_msg)
            turn_messages.append(tool_obs_msg)

    # If max_steps reached without final text, generate synthesis with tool observations
    try:
        final_response = llm_client.chat.completions.create(
            model=model,
            messages=messages
            + [
                {
                    "role": "user",
                    "content": (
                        "Maximum tool steps reached. Based on the gathered tool observations above, "
                        "synthesize your final concise answer to the original question."
                    ),
                }
            ],
        )
        final_text = (final_response.choices[0].message.content or "Maximum tool steps reached.").strip()
        turn_messages.append({"role": "assistant", "content": final_text})

        if clean_session_id:
            store.append_messages(clean_session_id, turn_messages)

        return _build_agent_response(
            clean_session_id=clean_session_id,
            clean_query=clean_query,
            final_answer=final_text,
            steps=steps,
            status="max_steps_reached",
            start_time=start_time,
        )
    except Exception:
        fallback_text = "The agent reached the maximum step limit before completing the request."
        turn_messages.append({"role": "assistant", "content": fallback_text})

        if clean_session_id:
            store.append_messages(clean_session_id, turn_messages)

        return _build_agent_response(
            clean_session_id=clean_session_id,
            clean_query=clean_query,
            final_answer=fallback_text,
            steps=steps,
            status="max_steps_reached",
            start_time=start_time,
        )
