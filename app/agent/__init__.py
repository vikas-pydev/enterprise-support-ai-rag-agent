"""Enterprise Support AI Agent Module.

Provides controlled tool-calling execution loops connecting user inquiries
to validated LangChain tools for hybrid RAG policy retrieval and PostgreSQL
operational data lookups, with multi-turn conversational session memory,
structured execution tracing, and observability.
"""

from app.agent.agent import (
    run_agent,
    AgentResponse,
    AgentStep,
    AgentExecutionTrace,
    TOOLS_BY_NAME,
    OPENAI_TOOL_SCHEMAS,
    DEFAULT_AGENT_MODEL,
    MAX_AGENT_STEPS,
)
from app.agent.graph import (
    run_graph_agent,
    create_agent_graph,
    AgentGraphState,
)
from app.agent.multi_agent import (
    run_multi_agent,
    resume_multi_agent_approval,
    check_approval_policy,
    create_multi_agent_graph,
    MultiAgentState,
    HR_POLICY_WORKER,
    EMPLOYEE_RECORDS_WORKER,
    TRAVEL_EXPENSE_WORKER,
    HR_POLICY_TOOLS,
    EMPLOYEE_RECORDS_TOOLS,
    TRAVEL_EXPENSE_TOOLS,
    ROUTING_ALLOWLIST,
    APPROVAL_STATUS_NOT_REQUIRED,
    APPROVAL_STATUS_PENDING,
    APPROVAL_STATUS_APPROVED,
    APPROVAL_STATUS_REJECTED,
    VALID_APPROVAL_DECISIONS,
)
from app.agent.checkpoint import (
    create_checkpointer,
    get_default_checkpointer,
    set_default_checkpointer,
    reset_default_checkpointer,
    get_thread_id_for_session,
    build_thread_config,
    format_approval_id,
    resolve_thread_from_approval_id,
    get_thread_state,
    delete_thread_checkpoints,
)
from app.agent.memory import InMemorySessionStore, default_session_store
from app.agent.prompts import AGENT_SYSTEM_PROMPT

__all__ = [
    "run_agent",
    "run_graph_agent",
    "create_agent_graph",
    "AgentGraphState",
    "run_multi_agent",
    "resume_multi_agent_approval",
    "check_approval_policy",
    "create_multi_agent_graph",
    "MultiAgentState",
    "HR_POLICY_WORKER",
    "EMPLOYEE_RECORDS_WORKER",
    "TRAVEL_EXPENSE_WORKER",
    "HR_POLICY_TOOLS",
    "EMPLOYEE_RECORDS_TOOLS",
    "TRAVEL_EXPENSE_TOOLS",
    "ROUTING_ALLOWLIST",
    "APPROVAL_STATUS_NOT_REQUIRED",
    "APPROVAL_STATUS_PENDING",
    "APPROVAL_STATUS_APPROVED",
    "APPROVAL_STATUS_REJECTED",
    "VALID_APPROVAL_DECISIONS",
    "create_checkpointer",
    "get_default_checkpointer",
    "set_default_checkpointer",
    "reset_default_checkpointer",
    "get_thread_id_for_session",
    "build_thread_config",
    "format_approval_id",
    "resolve_thread_from_approval_id",
    "get_thread_state",
    "delete_thread_checkpoints",
    "AgentResponse",
    "AgentStep",
    "AgentExecutionTrace",
    "InMemorySessionStore",
    "default_session_store",
    "TOOLS_BY_NAME",
    "OPENAI_TOOL_SCHEMAS",
    "DEFAULT_AGENT_MODEL",
    "MAX_AGENT_STEPS",
    "AGENT_SYSTEM_PROMPT",
]

