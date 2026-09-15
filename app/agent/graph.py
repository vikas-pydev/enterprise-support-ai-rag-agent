"""LangGraph Single-Agent Graph Implementation for Enterprise Support AI Agent.

Migrates the explicit tool-calling execution loop into a stateful, conditional
execution graph using LangGraph. Preserves all safety boundaries, allowlists,
Pydantic validation, duplicate tool protection, monotonic execution timing,
and structured execution tracing.
"""

import json
import logging
import time
from typing import Any, TypedDict
from openai import OpenAI
from langgraph.graph import StateGraph, START, END

from app.llm import client as default_client
from app.tools import ALL_TOOLS
from app.agent.prompts import AGENT_SYSTEM_PROMPT
from app.agent.memory import InMemorySessionStore, default_session_store
from app.agent.agent import (
    TOOLS_BY_NAME,
    OPENAI_TOOL_SCHEMAS,
    DEFAULT_AGENT_MODEL,
    MAX_AGENT_STEPS,
    AgentStep,
    AgentExecutionTrace,
    AgentResponse,
    _extract_citations,
    _execute_tool_call,
)

logger = logging.getLogger(__name__)


class AgentGraphState(TypedDict, total=False):
    """Explicit typed state schema representing the complete lifecycle of a graph run.

    Fields:
        session_id: Optional unique identifier for multi-turn session tracking.
        query: The cleaned user input query.
        system_prompt: System instructions governing tool routing and behavior.
        model: LLM model identifier.
        client: OpenAI/Groq API client instance.
        messages: Chronological message payload sent to the LLM.
        turn_messages: New messages produced in the current user turn.
        steps: List of AgentStep records capturing tool executions, timing, and errors.
        step_count: Number of tool iterations executed so far.
        max_steps: Step budget limit to prevent infinite execution cycles.
        executed_calls: Set or dict mapping (tool_name, serialized_args) to cached observations for duplicate protection.
        pending_tool_calls: List of raw tool calls requested by the LLM in the current step.
        final_answer: Synthesized final response text.
        status: Execution status ('completed', 'max_steps_reached', 'error').
        duration_ms: Total elapsed execution time in milliseconds.
        used_rag: Boolean flag indicating if policy retrieval was executed.
        citations: List of deduplicated RAG source citations.
        error: Optional error message string.
        start_time: Monotonic start timestamp (time.perf_counter).
    """

    session_id: str | None
    query: str
    system_prompt: str
    model: str
    client: Any
    messages: list[dict[str, Any]]
    turn_messages: list[dict[str, Any]]
    steps: list[AgentStep]
    step_count: int
    max_steps: int
    executed_calls: dict[tuple[str, str], dict[str, Any]]
    pending_tool_calls: list[dict[str, Any]]
    final_answer: str
    status: str
    duration_ms: float
    used_rag: bool
    citations: list[dict[str, Any]]
    error: str | None
    start_time: float


