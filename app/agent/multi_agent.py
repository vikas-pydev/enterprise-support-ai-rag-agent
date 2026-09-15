"""Multi-Agent Architecture with Supervisor, Specialized Workers & Human-in-the-Loop Approval in LangGraph.

Implements a centralized Supervisor coordinating specialized Worker Agents:
1. HR Policy Agent (ask_policy)
2. Employee Records Agent (get_employee, get_leave_balance, list_department_employees)
3. Travel & Expense Agent (get_travel_summary)

Features strict tool permission boundaries per worker, structured JSON supervisor routing,
evidence-dependent conditional branching, clarification for missing business identifiers,
deterministic Human-in-the-Loop (HITL) approval gates for sensitive operations,
repeated-worker and cycle stall protection, loop & step budget enforcement, RAG citation preservation,
multi-turn session memory, and detailed execution tracing.
"""

import json
import logging
import re
import time
import uuid
from typing import Any, TypedDict
from openai import OpenAI
from langchain_core.runnables import RunnableConfig
from langchain_core.utils.function_calling import convert_to_openai_tool
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.llm import client as default_client
from app.tools import (
    ask_policy,
    get_employee,
    get_leave_balance,
    get_travel_summary,
    list_department_employees,
    ALL_TOOLS,
)
from app.agent.memory import InMemorySessionStore, default_session_store
from app.agent.checkpoint import (
    get_default_checkpointer,
    get_thread_id_for_session,
    build_thread_config,
    format_approval_id,
    resolve_thread_from_approval_id,
    get_thread_state,
    delete_thread_checkpoints,
)
from app.agent.agent import (
    TOOLS_BY_NAME,
    DEFAULT_AGENT_MODEL,
    MAX_AGENT_STEPS,
    AgentStep,
    AgentExecutionTrace,
    AgentResponse,
    _extract_citations,
    _execute_tool_call,
)

logger = logging.getLogger(__name__)

# =====================================================================
# DOMAIN DEFINITIONS & WORKER TOOL BOUNDARIES
# =====================================================================

HR_POLICY_WORKER = "hr_policy"
EMPLOYEE_RECORDS_WORKER = "employee_records"
TRAVEL_EXPENSE_WORKER = "travel_expense"

HR_POLICY_TOOLS: set[str] = {"ask_policy"}
EMPLOYEE_RECORDS_TOOLS: set[str] = {
    "get_employee",
    "get_leave_balance",
    "list_department_employees",
}
TRAVEL_EXPENSE_TOOLS: set[str] = {"get_travel_summary"}

WORKER_TOOL_MAPPING: dict[str, set[str]] = {
    HR_POLICY_WORKER: HR_POLICY_TOOLS,
    EMPLOYEE_RECORDS_WORKER: EMPLOYEE_RECORDS_TOOLS,
    TRAVEL_EXPENSE_WORKER: TRAVEL_EXPENSE_TOOLS,
}

ROUTING_ALLOWLIST: set[str] = {
    HR_POLICY_WORKER,
    EMPLOYEE_RECORDS_WORKER,
    TRAVEL_EXPENSE_WORKER,
    "finish",
    "clarify",
}

# Pre-convert domain tools to OpenAI schemas strictly bounded per worker
HR_POLICY_TOOL_SCHEMAS = [convert_to_openai_tool(ask_policy)]
EMPLOYEE_RECORDS_TOOL_SCHEMAS = [
    convert_to_openai_tool(get_employee),
    convert_to_openai_tool(get_leave_balance),
    convert_to_openai_tool(list_department_employees),
]
TRAVEL_EXPENSE_TOOL_SCHEMAS = [convert_to_openai_tool(get_travel_summary)]

WORKER_TOOL_SCHEMAS: dict[str, list[dict[str, Any]]] = {
    HR_POLICY_WORKER: HR_POLICY_TOOL_SCHEMAS,
    EMPLOYEE_RECORDS_WORKER: EMPLOYEE_RECORDS_TOOL_SCHEMAS,
    TRAVEL_EXPENSE_WORKER: TRAVEL_EXPENSE_TOOL_SCHEMAS,
}

# =====================================================================
# APPROVAL POLICY & STATUS CONSTANTS (PHASE 7 TASK 4)
# =====================================================================

APPROVAL_STATUS_NOT_REQUIRED = "not_required"
APPROVAL_STATUS_PENDING = "pending"
APPROVAL_STATUS_APPROVED = "approved"
APPROVAL_STATUS_REJECTED = "rejected"

VALID_APPROVAL_DECISIONS: set[str] = {"approve", "reject"}

SENSITIVE_KEYWORDS: tuple[str, ...] = (
    "salary",
    "compensation",
    "confidential",
    "restricted",
    "executive",
    "disciplinary",
    "performance rating",
    "ssn",
    "termination",
)

SENSITIVE_EMPLOYEE_IDS: tuple[str, ...] = (
    "E1000",
    "E9999",
)

import threading

# In-memory runtime store for pending approval states (keyed by approval_id)
_PENDING_APPROVAL_STORE: dict[str, dict[str, Any]] = {}
_APPROVAL_MUTEX = threading.Lock()


def cleanup_pending_approvals_for_thread(thread_id: str) -> None:
    """Removes any in-memory pending approval store records associated with a given thread_id."""
    clean_thread = str(thread_id).strip()
    keys_to_remove = [
        appr_id for appr_id, data in list(_PENDING_APPROVAL_STORE.items())
        if data.get("session_id") == clean_thread or appr_id.endswith(f"_{clean_thread}")
    ]
    for k in keys_to_remove:
        _PENDING_APPROVAL_STORE.pop(k, None)


def check_approval_policy(query: str, worker: str | None = None) -> tuple[bool, str | None]:
    """Evaluates whether an inquiry involves sensitive or high-risk data requiring human approval.

    Determined strictly by deterministic application policy, not LLM discretion.

    Returns:
        tuple of (approval_required: bool, reason: str | None)
    """
    if not query:
        return (False, None)

    q_lower = query.lower()

    # 1. Check sensitive employee identifiers first (exact token boundary)
    for emp_id in SENSITIVE_EMPLOYEE_IDS:
        if re.search(rf"\b{re.escape(emp_id.lower())}\b", q_lower):
            return (True, f"Query accesses restricted executive profile: '{emp_id}'")

    # 2. Check sensitive keywords (token boundary)
    for kw in SENSITIVE_KEYWORDS:
        if re.search(rf"\b{re.escape(kw.lower())}\b", q_lower):
            return (True, f"Query contains restricted/sensitive keyword: '{kw}'")

    return (False, None)


# =====================================================================
# SYSTEM PROMPTS
# =====================================================================

