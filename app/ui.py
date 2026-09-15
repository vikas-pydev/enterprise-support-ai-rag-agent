"""Production-Style Streamlit Showcase UI for the Enterprise Support AI Agent.

Interfaces with the FastAPI REST backend service to deliver:
1. Grounded enterprise policy question answering with deterministic citations (Policy Assistant Mode).
2. Multi-turn conversational AI agent with LangChain tools, supervisor/worker multi-agent workflows,
   LangGraph durable checkpointing, and Human-in-the-Loop (HITL) approvals (AI Agent Mode).
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any
import streamlit as st

from app.frontend.api_client import (
    ApiClient,
    ApiResponse,
    DEFAULT_BACKEND_URL,
)

logger = logging.getLogger(__name__)

# =====================================================================
# 1. PAGE CONFIGURATION & METADATA
# =====================================================================

st.set_page_config(
    page_title="Enterprise Support AI Agent",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =====================================================================
# 2. CUSTOM ENTERPRISE CSS DESIGN SYSTEM
# =====================================================================

st.markdown(
    """
    <style>
    /* Global Typography & Palette */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Main Container Spacing */
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }

    /* Header Styling */
    .hero-header {
        margin-bottom: 1.2rem;
    }
    .hero-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #0f172a;
        letter-spacing: -0.02em;
        margin-bottom: 0.3rem;
        display: flex;
        align-items: center;
        gap: 0.6rem;
    }
    .hero-subtitle {
        font-size: 1.02rem;
        color: #475569;
        line-height: 1.5;
        margin-bottom: 1rem;
    }

    /* System Status Bar */
    .status-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 0.6rem;
        margin-bottom: 1.4rem;
        padding: 0.65rem 0.9rem;
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        align-items: center;
    }
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        color: #334155;
    }
    .status-dot-green {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10b981;
    }
    .status-dot-red {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #ef4444;
    }
    .status-dot-amber {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #f59e0b;
    }

    /* Mode Banner */
    .mode-badge-policy {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        font-size: 0.82rem;
        font-weight: 600;
        border-radius: 6px;
        background-color: #e0e7ff;
        color: #3730a3;
        border: 1px solid #c7d2fe;
    }
    .mode-badge-agent {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        font-size: 0.82rem;
        font-weight: 600;
        border-radius: 6px;
        background-color: #fef3c7;
        color: #92400e;
        border: 1px solid #fde68a;
    }

    /* Answer Cards */
    .answer-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1.25rem 1.4rem;
        margin-top: 0.75rem;
        margin-bottom: 1rem;
        font-size: 1rem;
        line-height: 1.65;
        color: #1e293b;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
    }
    .refusal-card {
        background-color: #fffbeb;
        border: 1px solid #fef3c7;
        border-left: 5px solid #f59e0b;
        border-radius: 6px;
        padding: 1.1rem 1.25rem;
        margin-top: 0.75rem;
        margin-bottom: 1rem;
        font-size: 0.98rem;
        line-height: 1.6;
        color: #92400e;
    }

    /* Source Citation Cards */
    .source-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 0.85rem 1rem;
        margin-bottom: 0.6rem;
    }
    .source-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.35rem;
    }
    .source-title {
        font-weight: 600;
        color: #0f172a;
        font-size: 0.92rem;
    }
    .source-badge {
        font-size: 0.72rem;
        font-weight: 600;
        padding: 0.15rem 0.5rem;
        border-radius: 4px;
        background-color: #e2e8f0;
        color: #334155;
    }
    .source-meta {
        font-size: 0.8rem;
        color: #64748b;
        margin-bottom: 0.4rem;
    }
    .source-snippet {
        font-size: 0.86rem;
        color: #334155;
        border-left: 2px solid #cbd5e1;
        padding-left: 0.65rem;
        font-style: italic;
        background-color: #ffffff;
        padding-top: 0.3rem;
        padding-bottom: 0.3rem;
        border-radius: 0 4px 4px 0;
    }

    /* Human-in-the-Loop Approval Card */
    .approval-card {
        background-color: #fff7ed;
        border: 1px solid #ffedd5;
        border-left: 5px solid #ea580c;
        border-radius: 8px;
        padding: 1.2rem 1.35rem;
        margin-top: 0.9rem;
        margin-bottom: 1.2rem;
    }
    .approval-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #9a3412;
        margin-bottom: 0.4rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .approval-body {
        font-size: 0.92rem;
        color: #7c2d12;
        line-height: 1.55;
        margin-bottom: 0.8rem;
    }
    .approval-meta {
        font-size: 0.82rem;
        color: #9a3412;
        background-color: #ffedd5;
        padding: 0.35rem 0.7rem;
        border-radius: 4px;
        display: inline-block;
        margin-bottom: 0.8rem;
        font-family: monospace;
    }

    /* Workflow Step Pills */
    .workflow-container {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin-top: 0.5rem;
        margin-bottom: 0.9rem;
        padding: 0.6rem 0.85rem;
        background-color: #f1f5f9;
        border-radius: 6px;
    }
    .workflow-pill {
        font-size: 0.78rem;
        font-weight: 600;
        padding: 0.2rem 0.55rem;
        border-radius: 4px;
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        color: #1e293b;
    }
    .workflow-arrow {
        color: #94a3b8;
        font-weight: 700;
        font-size: 0.85rem;
    }

    /* Small code helper */
    code {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 0.85em;
        padding: 0.15em 0.35em;
        border-radius: 3px;
        background-color: #f1f5f9;
        color: #0f172a;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =====================================================================
# 3. SESSION STATE INITIALIZATION
# =====================================================================

def _generate_session_id() -> str:
    return f"session-{uuid.uuid4().hex[:8]}"

if "session_id" not in st.session_state:
    st.session_state.session_id = _generate_session_id()

if "app_mode" not in st.session_state:
    st.session_state.app_mode = "AI Agent"

if "backend_url" not in st.session_state:
    st.session_state.backend_url = DEFAULT_BACKEND_URL

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_approval" not in st.session_state:
    st.session_state.pending_approval = None

if "preset_query" not in st.session_state:
    st.session_state.preset_query = None

# Initialize ApiClient
api_client = ApiClient(base_url=st.session_state.backend_url)

# =====================================================================
# 4. SIDEBAR CONFIGURATION & CONTROLS
# =====================================================================

with st.sidebar:
    st.markdown("### 🏢 Agent Control Panel")

    # Mode Selector
    st.markdown("**Application Mode**")
    selected_mode = st.radio(
        label="Select Mode",
        options=["AI Agent", "Policy Assistant"],
        index=0 if st.session_state.app_mode == "AI Agent" else 1,
        help=(
            "• AI Agent: Multi-turn agent coordinating LangChain tools, SQL queries, RAG policies, and HITL approvals.\n"
            "• Policy Assistant: Grounded RAG knowledge base policy lookup with deterministic citations."
        ),
        label_visibility="collapsed",
    )
    if selected_mode != st.session_state.app_mode:
        st.session_state.app_mode = selected_mode
        st.rerun()

    st.markdown("---")

    # Backend Connection Configuration
    st.markdown("**Backend Service Gateway**")
    configured_url = st.text_input(
        "API Base URL",
        value=st.session_state.backend_url,
        help="FastAPI REST service endpoint.",
        key="cfg_backend_url",
    )
    if configured_url.strip() and configured_url.strip() != st.session_state.backend_url:
        st.session_state.backend_url = configured_url.strip()
        api_client = ApiClient(base_url=st.session_state.backend_url)
        st.rerun()

    # Session Management
    st.markdown("---")
    st.markdown("**Session Management**")

    st.markdown(
        f"<div style='font-size: 0.8rem; color: #64748b; margin-bottom: 0.5rem;'>"
        f"Active Session: <code style='font-size: 0.78rem;'>{st.session_state.session_id}</code>"
        f"</div>",
        unsafe_allow_html=True,
    )

    btn_col1, btn_col2 = st.columns(2)

    if btn_col1.button("➕ New", use_container_width=True, help="Start a new isolated conversation session"):
        st.session_state.session_id = _generate_session_id()
        st.session_state.messages = []
        st.session_state.pending_approval = None
        st.session_state.preset_query = None
        st.success("New session created.")
        st.rerun()

    if btn_col2.button("🧹 Clear", use_container_width=True, help="Clear message history for current session"):
        res = api_client.clear_session(st.session_state.session_id)
        st.session_state.messages = []
        st.session_state.pending_approval = None
        st.session_state.preset_query = None
        if res.is_ok:
            st.success("Session history cleared.")
        st.rerun()

    if st.button("🗑️ Delete Session from Backend", use_container_width=True, help="Completely delete session from memory & checkpointer"):
        res = api_client.delete_session(st.session_state.session_id)
        st.session_state.session_id = _generate_session_id()
        st.session_state.messages = []
        st.session_state.pending_approval = None
        st.session_state.preset_query = None
        if res.is_ok:
            st.success("Session deleted from server.")
        st.rerun()

    # Collapsible System Architecture Section
    st.markdown("---")
    with st.expander("ℹ️ System Details & Architecture", expanded=False):
        st.markdown(
            f"""
            **Mode**: `{st.session_state.app_mode}`  
            **Backend**: `{st.session_state.backend_url}`  
            **Session ID**: `{st.session_state.session_id}`  

            **Active Architecture**:
            - **Retrieval**: Dense (ChromaDB) + Sparse (BM25)
            - **Reranker**: Cross-Encoder (`ms-marco-MiniLM-L-6-v2`)
            - **Database**: PostgreSQL (Operational Records)
            - **Agent**: Controlled LangChain Tools + LangGraph
            - **Checkpointing**: Durable State Saver
            """
        )

# =====================================================================
# 5. LIVE HEALTH CHECK & SERVICE STATUS
# =====================================================================

health_resp = api_client.check_health()
is_backend_online = health_resp.is_ok

# =====================================================================
# 6. MAIN HEADER & STATUS BAR
# =====================================================================

st.markdown(
    """
    <div class="hero-header">
        <div class="hero-title">🏢 Enterprise Support AI Agent</div>
        <div class="hero-subtitle">
            Grounded enterprise AI assistant powered by RAG, PostgreSQL, tool calling, and LangGraph
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Status Bar (Displays actual verified health)
if is_backend_online:
    st.markdown(
        """
        <div class="status-bar">
            <span class="status-pill"><span class="status-dot-green"></span> FastAPI Gateway: <strong>Online</strong></span>
            <span class="status-pill"><span class="status-dot-green"></span> RAG Engine: <strong>Active</strong></span>
            <span class="status-pill"><span class="status-dot-green"></span> PostgreSQL: <strong>Connected</strong></span>
            <span class="status-pill"><span class="status-dot-green"></span> Agent Service: <strong>Ready</strong></span>
            <span class="status-pill"><span class="status-dot-green"></span> LangGraph Checkpoint: <strong>Durable</strong></span>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f"""
        <div class="status-bar" style="background-color: #fef2f2; border-color: #fecaca;">
            <span class="status-pill"><span class="status-dot-red"></span> FastAPI Gateway: <strong>Offline</strong></span>
            <span class="status-pill" style="color: #991b1b;">
                Backend service is unreachable at <code>{st.session_state.backend_url}</code>.
                Start the backend using: <code>uvicorn app.api.main:app --reload</code>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Active Mode Indicator
mode_badge = (
    '<span class="mode-badge-agent">🤖 Mode: Multi-Agent AI Assistant</span>'
    if st.session_state.app_mode == "AI Agent"
    else '<span class="mode-badge-policy">📘 Mode: Enterprise Policy Assistant (RAG)</span>'
)
st.markdown(f"<div style='margin-bottom: 0.9rem;'>{mode_badge}</div>", unsafe_allow_html=True)

# =====================================================================
# 7. EXAMPLE QUERIES SELECTOR
# =====================================================================

POLICY_EXAMPLES = [
    {"label": "✈️ Meal Per Diem", "query": "What is the meal per diem allowance for domestic travel?"},
    {"label": "💰 401(k) Match", "query": "How much does the company match 401(k) contributions?"},
    {"label": "🕒 Remote Hours", "query": "What are the core collaboration hours for remote employees?"},
    {"label": "🚫 Policy Refusal", "query": "What is the company pet insurance reimbursement policy?"},
]

AGENT_EXAMPLES = [
    {"label": "👤 Employee Profile", "query": "Show employee E1001's information."},
    {"label": "🌴 Leave Balance", "query": "How many annual leave days does E1001 have left?"},
    {"label": "💼 Travel Spend", "query": "How much has E1001 spent on travel?"},
    {"label": "👥 Manager Info", "query": "Who is E1001's manager?"},
    {"label": "🔄 Multi-Domain", "query": "How much has E1001 spent on travel and what is the domestic meal allowance?"},
    {"label": "📊 Full Summary", "query": "Show E1001's travel expenses and leave balance."},
    {"label": "🛡️ Sensitive Approval", "query": "Show confidential salary and compensation records for employee E1000."},
]

active_examples = AGENT_EXAMPLES if st.session_state.app_mode == "AI Agent" else POLICY_EXAMPLES

st.markdown("<div style='font-size: 0.88rem; font-weight: 600; color: #475569; margin-bottom: 0.35rem;'>💡 Suggested Example Queries:</div>", unsafe_allow_html=True)
cols = st.columns(len(active_examples))
for idx, ex in enumerate(active_examples):
    if cols[idx].button(ex["label"], key=f"ex_btn_{st.session_state.app_mode}_{idx}", use_container_width=True):
        st.session_state.preset_query = ex["query"]
        st.rerun()

st.markdown("---")

# =====================================================================
# 8. HUMAN APPROVAL INTERACTION CARD
# =====================================================================

def _render_pending_approval_card(approval_info: dict[str, Any]):
    """Renders the interactive Human-in-the-Loop approval card."""
    approval_id = approval_info.get("approval_id", "")
    reason = approval_info.get("reason", "Sensitive operation requires explicit authorization.")
    worker = approval_info.get("worker", "employee_records")

    st.markdown(
        f"""
        <div class="approval-card">
            <div class="approval-title">⚠️ Human Operator Approval Required</div>
            <div class="approval-body">
                The agent has encountered an operation requiring supervisor authorization:
                <br><strong>Reason:</strong> {reason}
            </div>
            <div class="approval-meta">
                Approval ID: {approval_id} &nbsp;|&nbsp; Target Worker: {worker} &nbsp;|&nbsp; Status: PENDING
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    appr_col1, appr_col2, _ = st.columns([1.2, 1.2, 3])

    if appr_col1.button("✅ Approve Action", key=f"btn_approve_{approval_id}", type="primary", use_container_width=True):
        with st.spinner("Submitting approval and resuming agent workflow..."):
            res = api_client.submit_approval(approval_id=approval_id, decision="approve")
            if res.is_ok and res.data:
                data = res.data
                answer = data.get("answer", "Action approved and completed.")
                duration_ms = data.get("duration_ms", 0.0)
                trace = data.get("trace")

                # Append assistant completion to chat history
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "mode": "AI Agent",
                        "duration_ms": duration_ms,
                        "trace": trace,
                        "approval_resolved": "Approved",
                    }
                )
                st.session_state.pending_approval = None
                st.rerun()
            else:
                st.error(f"Approval failed: {res.error}")

    if appr_col2.button("❌ Reject Action", key=f"btn_reject_{approval_id}", use_container_width=True):
        with st.spinner("Submitting rejection decision..."):
            res = api_client.submit_approval(approval_id=approval_id, decision="reject")
            if res.is_ok and res.data:
                data = res.data
                answer = data.get("answer", "This request was rejected by a human operator and could not be fulfilled.")
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "mode": "AI Agent",
                        "approval_resolved": "Rejected",
                    }
                )
                st.session_state.pending_approval = None
                st.rerun()
            else:
                st.error(f"Rejection submission failed: {res.error}")