def llm_node(state: AgentGraphState) -> dict[str, Any]:
    """Invokes the tool-calling LLM with current graph conversation state.

    Determines whether the model generated a final text response or requested tool calls.
    """
    client: OpenAI = state.get("client") or default_client
    model = state.get("model", DEFAULT_AGENT_MODEL)
    messages = list(state.get("messages", []))
    step_num = state.get("step_count", 0) + 1

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=OPENAI_TOOL_SCHEMAS,
            tool_choice="auto",
        )
    except Exception as e:
        logger.error("LLM node invocation failed at step %d: %s", step_num, e)
        return {
            "status": "error",
            "error": "An error occurred while contacting the language model service.",
            "final_answer": "An error occurred while contacting the language model service.",
            "pending_tool_calls": [],
        }

    if not response or not getattr(response, "choices", None):
        logger.error("LLM returned empty or malformed completion response in graph at step %d", step_num)
        return {
            "status": "error",
            "error": "Empty or malformed completion response.",
            "final_answer": "An error occurred while contacting the language model service.",
            "pending_tool_calls": [],
        }

    choice = response.choices[0]
    message = choice.message
    tool_calls = getattr(message, "tool_calls", None)

    if not tool_calls:
        # Final text response
        final_text = (message.content or "").strip()
        updated_turn_msgs = list(state.get("turn_messages", [])) + [{"role": "assistant", "content": final_text}]
        logger.info("LLM node produced final text answer in graph at step %d", step_num)
        return {
            "final_answer": final_text,
            "status": "completed",
            "pending_tool_calls": [],
            "turn_messages": updated_turn_msgs,
        }

    # Model emitted tool call(s)
    tool_names = [getattr(getattr(tc, "function", None), "name", "unknown") for tc in tool_calls]
    logger.info("LLM node requested tool calls in graph at step %d: %s", step_num, tool_names)

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

    updated_messages = list(messages) + [assistant_msg]
    updated_turn_msgs = list(state.get("turn_messages", [])) + [assistant_msg]

    raw_tool_calls = [
        {
            "id": getattr(tc, "id", f"call_{i}"),
            "name": getattr(getattr(tc, "function", None), "name", ""),
            "arguments": getattr(getattr(tc, "function", None), "arguments", "{}"),
        }
        for i, tc in enumerate(tool_calls)
    ]

    return {
        "messages": updated_messages,
        "turn_messages": updated_turn_msgs,
        "pending_tool_calls": raw_tool_calls,
        "status": "running",
    }



def tool_node(state: AgentGraphState) -> dict[str, Any]:
    """Executes requested tool calls with validation, duplicate protection, and timing.

    Appends structured tool observation messages to the conversation state.
    """
    pending_tool_calls = state.get("pending_tool_calls", [])
    current_steps = list(state.get("steps", []))
    executed_calls = dict(state.get("executed_calls", {}))
    messages = list(state.get("messages", []))
    turn_messages = list(state.get("turn_messages", []))

    for tc in pending_tool_calls:
        step_num = len(current_steps) + 1
        tool_name = tc.get("name", "") or ""
        raw_args = tc.get("arguments", "{}") or "{}"
        call_id = tc.get("id") or f"call_{step_num}"

        # Parse arguments for duplicate checking
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
            current_steps.append(step)
            logger.info("Graph tool node: duplicate tool call rejected | step=%d | tool=%s", step_num, tool_name)

            tool_obs_msg = {
                "role": "tool",
                "tool_call_id": call_id,
                "content": json.dumps(dup_result),
            }
            messages.append(tool_obs_msg)
            turn_messages.append(tool_obs_msg)
            continue

        # Execute tool call safely
        val_args, tool_result, step = _execute_tool_call(tool_name, raw_args, step_number=step_num)
        current_steps.append(step)

        if tool_name in TOOLS_BY_NAME:
            executed_calls[call_key] = tool_result

        logger.info(
            "Graph tool node: executed tool | step=%d | tool=%s | status=%s | duration_ms=%.2f",
            step_num,
            tool_name,
            step.status,
            step.duration_ms,
        )

        tool_obs_msg = {
            "role": "tool",
            "tool_call_id": call_id,
            "content": json.dumps(tool_result),
        }
        messages.append(tool_obs_msg)
        turn_messages.append(tool_obs_msg)

    used_rag = any(s.tool_name == "ask_policy" for s in current_steps)
    new_step_count = state.get("step_count", 0) + 1

    return {
        "messages": messages,
        "turn_messages": turn_messages,
        "steps": current_steps,
        "step_count": new_step_count,
        "executed_calls": executed_calls,
        "pending_tool_calls": [],
        "used_rag": used_rag,
    }