SUPERVISOR_SYSTEM_PROMPT = """You are the Supervisor of an Enterprise Support AI Multi-Agent system.
Your role is to orchestrate inquiries by routing tasks to specialized domain worker agents, managing multi-step workflows, or concluding with a final response.

SPECIALIZED WORKER DOMAINS:
1. `hr_policy`: Responsible for company policies, employee handbook, benefits, leave policy rules, meal per diem, travel expense rules, and IT security guidelines.
2. `employee_records`: Responsible for employee profiles, full name, department, job title, direct manager hierarchy, employee PTO/leave balances, and department employee rosters.
3. `travel_expense`: Responsible for employee travel expense claims, total spend, expense status, and expense category breakdowns.

ROUTING DESTINATIONS:
- "hr_policy": Select when general company policy, handbook, or guidelines need to be retrieved.
- "employee_records": Select when an employee profile, manager, leave balance, or department roster is needed and the employee/department identifier is known.
- "travel_expense": Select when employee travel expenditure or expense records are needed and the employee identifier is known.
- "finish": Select when all required facts have been collected and you are ready to synthesize the final answer to the user.
- "clarify": Select when the user request is missing an essential identifier (such as employee ID or department name) and cannot be resolved from conversation context, or when the request is too ambiguous to route safely.

EVIDENCE-BASED CONDITIONAL ROUTING RULES:
1. EVIDENCE ASSESSMENT: Review the gathered evidence before deciding the next route. If a domain worker has already successfully provided the required facts for its domain, do NOT route to it again.
2. MULTI-DOMAIN WORKFLOWS: If an inquiry requires multiple pieces of information across different domains (e.g. Travel Spend AND Manager Name, or Travel Spend AND Policy Meal Per Diem), route sequentially to the first required domain worker, then to the next after receiving findings.
3. INTRA-DOMAIN MULTI-STEP WORKFLOWS: If an inquiry asks for multiple facts within the same domain (e.g. employee profile AND leave balance), you may route to that domain worker to gather all needed evidence.
4. MISSING IDENTIFIERS & CLARIFICATION: If a request requires employee-specific data (profile, leave, travel) but no employee ID (e.g. 'E1001') is specified in the inquiry or previous conversation turns, route to "clarify". Do NOT invent or guess employee IDs.
5. NO DIRECT WORKER ACTIONS: You do not execute tools yourself. You only route or finish.
6. STRICT JSON OUTPUT: You MUST respond with ONLY a valid JSON object matching this schema:
{
  "next_worker": "hr_policy" | "employee_records" | "travel_expense" | "finish" | "clarify",
  "reasoning_summary": "Brief 1-sentence explanation of the routing decision",
  "missing_information": ["List of missing facts or identifiers, if any"],
  "completed_domains": ["List of domains already satisfied"]
}
"""

HR_POLICY_WORKER_PROMPT = """You are the HR Policy Agent.
You are responsible for looking up enterprise policies, guidelines, handbook details, travel expense rules, and per diem rates.
Use the `ask_policy` tool to retrieve accurate policy answers from the verified knowledge base.
Do not attempt to look up individual employee balances or operational database records.
"""

EMPLOYEE_RECORDS_WORKER_PROMPT = """You are the Employee Records Agent.
You are responsible for looking up employee profiles, job titles, departments, direct managers, leave/PTO balances, and department employee rosters.
Use `get_employee`, `get_leave_balance`, or `list_department_employees` to obtain official employee records.
Do not attempt to query company policy handbooks or travel expense claims.
"""

TRAVEL_EXPENSE_WORKER_PROMPT = """You are the Travel & Expense Agent.
You are responsible for looking up employee travel expense claims, spending totals, approval statuses, and category breakdowns.
Use `get_travel_summary` to retrieve operational travel expenditure records.
Do not attempt to query general HR handbook policies or employee profile details.
"""

WORKER_PROMPTS: dict[str, str] = {
    HR_POLICY_WORKER: HR_POLICY_WORKER_PROMPT,
    EMPLOYEE_RECORDS_WORKER: EMPLOYEE_RECORDS_WORKER_PROMPT,
    TRAVEL_EXPENSE_WORKER: TRAVEL_EXPENSE_WORKER_PROMPT,
}

# =====================================================================
# MULTI-AGENT STATE SCHEMA
# =====================================================================

class MultiAgentState(TypedDict, total=False):
    """Explicit typed state schema representing the complete lifecycle of a multi-agent run.

    Fields:
        session_id: Optional unique identifier for multi-turn session tracking.
        query: The cleaned original user input query.
        messages: Full chronological message payload sent across turns.
        turn_messages: New messages produced in the current turn.
        current_worker: Name of the worker agent currently active.
        worker_results: Chronological list of structured worker findings and summaries.
        collected_evidence: Chronological list of verified facts collected from workers.
        completed_domains: List of worker domain identifiers whose requirements have been satisfied.
        missing_information: List of required facts/identifiers not yet obtained.
        workflow_intent: Inferred high-level goal of the workflow.
        workflow_status: Execution status ('in_progress', 'completed', 'clarification_needed', 'pending_approval', 'stalled', 'max_steps_reached', 'error').
        conditional_decisions: History of conditional routing evaluations made by the supervisor.
        approval_required: Boolean flag indicating if human approval is required before execution.
        approval_status: Status of approval ('not_required', 'pending', 'approved', 'rejected').
        approval_reason: Explanation of why human approval is required.
        approval_request: Structured payload describing the pending approval request.
        approval_decision: Human decision submitted ('approve' or 'reject').
        approval_id: Unique identifier for tracking the approval lifecycle.
        steps: List of AgentStep records capturing all tool executions across workers.
        step_count: Total number of tool iterations executed across all workers.
        max_steps: Maximum step budget limit to prevent infinite agent loops.
        supervisor_iterations: Number of supervisor routing cycles executed.
        max_supervisor_iterations: Limit on supervisor routing decisions to prevent supervisor loops.
        routing_history: Chronological list of supervisor routing decisions.
        executed_calls: Map of (tool_name, serialized_args) to cached observations for duplicate protection.
        final_answer: Synthesized final response text returned to the user.
        status: Execution status ('completed', 'pending_approval', 'rejected', 'max_steps_reached', 'error').
        duration_ms: Total elapsed execution time in milliseconds.
        used_rag: Boolean flag indicating if policy retrieval was executed by HR Policy worker.
        citations: List of deduplicated RAG source citations.
        error: Optional error message string.
        start_time: Monotonic start timestamp (time.perf_counter).
        model: LLM model identifier.
        client: OpenAI/Groq API client instance.
    """

    session_id: str | None
    query: str
    messages: list[dict[str, Any]]
    turn_messages: list[dict[str, Any]]
    current_worker: str | None
    worker_results: list[dict[str, Any]]
    collected_evidence: list[dict[str, Any]]
    completed_domains: list[str]
    missing_information: list[str]
    workflow_intent: str | None
    workflow_status: str
    conditional_decisions: list[dict[str, Any]]
    approval_required: bool
    approval_status: str
    approval_reason: str | None
    approval_request: dict[str, Any] | None
    approval_decision: str | None
    approval_id: str | None
    steps: list[AgentStep]
    step_count: int
    max_steps: int
    supervisor_iterations: int
    max_supervisor_iterations: int
    routing_history: list[dict[str, Any]]
    executed_calls: dict[str, dict[str, Any]]
    final_answer: str
    status: str
    duration_ms: float
    used_rag: bool
    citations: list[dict[str, Any]]
    error: str | None
    start_time: float
    model: str
    client: Any