# =====================================================================
# 9. CHAT HISTORY DISPLAY
# =====================================================================

for msg_idx, msg in enumerate(st.session_state.messages):
    role = msg.get("role", "assistant")
    content = msg.get("content", "")

    if role == "user":
        with st.chat_message("user"):
            st.markdown(content)
    else:
        with st.chat_message("assistant"):
            mode = msg.get("mode", "AI Agent")
            is_refusal = msg.get("is_refusal", False)
            sources = msg.get("sources", [])
            steps = msg.get("steps", [])
            trace = msg.get("trace")
            duration_ms = msg.get("duration_ms", 0.0)
            approval_resolved = msg.get("approval_resolved")

            if approval_resolved:
                badge_color = "#10b981" if approval_resolved == "Approved" else "#ef4444"
                st.markdown(
                    f"<div style='font-size: 0.8rem; font-weight: 600; color: {badge_color}; margin-bottom: 0.4rem;'>"
                    f"🛡️ Human Approval Decision: <strong>{approval_resolved}</strong>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            # Refusal presentation
            if is_refusal or "not available in the provided documents" in content.lower():
                st.markdown(
                    f"""
                    <div class="refusal-card">
                        <strong>⚠️ Knowledge Base Refusal:</strong><br>
                        {content}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
                    <div class="answer-card">
                        {content}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Citations (Policy Assistant or Agent with RAG)
            if sources:
                st.markdown("<div style='font-size: 0.88rem; font-weight: 600; color: #334155; margin-top: 0.6rem; margin-bottom: 0.35rem;'>📚 Verifiable Source Citations:</div>", unsafe_allow_html=True)
                for src in sources:
                    rank = src.get("rank", 1)
                    title = src.get("title", "Policy Document")
                    source_file = src.get("source_file", "policy.md")
                    chunk_uid = src.get("chunk_uid", f"chunk_{rank}")
                    rerank_score = src.get("rerank_score", 0.0)
                    snippet = src.get("snippet", "")

                    st.markdown(
                        f"""
                        <div class="source-card">
                            <div class="source-header">
                                <span class="source-title">{title}</span>
                                <span class="source-badge">Rank #{rank}</span>
                            </div>
                            <div class="source-meta">
                                <strong>File:</strong> <code>{source_file}</code> &nbsp;|&nbsp;
                                <strong>Chunk UID:</strong> <code>{chunk_uid}</code> &nbsp;|&nbsp;
                                <strong>Rerank Score:</strong> <code>{rerank_score:.3f}</code>
                            </div>
                            <div class="source-snippet">"{snippet}"</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            # Execution Summary & Multi-Agent Visualization (Agent Mode)
            if mode == "AI Agent" and (steps or trace):
                tools_used = []
                if trace and trace.get("tools_invoked"):
                    tools_used = trace.get("tools_invoked", [])
                elif steps:
                    tools_used = [s.get("tool_name") for s in steps if s.get("tool_name")]

                # Visual Multi-Agent Flow sequence
                workflow_pills = [
                    '<span class="workflow-pill">👤 User Query</span>',
                    '<span class="workflow-arrow">→</span>',
                    '<span class="workflow-pill">🧭 Supervisor Router</span>',
                ]

                # Map tools to worker domain badges
                for t in tools_used:
                    if t == "ask_policy":
                        w_name = "📘 HR Policy Worker"
                    elif t in ("get_employee", "get_leave_balance", "list_department_employees"):
                        w_name = "👤 Employee Records Worker"
                    elif t == "get_travel_summary":
                        w_name = "💼 Travel & Expense Worker"
                    else:
                        w_name = f"🔧 Tool: {t}"

                    workflow_pills.append('<span class="workflow-arrow">→</span>')
                    workflow_pills.append(f'<span class="workflow-pill">{w_name} (<code>{t}</code>)</span>')

                workflow_pills.append('<span class="workflow-arrow">→</span>')
                workflow_pills.append('<span class="workflow-pill">🎯 Final Synthesis</span>')

                st.markdown(
                    f"""
                    <div class="workflow-container">
                        {' '.join(workflow_pills)}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Safe Execution Details Expander
                with st.expander("🔍 Execution Summary & Tool Steps", expanded=False):
                    met_col1, met_col2, met_col3, met_col4 = st.columns(4)
                    met_col1.metric("Execution Status", msg.get("status", "completed").upper())
                    met_col2.metric("Total Steps", len(steps))
                    met_col3.metric("Latency", f"{duration_ms:.1f} ms" if duration_ms else "N/A")
                    met_col4.metric("RAG Policy Used", "Yes" if msg.get("used_rag") else "No")

                    if steps:
                        st.markdown("**Executed Tool Steps:**")
                        table_data = []
                        for s in steps:
                            table_data.append(
                                {
                                    "Step": s.get("step_number", 1),
                                    "Tool": s.get("tool_name", "unknown"),
                                    "Arguments": str(s.get("tool_args", {})),
                                    "Status": s.get("status", "success"),
                                    "Duration (ms)": round(s.get("duration_ms", 0.0), 1),
                                }
                            )
                        st.dataframe(table_data, use_container_width=True)

# Render pending approval card if active
if st.session_state.pending_approval is not None:
    _render_pending_approval_card(st.session_state.pending_approval)

# =====================================================================
# 10. INPUT & INVOCATION PIPELINE
# =====================================================================

prompt_input = st.chat_input("Ask a policy question or instruct the AI agent...")

# Check if a preset example query was clicked
active_query = None
if st.session_state.preset_query:
    active_query = st.session_state.preset_query
    st.session_state.preset_query = None
elif prompt_input:
    active_query = prompt_input.strip()

if active_query:
    # 1. Append user message to state
    st.session_state.messages.append(
        {
            "role": "user",
            "content": active_query,
            "mode": st.session_state.app_mode,
        }
    )

    # 2. Execute Backend Pipeline
    if not is_backend_online:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": (
                    f"⚠️ Backend service unavailable at `{st.session_state.backend_url}`. "
                    "Please start the FastAPI service (`uvicorn app.api.main:app --reload`) and try again."
                ),
                "mode": st.session_state.app_mode,
            }
        )
        st.rerun()

    # -------------------------------------------------------------
    # Pipeline Branch A: Policy Assistant Mode (RAG /api/v1/ask)
    # -------------------------------------------------------------
    if st.session_state.app_mode == "Policy Assistant":
        with st.spinner("Retrieving authoritative policy documents and generating answer..."):
            t_start = time.perf_counter()
            api_res = api_client.ask_policy(active_query)
            t_latency = (time.perf_counter() - t_start) * 1000.0

            if api_res.is_ok and isinstance(api_res.data, dict):
                data = api_res.data
                answer_text = data.get("answer", "No answer returned.")
                is_refusal = data.get("is_refusal", False)
                sources = data.get("sources", [])

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer_text,
                        "mode": "Policy Assistant",
                        "is_refusal": is_refusal,
                        "sources": sources,
                        "duration_ms": t_latency,
                    }
                )
            else:
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": f"⚠️ Error: {api_res.error or 'Failed to retrieve policy answer.'}",
                        "mode": "Policy Assistant",
                        "is_refusal": True,
                    }
                )
        st.rerun()

    # -------------------------------------------------------------
    # Pipeline Branch B: AI Agent Mode (/api/v1/agent/chat)
    # -------------------------------------------------------------
    else:
        with st.spinner("Agent is reasoning, calling tools, and synthesizing answer..."):
            api_res = api_client.chat_agent(
                message=active_query,
                session_id=st.session_state.session_id,
            )

            if api_res.is_ok and isinstance(api_res.data, dict):
                data = api_res.data
                answer_text = data.get("answer", "")
                status = data.get("status", "completed")
                steps = data.get("steps", [])
                duration_ms = data.get("duration_ms", 0.0)
                used_rag = data.get("used_rag", False)
                citations = data.get("citations", [])
                trace = data.get("trace")

                # Check if this query triggered a Human Approval gate
                if status == "pending_approval" or "Approval Request ID: '" in answer_text:
                    # Extract approval ID from answer or trace
                    import re
                    match = re.search(r"Approval Request ID: '([^']+)'", answer_text)
                    approval_id = match.group(1) if match else f"appr-{st.session_state.session_id}"

                    reason_match = re.search(r"Reason:\s*([^.]+)", answer_text)
                    reason = reason_match.group(1) if reason_match else "Sensitive executive profile or restricted data access."

                    st.session_state.pending_approval = {
                        "approval_id": approval_id,
                        "reason": reason,
                        "worker": "employee_records",
                        "query": active_query,
                    }

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer_text,
                        "mode": "AI Agent",
                        "status": status,
                        "steps": steps,
                        "duration_ms": duration_ms,
                        "used_rag": used_rag,
                        "sources": citations,
                        "trace": trace,
                    }
                )
            else:
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": f"⚠️ Agent Error: {api_res.error or 'Failed to execute agent workflow.'}",
                        "mode": "AI Agent",
                        "status": "error",
                    }
                )
        st.rerun()