def max_steps_node(state: AgentGraphState) -> dict[str, Any]:
    """Synthesizes a final response when the maximum agent step limit is reached."""
    client: OpenAI = state.get("client") or default_client
    model = state.get("model", DEFAULT_AGENT_MODEL)
    messages = list(state.get("messages", []))
    turn_messages = list(state.get("turn_messages", []))

    logger.warning("Graph max_steps_node reached | step_count=%d", state.get("step_count", 0))

    try:
        synthesis_prompt = {
            "role": "user",
            "content": (
                "Maximum tool steps reached. Based on the gathered tool observations above, "
                "synthesize your final concise answer to the original question."
            ),
        }
        final_response = client.chat.completions.create(
            model=model,
            messages=messages + [synthesis_prompt],
        )
        final_text = (final_response.choices[0].message.content or "Maximum tool steps reached.").strip()
    except Exception:
        final_text = "The agent reached the maximum step limit before completing the request."

    turn_messages.append({"role": "assistant", "content": final_text})

    return {
        "final_answer": final_text,
        "status": "max_steps_reached",
        "turn_messages": turn_messages,
        "pending_tool_calls": [],
    }


def route_after_llm(state: AgentGraphState) -> str:
    """Conditional routing edge determining next node after LLM execution.

    Routes to:
        - END if error occurred or final answer was reached
        - 'max_steps' if step budget is exhausted
        - 'tools' if pending tool calls exist
    """
    if state.get("status") in ("error", "completed") or state.get("final_answer"):
        return END

    pending_calls = state.get("pending_tool_calls") or []
    if pending_calls:
        step_count = state.get("step_count") or 0
        max_steps = state.get("max_steps") or MAX_AGENT_STEPS
        if step_count >= max_steps:
            return "max_steps"
        return "tools"

    return END


def route_after_tools(state: AgentGraphState) -> str:
    """Conditional routing edge determining next node after Tool execution.

    Routes to:
        - 'max_steps' if step count reaches or exceeds max_steps
        - 'llm' to continue conversation loop
    """
    step_count = state.get("step_count") or 0
    max_steps = state.get("max_steps") or MAX_AGENT_STEPS
    if step_count >= max_steps:
        return "max_steps"
    return "llm"


def create_agent_graph():
    """Builds and compiles the single-agent LangGraph workflow.

    Returns:
        Compiled StateGraph instance ready for invocation.
    """
    workflow = StateGraph(AgentGraphState)

    # 1. Add graph nodes
    workflow.add_node("llm", llm_node)
    workflow.add_node("tools", tool_node)
    workflow.add_node("max_steps", max_steps_node)

    # 2. Define edges & entry point
    workflow.add_edge(START, "llm")
    workflow.add_conditional_edges(
        "llm",
        route_after_llm,
        {
            "tools": "tools",
            "max_steps": "max_steps",
            END: END,
        },
    )
    workflow.add_conditional_edges(
        "tools",
        route_after_tools,
        {
            "llm": "llm",
            "max_steps": "max_steps",
        },
    )
    workflow.add_edge("max_steps", END)

    return workflow.compile()


# Global precompiled graph instance for standard use
compiled_agent_graph = create_agent_graph()