# =====================================================================
# SUPERVISOR ROUTER NODE
# =====================================================================

def _parse_supervisor_response(raw_content: str) -> tuple[str, str, list[str], list[str], bool]:
    """Parses supervisor model output to extract next_worker, reasoning, missing info, and completed domains.

    Returns:
        tuple of (next_worker, reasoning_summary, missing_info, completed_domains, is_valid)
    """
    if not raw_content or not raw_content.strip():
        return ("finish", "Empty response from supervisor", [], [], False)

    content = raw_content.strip()

    # Handle markdown fenced JSON blocks
    if "```" in content:
        lines = content.split("\n")
        json_lines = []
        in_block = False
        for line in lines:
            if line.strip().startswith("```"):
                in_block = not in_block
                continue
            if in_block:
                json_lines.append(line)
        if json_lines:
            content = "\n".join(json_lines).strip()

    # Attempt JSON parse
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            next_worker = str(parsed.get("next_worker", "")).strip().lower()
            reasoning = str(parsed.get("reasoning_summary", "")).strip()
            missing_info = parsed.get("missing_information", [])
            if not isinstance(missing_info, list):
                missing_info = [str(missing_info)]
            comp_domains = parsed.get("completed_domains", [])
            if not isinstance(comp_domains, list):
                comp_domains = [str(comp_domains)]

            if next_worker in ROUTING_ALLOWLIST:
                return (next_worker, reasoning, missing_info, comp_domains, True)
            else:
                return (next_worker, f"Invalid worker requested: '{next_worker}'", missing_info, comp_domains, False)
    except Exception:
        pass

    # Fallback heuristic if model replied with plain text
    lower_content = content.lower()
    for valid_route in ROUTING_ALLOWLIST:
        if valid_route in lower_content:
            return (valid_route, f"Inferred route '{valid_route}' from supervisor text.", [], [], True)

    return ("finish", f"Unable to parse valid route from: {content[:100]}", [], [], False)


def _get_llm_client(state: MultiAgentState, config: RunnableConfig | None = None) -> Any:
    """Extracts the active LLM client from runtime config or state, falling back to default_client."""
    if config and isinstance(config, dict):
        cfg_client = config.get("configurable", {}).get("client")
        if cfg_client is not None:
            return cfg_client
    if "client" in state and state.get("client") is not None:
        return state.get("client")
    return default_client