def run_graph_agent(
    user_query: str,
    session_id: str | None = None,
    session_store: InMemorySessionStore | None = None,
    max_steps: int = MAX_AGENT_STEPS,
    model: str = DEFAULT_AGENT_MODEL,
    client: OpenAI | None = None,
    system_prompt: str = AGENT_SYSTEM_PROMPT,
    graph: Any | None = None,
) -> AgentResponse:
    """Executes the single-agent LangGraph workflow with session memory and structured tracing.

    Args:
        user_query: The natural language question or request from the user.
        session_id: Optional unique identifier for multi-turn session tracking.
        session_store: Optional session store instance (defaults to default_session_store).
        max_steps: Maximum tool iteration cycles before terminating.
        model: The LLM model identifier supporting native OpenAI tool calling.
        client: Optional OpenAI client instance (defaults to preconfigured Groq client).
        system_prompt: System prompt defining agent behavior and routing rules.
        graph: Optional compiled LangGraph instance (defaults to compiled_agent_graph).

    Returns:
        AgentResponse containing the final answer, step history, citations, timing, and trace.
    """
    start_time = time.perf_counter()

    clean_session_id = str(session_id).strip() if session_id is not None else None
    if clean_session_id == "":
        clean_session_id = None

    if not user_query or not str(user_query).strip():
        trace = AgentExecutionTrace(
            session_id=clean_session_id,
            query=user_query,
            total_steps=0,
            total_duration_ms=0.0,
            used_rag=False,
            status="completed",
            tools_invoked=[],
            steps=[],
        )
        return AgentResponse(
            session_id=clean_session_id,
            query=user_query,
            final_answer="Please provide a valid question or request.",
            steps=[],
            total_steps=0,
            duration_ms=0.0,
            status="completed",
            used_rag=False,
            citations=[],
            trace=trace,
        )

    llm_client = client or default_client
    clean_query = str(user_query).strip()

    logger.info("LangGraph agent run started | session_id=%s | query=%s", clean_session_id, clean_query[:80])

    # Resolve session store and conversation history
    store = session_store or default_session_store
    history_messages: list[dict[str, Any]] = []
    if clean_session_id:
        history_messages = store.get_session(clean_session_id)

    # Construct conversation payload for the LLM
    initial_messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
    ]
    initial_messages.extend(history_messages)
    initial_messages.append({"role": "user", "content": clean_query})

    initial_turn_messages: list[dict[str, Any]] = [
        {"role": "user", "content": clean_query},
    ]

    initial_state: AgentGraphState = {
        "session_id": clean_session_id,
        "query": clean_query,
        "system_prompt": system_prompt,
        "model": model,
        "client": llm_client,
        "messages": initial_messages,
        "turn_messages": initial_turn_messages,
        "steps": [],
        "step_count": 0,
        "max_steps": max_steps,
        "executed_calls": {},
        "pending_tool_calls": [],
        "final_answer": "",
        "status": "running",
        "duration_ms": 0.0,
        "used_rag": False,
        "citations": [],
        "error": None,
        "start_time": start_time,
    }

    runner_graph = graph or compiled_agent_graph

    try:
        final_state = runner_graph.invoke(initial_state)
    except Exception as e:
        logger.error("LangGraph execution encountered an unhandled exception: %s", e)
        total_duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        err_msg = "An error occurred while executing the agent graph."
        trace = AgentExecutionTrace(
            session_id=clean_session_id,
            query=clean_query,
            total_steps=0,
            total_duration_ms=total_duration_ms,
            used_rag=False,
            status="error",
            tools_invoked=[],
            steps=[],
        )
        return AgentResponse(
            session_id=clean_session_id,
            query=clean_query,
            final_answer=err_msg,
            steps=[],
            total_steps=0,
            duration_ms=total_duration_ms,
            status="error",
            used_rag=False,
            citations=[],
            trace=trace,
        )

    total_duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    final_steps: list[AgentStep] = final_state.get("steps", [])
    final_answer: str = final_state.get("final_answer", "")
    final_status: str = final_state.get("status", "completed")
    used_rag: bool = final_state.get("used_rag", False) or any(s.tool_name == "ask_policy" for s in final_steps)
    citations = _extract_citations(final_steps)
    tools_invoked = [s.tool_name for s in final_steps]

    # Save turn messages to session store if session is active
    if clean_session_id:
        store.append_messages(clean_session_id, final_state.get("turn_messages", []))

    trace = AgentExecutionTrace(
        session_id=clean_session_id,
        query=clean_query,
        total_steps=len(final_steps),
        total_duration_ms=total_duration_ms,
        used_rag=used_rag,
        status=final_status,
        tools_invoked=tools_invoked,
        steps=final_steps,
    )

    logger.info(
        "LangGraph agent run finished | session_id=%s | status=%s | steps=%d | used_rag=%s | duration_ms=%.2f",
        clean_session_id,
        final_status,
        len(final_steps),
        used_rag,
        total_duration_ms,
    )

    return AgentResponse(
        session_id=clean_session_id,
        query=clean_query,
        final_answer=final_answer,
        steps=final_steps,
        total_steps=len(final_steps),
        duration_ms=total_duration_ms,
        status=final_status,
        used_rag=used_rag,
        citations=citations,
        trace=trace,
    )