def supervisor_node(state: MultiAgentState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Evaluates conversation history, worker findings, and approval policy to select the next step."""
    client: OpenAI = _get_llm_client(state, config)
    model = state.get("model") or DEFAULT_AGENT_MODEL
    step_count = state.get("step_count") or 0
    max_steps = state.get("max_steps") or MAX_AGENT_STEPS
    supervisor_iters = (state.get("supervisor_iterations") or 0) + 1
    max_supervisor_iters = state.get("max_supervisor_iterations") or 6

    # 0a. Fast-path for explicit approval rejection
    approval_status = state.get("approval_status", APPROVAL_STATUS_NOT_REQUIRED)
    if approval_status == APPROVAL_STATUS_REJECTED:
        return {
            "current_worker": "finish",
            "workflow_status": "rejected",
            "status": "rejected",
            "supervisor_iterations": supervisor_iters,
        }

    # 0b. Fast-path for approved resumption: if worker is already targeted and not yet executed
    current_worker = state.get("current_worker")
    worker_results = state.get("worker_results", [])
    if (
        approval_status == APPROVAL_STATUS_APPROVED
        and current_worker in WORKER_TOOL_MAPPING
        and not any(r.get("worker") == current_worker for r in worker_results)
    ):
        logger.info("Supervisor fast-path: dispatching approved worker '%s'", current_worker)
        return {
            "current_worker": current_worker,
            "workflow_status": "in_progress",
            "supervisor_iterations": supervisor_iters,
        }

    # 1. Budget check
    if step_count >= max_steps or supervisor_iters > max_supervisor_iters:
        logger.warning(
            "Supervisor budget reached | step_count=%d/%d | iterations=%d/%d",
            step_count,
            max_steps,
            supervisor_iters,
            max_supervisor_iters,
        )
        return {
            "current_worker": "finish",
            "workflow_status": "max_steps_reached",
            "supervisor_iterations": supervisor_iters,
            "routing_history": state.get("routing_history", [])
            + [{"route": "finish", "reason": "Execution step or supervisor budget reached.", "valid": True}],
        }

    # 2. Build supervisor prompt context with prior worker observations
    worker_results = state.get("worker_results", [])
    history_summary = ""
    completed_domains_set = set(state.get("completed_domains", []))

    if worker_results:
        history_summary = "\n\nWORKER FINDINGS COLLECTED SO FAR:\n"
        for idx, res in enumerate(worker_results, start=1):
            worker_name = res.get("worker", "unknown")
            obs = res.get("summary", "")
            success = res.get("success", True)
            history_summary += f"{idx}. [{worker_name} | Success: {success}]: {obs}\n"
            if success and worker_name in WORKER_TOOL_MAPPING:
                completed_domains_set.add(worker_name)

    completed_domains_list = list(completed_domains_set)

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SUPERVISOR_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"USER INQUIRY: {state.get('query', '')}{history_summary}\nDecide next route in JSON.",
                },
            ],
            temperature=0.0,
        )
        raw_text = completion.choices[0].message.content or ""
    except Exception as e:
        logger.error("Supervisor LLM invocation failed: %s", e)
        return {
            "current_worker": "finish",
            "status": "error",
            "workflow_status": "error",
            "error": "Failed to contact supervisor model.",
            "supervisor_iterations": supervisor_iters,
            "routing_history": state.get("routing_history", [])
            + [{"route": "finish", "reason": "Supervisor invocation error", "valid": False}],
        }

    next_worker, reasoning, missing_info, parsed_comp_domains, is_valid = _parse_supervisor_response(raw_text)

    # 3. Stall & Loop Detection
    routing_history = list(state.get("routing_history", []))
    if routing_history:
        last_route = routing_history[-1].get("route")
        if last_route == next_worker and next_worker in WORKER_TOOL_MAPPING:
            last_res = worker_results[-1] if worker_results else None
            if last_res and (not last_res.get("success", True) or last_res.get("worker") == next_worker):
                consecutive_count = sum(1 for r in reversed(routing_history) if r.get("route") == next_worker)
                if consecutive_count >= 2:
                    logger.warning("Stall detected: Worker '%s' repeated without progress. Concluding.", next_worker)
                    next_worker = "finish"
                    reasoning = f"Stall protection: worker '{last_route}' completed its turn."

    if len(routing_history) >= 4:
        recent_routes = [r.get("route") for r in routing_history[-4:]]
        if recent_routes[0] == recent_routes[2] and recent_routes[1] == recent_routes[3] and recent_routes[0] != recent_routes[1]:
            logger.warning("Cycle detected: %s. Concluding workflow safely.", recent_routes)
            next_worker = "finish"
            reasoning = "Cycle protection: terminating repeated worker cycle."

    # 4. Deterministic Human-in-the-Loop Approval Check (Phase 7 Task 4)
    # Check if target operation requires approval and has not yet been approved
    approval_required = state.get("approval_required", False)
    approval_status = state.get("approval_status", APPROVAL_STATUS_NOT_REQUIRED)
    approval_reason = state.get("approval_reason")

    if next_worker in WORKER_TOOL_MAPPING and approval_status != APPROVAL_STATUS_APPROVED:
        is_req, reason = check_approval_policy(state.get("query", ""), next_worker)
        if is_req:
            approval_required = True
            approval_status = APPROVAL_STATUS_PENDING
            approval_reason = reason
            logger.info("HITL Approval required for query | target=%s | reason=%s", next_worker, reason)

    routing_record = {
        "iteration": supervisor_iters,
        "route": next_worker,
        "reason": reasoning,
        "valid": is_valid,
        "missing_information": missing_info,
        "completed_domains": completed_domains_list,
        "approval_required": approval_required,
        "approval_status": approval_status,
    }
    updated_routing_history = routing_history + [routing_record]

    updated_conditional_decisions = list(state.get("conditional_decisions", [])) + [{
        "step": supervisor_iters,
        "selected_route": next_worker,
        "reason": reasoning,
        "completed_domains": completed_domains_list,
        "missing_information": missing_info,
    }]

    if not is_valid:
        logger.warning("Supervisor produced invalid route: '%s' | rejecting and terminating safely.", next_worker)
        return {
            "current_worker": "finish",
            "workflow_status": "error",
            "supervisor_iterations": supervisor_iters,
            "routing_history": updated_routing_history,
            "conditional_decisions": updated_conditional_decisions,
            "error": f"Invalid worker route '{next_worker}' rejected.",
        }

    workflow_status = "in_progress"
    if approval_status == APPROVAL_STATUS_PENDING:
        workflow_status = "pending_approval"
    elif next_worker == "finish":
        workflow_status = "completed"
    elif next_worker == "clarify":
        workflow_status = "clarification_needed"

    logger.info(
        "Supervisor routed inquiry | route=%s | status=%s | approval=%s | reason=%s",
        next_worker,
        workflow_status,
        approval_status,
        reasoning,
    )

    return {
        "current_worker": next_worker,
        "workflow_status": workflow_status,
        "completed_domains": completed_domains_list,
        "missing_information": missing_info,
        "approval_required": approval_required,
        "approval_status": approval_status,
        "approval_reason": approval_reason,
        "supervisor_iterations": supervisor_iters,
        "routing_history": updated_routing_history,
        "conditional_decisions": updated_conditional_decisions,
    }


# =====================================================================
# HUMAN-IN-THE-LOOP APPROVAL NODE (PHASE 7 TASK 4)
# =====================================================================

def approval_node(state: MultiAgentState) -> dict[str, Any]:
    """Handles controlled Human-in-the-Loop pause and approval request registration.

    Pauses execution safely without executing any domain tools when approval is pending.
    LangGraph checkpointing automatically persists the complete state snapshot for this thread.
    """
    session_id = state.get("session_id")
    thread_id = get_thread_id_for_session(session_id)
    approval_id = state.get("approval_id") or format_approval_id(thread_id)
    reason = state.get("approval_reason") or "Access to restricted data requires operator authorization."
    target_worker = state.get("current_worker", "unknown")
    query = state.get("query", "")

    request_payload = {
        "approval_id": approval_id,
        "query": query,
        "target_worker": target_worker,
        "reason": reason,
        "timestamp": time.time(),
        "status": APPROVAL_STATUS_PENDING,
    }

    # Store backward-compatible mirror for legacy tests
    state_snapshot = dict(state)
    state_snapshot["approval_id"] = approval_id
    state_snapshot["approval_request"] = request_payload
    state_snapshot["approval_status"] = APPROVAL_STATUS_PENDING
    _PENDING_APPROVAL_STORE[approval_id] = state_snapshot

    pause_message = (
        f"This operation requires human approval before proceeding. "
        f"Approval Request ID: '{approval_id}'. Reason: {reason}."
    )

    turn_messages = list(state.get("turn_messages", []))
    turn_messages.append({"role": "assistant", "content": pause_message})

    logger.info("Graph paused for human approval | approval_id=%s | thread_id=%s | reason=%s", approval_id, thread_id, reason)

    return {
        "approval_id": approval_id,
        "approval_request": request_payload,
        "approval_status": APPROVAL_STATUS_PENDING,
        "workflow_status": "pending_approval",
        "status": "pending_approval",
        "final_answer": pause_message,
        "turn_messages": turn_messages,
    }


# =====================================================================
# SPECIALIZED WORKER EXECUTION HELPER
# =====================================================================

def _execute_worker(worker_name: str, state: MultiAgentState, config: Any | None = None) -> dict[str, Any]:
    """Executes a specialized worker agent with strict tool sandboxing and observation recording."""
    client: OpenAI = _get_llm_client(state, config)
    model = state.get("model", DEFAULT_AGENT_MODEL)
    allowed_tools = WORKER_TOOL_MAPPING.get(worker_name, set())
    tool_schemas = WORKER_TOOL_SCHEMAS.get(worker_name, [])
    worker_prompt = WORKER_PROMPTS.get(worker_name, "")

    query = state.get("query", "")
    current_steps = list(state.get("steps", []))
    executed_calls = dict(state.get("executed_calls", {}))
    worker_results = list(state.get("worker_results", []))
    collected_evidence = list(state.get("collected_evidence", []))
    completed_domains = list(state.get("completed_domains", []))

    prior_obs_text = ""
    if worker_results:
        prior_obs_text = "\nPrior worker observations:\n" + "\n".join(
            [f"- [{r.get('worker')}]: {r.get('summary')}" for r in worker_results]
        )

    worker_messages = [
        {"role": "system", "content": f"{worker_prompt}\n{prior_obs_text}"},
        {"role": "user", "content": query},
    ]

    step_num = len(current_steps) + 1

    try:
        response = client.chat.completions.create(
            model=model,
            messages=worker_messages,
            tools=tool_schemas,
            tool_choice="auto",
        )
    except Exception as e:
        logger.error("Worker '%s' LLM invocation failed: %s", worker_name, e)
        err_step = AgentStep(
            step_number=step_num,
            tool_name=f"{worker_name}_error",
            tool_args={},
            tool_result={"error": str(e)},
            status="error",
            duration_ms=0.0,
            error=f"Worker '{worker_name}' failed to call model.",
        )
        current_steps.append(err_step)
        worker_results.append({
            "worker": worker_name,
            "summary": f"Worker encountered an error contacting model: {str(e)}",
            "success": False,
        })
        return {
            "steps": current_steps,
            "step_count": state.get("step_count", 0) + 1,
            "worker_results": worker_results,
            "collected_evidence": collected_evidence,
            "error": str(e),
        }

    choice = response.choices[0]
    tool_calls = getattr(choice.message, "tool_calls", None)

    if not tool_calls:
        direct_text = (choice.message.content or "").strip()
        worker_results.append({
            "worker": worker_name,
            "summary": direct_text or "No additional information found.",
            "success": True,
        })
        collected_evidence.append({
            "worker": worker_name,
            "fact": direct_text,
            "tool": "direct",
        })
        if worker_name not in completed_domains:
            completed_domains.append(worker_name)
        return {
            "worker_results": worker_results,
            "collected_evidence": collected_evidence,
            "completed_domains": completed_domains,
            "step_count": state.get("step_count", 0) + 1,
        }

    # Worker requested tool calls
    for tc in tool_calls:
        tool_name = getattr(getattr(tc, "function", None), "name", "")
        raw_args = getattr(getattr(tc, "function", None), "arguments", "{}")

        # 1. Strict tool permission validation
        if tool_name not in allowed_tools:
            logger.error(
                "SECURITY VIOLATION: Worker '%s' attempted to execute unauthorized tool '%s'",
                worker_name,
                tool_name,
            )
            err_msg = f"Security error: Worker '{worker_name}' is not authorized to use tool '{tool_name}'."
            sec_step = AgentStep(
                step_number=step_num,
                tool_name=tool_name,
                tool_args={},
                tool_result={"error": err_msg, "status": "unauthorized"},
                status="error",
                duration_ms=0.0,
                error=err_msg,
            )
            current_steps.append(sec_step)
            worker_results.append({
                "worker": worker_name,
                "summary": err_msg,
                "success": False,
            })
            continue

        # 2. Parse arguments & check duplicate call protection
        if isinstance(raw_args, str):
            try:
                parsed_args = json.loads(raw_args) if raw_args.strip() else {}
            except Exception:
                parsed_args = {}
        elif isinstance(raw_args, dict):
            parsed_args = raw_args
        else:
            parsed_args = {}

        call_key = f"{tool_name}:{json.dumps(parsed_args, sort_keys=True, default=str)}"

        if call_key in executed_calls and tool_name in TOOLS_BY_NAME:
            previous_result = executed_calls[call_key]
            dup_result = {
                "status": "duplicate_rejected",
                "message": f"Tool '{tool_name}' with identical arguments was already executed.",
                "previous_result": previous_result,
            }
            dup_step = AgentStep(
                step_number=step_num,
                tool_name=tool_name,
                tool_args=parsed_args,
                tool_result=dup_result,
                status="rejected_duplicate",
                duration_ms=0.0,
                error="Duplicate tool call rejected.",
            )
            current_steps.append(dup_step)
            worker_results.append({
                "worker": worker_name,
                "tool": tool_name,
                "summary": f"Duplicate call to {tool_name} returned cached data.",
                "result": previous_result,
                "success": True,
            })
            if worker_name not in completed_domains:
                completed_domains.append(worker_name)
            continue

        # 3. Execute approved tool safely
        val_args, tool_result, step = _execute_tool_call(tool_name, raw_args, step_number=step_num)
        current_steps.append(step)

        if tool_name in TOOLS_BY_NAME:
            executed_calls[call_key] = tool_result

        summary_text = json.dumps(tool_result) if isinstance(tool_result, (dict, list)) else str(tool_result)
        worker_results.append({
            "worker": worker_name,
            "tool": tool_name,
            "summary": summary_text,
            "result": tool_result,
            "success": step.status == "success",
        })
        collected_evidence.append({
            "worker": worker_name,
            "tool": tool_name,
            "args": parsed_args,
            "observation": tool_result,
        })
        if step.status == "success" and worker_name not in completed_domains:
            completed_domains.append(worker_name)

    used_rag = state.get("used_rag", False) or any(s.tool_name == "ask_policy" for s in current_steps)

    return {
        "steps": current_steps,
        "step_count": state.get("step_count", 0) + 1,
        "executed_calls": executed_calls,
        "worker_results": worker_results,
        "collected_evidence": collected_evidence,
        "completed_domains": completed_domains,
        "used_rag": used_rag,
    }


# =====================================================================
# WORKER NODES
# =====================================================================

def hr_policy_worker_node(state: MultiAgentState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """HR Policy Agent worker node."""
    logger.info("Executing HR Policy worker node")
    return _execute_worker(HR_POLICY_WORKER, state, config)


def employee_records_worker_node(state: MultiAgentState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Employee Records Agent worker node."""
    logger.info("Executing Employee Records worker node")
    return _execute_worker(EMPLOYEE_RECORDS_WORKER, state, config)


def travel_expense_worker_node(state: MultiAgentState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Travel & Expense Agent worker node."""
    logger.info("Executing Travel & Expense worker node")
    return _execute_worker(TRAVEL_EXPENSE_WORKER, state, config)


# =====================================================================
# FINAL SYNTHESIS & MAX STEPS NODES
# =====================================================================

def final_synthesis_node(state: MultiAgentState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Synthesizes a grounded final response, handles clarification, or terminates rejected approval."""
    client: OpenAI = _get_llm_client(state, config)
    model = state.get("model", DEFAULT_AGENT_MODEL)
    query = state.get("query", "")
    current_worker = state.get("current_worker", "finish")
    workflow_status = state.get("workflow_status", "completed")
    approval_status = state.get("approval_status", APPROVAL_STATUS_NOT_REQUIRED)
    worker_results = state.get("worker_results", [])
    missing_info = state.get("missing_information", [])
    turn_messages = list(state.get("turn_messages", []))
    history_messages = list(state.get("messages", []))

    # Handle explicit approval rejection
    if approval_status == APPROVAL_STATUS_REJECTED:
        rejection_msg = "This request was rejected by a human operator and could not be fulfilled."
        turn_messages.append({"role": "assistant", "content": rejection_msg})
        return {
            "final_answer": rejection_msg,
            "status": "rejected",
            "workflow_status": "rejected",
            "turn_messages": turn_messages,
        }

    # Handle clarification routing
    if current_worker == "clarify" or workflow_status == "clarification_needed":
        clarify_prompt = (
            "You are an authoritative Enterprise Support AI Agent. "
            "The user's inquiry requires specific details (such as an Employee ID, department name, or clear entity) "
            "that were not provided in the question or conversational context.\n\n"
            f"USER QUESTION: {query}\n"
            f"MISSING DETAILS: {missing_info}\n\n"
            "Please respond directly to the user, politely explaining what specific information is needed to fulfill their request. "
            "Do not guess, hallucinate, or make up employee identifiers."
        )
        try:
            response = client.chat.completions.create(
                model=model,
                messages=history_messages + [{"role": "user", "content": clarify_prompt}],
                temperature=0.0,
            )
            clarify_text = (response.choices[0].message.content or "").strip()
        except Exception as e:
            logger.error("Clarification synthesis LLM invocation failed: %s", e)
            clarify_text = "Please provide your Employee ID (e.g. E1001) to look up this record."

        turn_messages.append({"role": "assistant", "content": clarify_text})
        return {
            "final_answer": clarify_text,
            "status": "completed",
            "workflow_status": "clarification_needed",
            "turn_messages": turn_messages,
        }

    # Standard final answer synthesis
    if not worker_results:
        synthesis_messages = history_messages + [
            {"role": "user", "content": query}
        ]
    else:
        findings_text = "\n".join(
            [f"- [{r.get('worker')} / {r.get('tool', 'direct')}]: {r.get('summary')}" for r in worker_results]
        )
        synthesis_prompt = (
            "You are an authoritative Enterprise Support AI Agent. "
            "Using ONLY the verified worker observations gathered below, synthesize a clear, helpful, "
            "and concise final answer directly addressing the user's question.\n\n"
            f"USER QUESTION: {query}\n\n"
            f"GATHERED EVIDENCE:\n{findings_text}\n\n"
            "Final Answer:"
        )
        synthesis_messages = history_messages + [
            {"role": "user", "content": synthesis_prompt}
        ]

    try:
        response = client.chat.completions.create(
            model=model,
            messages=synthesis_messages,
            temperature=0.0,
        )
        final_text = (response.choices[0].message.content or "").strip()
    except Exception as e:
        logger.error("Final synthesis LLM invocation failed: %s", e)
        final_text = "An error occurred while synthesizing the final response."

    turn_messages.append({"role": "assistant", "content": final_text})

    raw_status = state.get("status")
    final_status = raw_status if raw_status and raw_status not in ("running", "pending_approval") else "completed"

    return {
        "final_answer": final_text,
        "status": final_status,
        "workflow_status": "completed",
        "turn_messages": turn_messages,
    }


def max_steps_node(state: MultiAgentState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Synthesizes a response when maximum agent step or supervisor budget is reached."""
    client: OpenAI = _get_llm_client(state, config)
    model = state.get("model") or DEFAULT_AGENT_MODEL
    query = state.get("query") or ""
    worker_results = state.get("worker_results") or []
    turn_messages = list(state.get("turn_messages") or [])

    findings_text = "\n".join(
        [f"- [{r.get('worker')}]: {r.get('summary')}" for r in worker_results]
    )

    try:
        prompt = (
            "Maximum agent steps reached. Based on the gathered evidence below, "
            "synthesize your best concise final answer.\n\n"
            f"USER QUESTION: {query}\n"
            f"GATHERED EVIDENCE:\n{findings_text}"
        )
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        final_text = (response.choices[0].message.content or "Maximum agent steps reached.").strip()
    except Exception:
        final_text = "The agent reached the maximum step limit before completing the request."

    turn_messages.append({"role": "assistant", "content": final_text})

    return {
        "final_answer": final_text,
        "status": "max_steps_reached",
        "workflow_status": "max_steps_reached",
        "turn_messages": turn_messages,
    }


# =====================================================================
# CONDITIONAL ROUTING EDGES
# =====================================================================

def route_after_supervisor(state: MultiAgentState) -> str:
    """Evaluates supervisor routing decision and approval status to determine the next graph node."""
    step_count = state.get("step_count") or 0
    max_steps = state.get("max_steps") or MAX_AGENT_STEPS

    if step_count >= max_steps:
        return "max_steps"

    approval_status = state.get("approval_status", APPROVAL_STATUS_NOT_REQUIRED)

    # If human approval is pending, route strictly to approval pause node
    if approval_status == APPROVAL_STATUS_PENDING:
        return "approval_node"

    # If approval was explicitly rejected, route to final synthesis for safe termination
    if approval_status == APPROVAL_STATUS_REJECTED:
        return "final_synthesis"

    current_worker = state.get("current_worker", "finish")

    if current_worker == HR_POLICY_WORKER:
        return "hr_policy_worker"
    elif current_worker == EMPLOYEE_RECORDS_WORKER:
        return "employee_records_worker"
    elif current_worker == TRAVEL_EXPENSE_WORKER:
        return "travel_expense_worker"
    elif current_worker in ("finish", "clarify"):
        return "final_synthesis"
    else:
        return "final_synthesis"


# =====================================================================
# GRAPH COMPILATION
# =====================================================================

def create_multi_agent_graph(checkpointer: BaseCheckpointSaver | None = None):
    """Builds and compiles the multi-agent LangGraph workflow with Supervisor, approval node, and workers.

    Topology:
        START -> supervisor
        supervisor -> [approval_node, hr_policy_worker, employee_records_worker, travel_expense_worker, final_synthesis, max_steps]
        approval_node -> END (pauses execution)
        hr_policy_worker -> supervisor
        employee_records_worker -> supervisor
        travel_expense_worker -> supervisor
        final_synthesis -> END
        max_steps -> END

    Args:
        checkpointer: Optional BaseCheckpointSaver instance (defaults to get_default_checkpointer()).

    Returns:
        Compiled StateGraph instance ready for invocation.
    """
    workflow = StateGraph(MultiAgentState)

    # 1. Register Graph Nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("approval_node", approval_node)
    workflow.add_node("hr_policy_worker", hr_policy_worker_node)
    workflow.add_node("employee_records_worker", employee_records_worker_node)
    workflow.add_node("travel_expense_worker", travel_expense_worker_node)
    workflow.add_node("final_synthesis", final_synthesis_node)
    workflow.add_node("max_steps", max_steps_node)

    # 2. Register Edges
    workflow.add_edge(START, "supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "approval_node": "approval_node",
            "hr_policy_worker": "hr_policy_worker",
            "employee_records_worker": "employee_records_worker",
            "travel_expense_worker": "travel_expense_worker",
            "final_synthesis": "final_synthesis",
            "max_steps": "max_steps",
        },
    )

    # Approval node halts current run to await human input
    workflow.add_edge("approval_node", END)

    # Workers strictly route back to supervisor
    workflow.add_edge("hr_policy_worker", "supervisor")
    workflow.add_edge("employee_records_worker", "supervisor")
    workflow.add_edge("travel_expense_worker", "supervisor")

    workflow.add_edge("final_synthesis", END)
    workflow.add_edge("max_steps", END)

    ckpt = checkpointer if checkpointer is not None else get_default_checkpointer()
    return workflow.compile(checkpointer=ckpt)


# Global precompiled multi-agent graph instance
compiled_multi_agent_graph = create_multi_agent_graph()


# =====================================================================
# MULTI-AGENT EXECUTION RUNNER
# =====================================================================

def run_multi_agent(
    user_query: str,
    session_id: str | None = None,
    session_store: InMemorySessionStore | None = None,
    max_steps: int = MAX_AGENT_STEPS,
    model: str = DEFAULT_AGENT_MODEL,
    client: OpenAI | None = None,
    graph: Any | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> AgentResponse:
    """Executes the multi-agent workflow with Supervisor coordination, approval checking, and session memory.

    Args:
        user_query: The natural language question or request from the user.
        session_id: Optional unique identifier for multi-turn session tracking.
        session_store: Optional session store instance (defaults to default_session_store).
        max_steps: Maximum total worker tool execution budget.
        model: The LLM model identifier.
        client: Optional OpenAI client instance (defaults to preconfigured Groq client).
        graph: Optional compiled LangGraph instance (defaults to compiled_multi_agent_graph).
        checkpointer: Optional explicit checkpointer instance.

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
    thread_id = get_thread_id_for_session(clean_session_id)
    thread_config = {
        "configurable": {
            "thread_id": thread_id,
            "client": llm_client,
        }
    }

    logger.info(
        "Multi-agent run started | session_id=%s | thread_id=%s | query=%s",
        clean_session_id,
        thread_id,
        clean_query[:80],
    )

    # Resolve session history
    store = session_store or default_session_store
    history_messages: list[dict[str, Any]] = []
    if clean_session_id:
        history_messages = store.get_session(clean_session_id)

    initial_turn_messages: list[dict[str, Any]] = [
        {"role": "user", "content": clean_query},
    ]

    initial_state: MultiAgentState = {
        "session_id": clean_session_id,
        "query": clean_query,
        "messages": history_messages,
        "turn_messages": initial_turn_messages,
        "current_worker": None,
        "worker_results": [],
        "collected_evidence": [],
        "completed_domains": [],
        "missing_information": [],
        "workflow_intent": None,
        "workflow_status": "in_progress",
        "conditional_decisions": [],
        "approval_required": False,
        "approval_status": APPROVAL_STATUS_NOT_REQUIRED,
        "approval_reason": None,
        "approval_request": None,
        "approval_decision": None,
        "approval_id": None,
        "steps": [],
        "step_count": 0,
        "max_steps": max_steps,
        "supervisor_iterations": 0,
        "max_supervisor_iterations": 6,
        "routing_history": [],
        "executed_calls": {},
        "final_answer": "",
        "status": "running",
        "duration_ms": 0.0,
        "used_rag": False,
        "citations": [],
        "error": None,
        "start_time": start_time,
        "model": model,
    }

    runner_graph = graph or (create_multi_agent_graph(checkpointer=checkpointer) if checkpointer is not None else compiled_multi_agent_graph)

    try:
        final_state = runner_graph.invoke(initial_state, config=thread_config)
    except Exception as e:
        logger.error("Multi-agent graph encountered unhandled exception: %s", e)
        total_duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        err_msg = "An error occurred while executing the multi-agent graph."
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
        "Multi-agent run finished | session_id=%s | thread_id=%s | status=%s | workflow_status=%s | approval=%s | steps=%d | used_rag=%s | duration_ms=%.2f",
        clean_session_id,
        thread_id,
        final_status,
        final_state.get("workflow_status", "completed"),
        final_state.get("approval_status", APPROVAL_STATUS_NOT_REQUIRED),
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


# =====================================================================
# HUMAN-IN-THE-LOOP RESUME RUNNER (PHASE 7 TASK 5 - CHECKPOINTING)
# =====================================================================

def resume_multi_agent_approval(
    approval_id: str,
    decision: str,
    client: OpenAI | None = None,
    session_store: InMemorySessionStore | None = None,
    graph: Any | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    expected_session_id: str | None = None,
) -> AgentResponse:
    """Resumes an approval-paused multi-agent execution with an explicit human decision using LangGraph checkpoint state.

    Args:
        approval_id: The unique approval request identifier.
        decision: The human decision ('approve' or 'reject').
        client: Optional OpenAI/Groq client instance.
        session_store: Optional session store instance.
        graph: Optional compiled StateGraph instance.
        checkpointer: Optional explicit checkpointer instance.
        expected_session_id: Optional expected session/thread ID to enforce authorization/ownership.

    Returns:
        AgentResponse representing the completed or safely rejected workflow outcome.
    """
    t_start = time.perf_counter()

    clean_appr_id = str(approval_id).strip() if approval_id else ""
    if not clean_appr_id:
        err_msg = "Invalid approval ID provided."
        logger.warning("Approval resume rejected: %s", err_msg)
        trace = AgentExecutionTrace(
            session_id=None,
            query="",
            total_steps=0,
            total_duration_ms=0.0,
            used_rag=False,
            status="error",
            tools_invoked=[],
            steps=[],
        )
        return AgentResponse(
            session_id=None,
            query="",
            final_answer=err_msg,
            steps=[],
            total_steps=0,
            duration_ms=0.0,
            status="error",
            used_rag=False,
            citations=[],
            trace=trace,
        )

    clean_decision = str(decision).strip().lower() if decision else ""
    if clean_decision not in VALID_APPROVAL_DECISIONS:
        err_msg = f"Invalid decision '{decision}'. Must be explicitly 'approve' or 'reject'."
        logger.warning("Invalid approval decision: %s", err_msg)
        trace = AgentExecutionTrace(
            session_id=None,
            query="",
            total_steps=0,
            total_duration_ms=0.0,
            used_rag=False,
            status="error",
            tools_invoked=[],
            steps=[],
        )
        return AgentResponse(
            session_id=None,
            query="",
            final_answer=err_msg,
            steps=[],
            total_steps=0,
            duration_ms=0.0,
            status="error",
            used_rag=False,
            citations=[],
            trace=trace,
        )

    with _APPROVAL_MUTEX:
        target_checkpointer = checkpointer or get_default_checkpointer()
        runner_graph = graph or (create_multi_agent_graph(checkpointer=target_checkpointer) if checkpointer is not None else compiled_multi_agent_graph)

        # 1. Resolve thread identity from approval_id
        thread_id = resolve_thread_from_approval_id(clean_appr_id, checkpointer=target_checkpointer)
        if not thread_id and clean_appr_id in _PENDING_APPROVAL_STORE:
            thread_id = _PENDING_APPROVAL_STORE[clean_appr_id].get("session_id") or clean_appr_id

        if not thread_id:
            err_msg = f"Approval request '{clean_appr_id}' was not found or has already expired."
            logger.warning("Approval resume rejected: %s", err_msg)
            trace = AgentExecutionTrace(
                session_id=None,
                query="",
                total_steps=0,
                total_duration_ms=0.0,
                used_rag=False,
                status="error",
                tools_invoked=[],
                steps=[],
            )
            return AgentResponse(
                session_id=None,
                query="",
                final_answer=err_msg,
                steps=[],
                total_steps=0,
                duration_ms=0.0,
                status="error",
                used_rag=False,
                citations=[],
                trace=trace,
            )

        # Enforce optional session ownership constraint
        if expected_session_id and str(expected_session_id).strip():
            clean_expected = str(expected_session_id).strip()
            if thread_id != clean_expected:
                err_msg = f"Approval authorization error: approval '{clean_appr_id}' does not belong to session '{clean_expected}'."
                logger.warning("Cross-session approval resume rejected: %s", err_msg)
                trace = AgentExecutionTrace(
                    session_id=clean_expected,
                    query="",
                    total_steps=0,
                    total_duration_ms=0.0,
                    used_rag=False,
                    status="error",
                    tools_invoked=[],
                    steps=[],
                )
                return AgentResponse(
                    session_id=clean_expected,
                    query="",
                    final_answer=err_msg,
                    steps=[],
                    total_steps=0,
                    duration_ms=0.0,
                    status="error",
                    used_rag=False,
                    citations=[],
                    trace=trace,
                )

        thread_config = build_thread_config(thread_id)

        # 2. Retrieve checkpoint snapshot for this thread
        state_snapshot = None
        try:
            if hasattr(runner_graph, "get_state"):
                graph_snapshot = runner_graph.get_state(thread_config)
                if graph_snapshot and graph_snapshot.values:
                    state_snapshot = graph_snapshot.values
        except Exception as e:
            logger.warning("Error getting state from graph: %s", e)

        if not state_snapshot:
            raw_state = get_thread_state(target_checkpointer, thread_id)
            if raw_state:
                state_snapshot = raw_state
            elif clean_appr_id in _PENDING_APPROVAL_STORE:
                state_snapshot = _PENDING_APPROVAL_STORE.get(clean_appr_id)

        if not state_snapshot:
            err_msg = f"Approval request '{clean_appr_id}' was not found or has already expired."
            logger.warning("Approval resume rejected: %s", err_msg)
            trace = AgentExecutionTrace(
                session_id=thread_id,
                query="",
                total_steps=0,
                total_duration_ms=0.0,
                used_rag=False,
                status="error",
                tools_invoked=[],
                steps=[],
            )
            return AgentResponse(
                session_id=thread_id,
                query="",
                final_answer=err_msg,
                steps=[],
                total_steps=0,
                duration_ms=0.0,
                status="error",
                used_rag=False,
                citations=[],
                trace=trace,
            )

        # 3. Check for valid pending approval state transition
        existing_approval_status = state_snapshot.get("approval_status")
        if existing_approval_status != APPROVAL_STATUS_PENDING:
            if existing_approval_status == APPROVAL_STATUS_APPROVED:
                err_msg = f"Approval request '{clean_appr_id}' has already been approved."
            elif existing_approval_status == APPROVAL_STATUS_REJECTED:
                err_msg = f"Approval request '{clean_appr_id}' has already been rejected."
            else:
                err_msg = f"Approval request '{clean_appr_id}' is not in a pending state (current status: '{existing_approval_status}')."
            logger.warning("Invalid approval state transition rejected: %s", err_msg)
            trace = AgentExecutionTrace(
                session_id=state_snapshot.get("session_id") or thread_id,
                query=state_snapshot.get("query", ""),
                total_steps=0,
                total_duration_ms=0.0,
                used_rag=False,
                status="error",
                tools_invoked=[],
                steps=[],
            )
            return AgentResponse(
                session_id=state_snapshot.get("session_id") or thread_id,
                query=state_snapshot.get("query", ""),
                final_answer=err_msg,
                steps=[],
                total_steps=0,
                duration_ms=0.0,
                status="error",
                used_rag=False,
                citations=[],
                trace=trace,
            )

        # 4. Verify approval ID in checkpoint matches if recorded
        persisted_appr_id = state_snapshot.get("approval_id")
        if persisted_appr_id and persisted_appr_id != clean_appr_id:
            err_msg = f"Approval request '{clean_appr_id}' does not match the active approval for this session."
            logger.warning("Approval resume rejected due to ID mismatch: %s", err_msg)
            trace = AgentExecutionTrace(
                session_id=state_snapshot.get("session_id") or thread_id,
                query=state_snapshot.get("query", ""),
                total_steps=0,
                total_duration_ms=0.0,
                used_rag=False,
                status="error",
                tools_invoked=[],
                steps=[],
            )
            return AgentResponse(
                session_id=state_snapshot.get("session_id") or thread_id,
                query=state_snapshot.get("query", ""),
                final_answer=err_msg,
                steps=[],
                total_steps=0,
                duration_ms=0.0,
                status="error",
                used_rag=False,
                citations=[],
                trace=trace,
            )

        # 5. Prepare resume payload and inject client via thread_config
        llm_client = client or state_snapshot.get("client") or default_client
        thread_config = {
            "configurable": {
                "thread_id": thread_id,
                "client": llm_client,
            }
        }

        if clean_decision == "approve":
            target_worker = state_snapshot.get("current_worker") or (state_snapshot.get("approval_request") or {}).get("target_worker")
            resume_payload: dict[str, Any] = {
                "current_worker": target_worker,
                "approval_decision": "approve",
                "approval_status": APPROVAL_STATUS_APPROVED,
                "workflow_status": "in_progress",
                "status": "running",
            }
        else:
            resume_payload = {
                "current_worker": "finish",
                "approval_decision": "reject",
                "approval_status": APPROVAL_STATUS_REJECTED,
                "workflow_status": "rejected",
                "status": "rejected",
            }

        # Clean legacy store mirror if present
        _PENDING_APPROVAL_STORE.pop(clean_appr_id, None)

        logger.info(
            "Resuming graph from checkpointer | approval_id=%s | thread_id=%s | decision=%s | target_worker=%s",
            clean_appr_id,
            thread_id,
            clean_decision,
            state_snapshot.get("current_worker"),
        )

        try:
            final_state = runner_graph.invoke(resume_payload, config=thread_config)
        except Exception as e:
            logger.error("Error resuming graph from checkpointer: %s", e)
            total_duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
            err_msg = "An error occurred while resuming the approved agent workflow."
            trace = AgentExecutionTrace(
                session_id=state_snapshot.get("session_id") or thread_id,
                query=state_snapshot.get("query", ""),
                total_steps=0,
                total_duration_ms=total_duration_ms,
                used_rag=False,
                status="error",
                tools_invoked=[],
                steps=[],
            )
            return AgentResponse(
                session_id=state_snapshot.get("session_id") or thread_id,
                query=state_snapshot.get("query", ""),
                final_answer=err_msg,
                steps=[],
                total_steps=0,
                duration_ms=total_duration_ms,
                status="error",
                used_rag=False,
                citations=[],
                trace=trace,
            )

        total_duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
        final_steps: list[AgentStep] = final_state.get("steps", [])
        final_answer: str = final_state.get("final_answer", "")
        final_status: str = final_state.get("status", "completed")
        used_rag: bool = final_state.get("used_rag", False) or any(s.tool_name == "ask_policy" for s in final_steps)
        citations = _extract_citations(final_steps)
        tools_invoked = [s.tool_name for s in final_steps]

        clean_session_id = final_state.get("session_id") or thread_id
        store = session_store or default_session_store
        if clean_session_id:
            store.append_messages(clean_session_id, final_state.get("turn_messages", []))

        trace = AgentExecutionTrace(
            session_id=clean_session_id,
            query=final_state.get("query", ""),
            total_steps=len(final_steps),
            total_duration_ms=total_duration_ms,
            used_rag=used_rag,
            status=final_status,
            tools_invoked=tools_invoked,
            steps=final_steps,
        )

        logger.info(
            "Resumed multi-agent approval completed | approval_id=%s | thread_id=%s | status=%s | steps=%d | duration_ms=%.2f",
            clean_appr_id,
            thread_id,
            final_status,
            len(final_steps),
            total_duration_ms,
        )

        return AgentResponse(
            session_id=clean_session_id,
            query=final_state.get("query", ""),
            final_answer=final_answer,
            steps=final_steps,
            total_steps=len(final_steps),
            duration_ms=total_duration_ms,
            status=final_status,
            used_rag=used_rag,
            citations=citations,
            trace=trace,
        )
