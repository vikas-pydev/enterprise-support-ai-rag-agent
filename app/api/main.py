import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.schemas import (
    HealthResponse,
    AskRequest,
    AskResponse,
    CitationSource,
    EmployeeResponse,
    EmployeeLeaveResponse,
    EmployeeTravelResponse,
    AgentChatRequest,
    AgentChatResponse,
    AgentStepResponse,
    AgentExecutionTraceResponse,
    SessionClearResponse,
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    ErrorResponse,
)
from app.retriever import retrieve
from app.rag import generate_answer
from app.context_config import DEFAULT_CONFIG
from app.database import (
    get_employee_summary,
    get_employee_leave_summary,
    get_employee_travel_summary,
    DatabaseError,
)
from app.agent import (
    run_agent,
    resume_multi_agent_approval,
    default_session_store,
    get_default_checkpointer,
    delete_thread_checkpoints,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Deterministic startup initialization: auto-seeds ChromaDB and verifies DB."""
    # 1. Deterministic ChromaDB auto-seed if vector collection is empty
    try:
        from app.vector_store import collection
        from app.ingestion import ingest_directory
        if collection is not None and collection.count() == 0:
            docs_dir = os.getenv("DOCUMENTS_DIR", "data/documents")
            if os.path.isdir(docs_dir):
                logger.info("ChromaDB vector store is empty on startup. Auto-seeding from %s...", docs_dir)
                summary = ingest_directory(docs_dir, reset=False)
                logger.info(
                    "Auto-seeded ChromaDB: %s chunks stored from %s documents.",
                    summary.get("total_chunks", 0),
                    summary.get("total_documents", 0),
                )
    except Exception as e:
        logger.warning("Startup ChromaDB auto-seeding check skipped or encountered error: %s", e)

    # 2. Idempotent PostgreSQL schema bootstrap if database is reachable
    try:
        from app.database.bootstrap import bootstrap_database
        from app.database.config import DEFAULT_DB_CONFIG
        from app.database.connection import test_connection
        if test_connection(DEFAULT_DB_CONFIG):
            seed_demo = os.getenv("SEED_DEMO_DATA", "0").lower() in ("1", "true", "yes")
            bootstrap_database(config=DEFAULT_DB_CONFIG, seed_demo=seed_demo)
    except Exception as e:
        logger.info("Startup database auto-bootstrap skipped: %s", e)

    yield


# Initialize FastAPI application
app = FastAPI(
    title="Enterprise Support AI Agent API",
    description=(
        "Production REST service layer exposing hybrid RAG policy question answering, "
        "PostgreSQL structured enterprise data queries, and multi-turn conversational AI agent capabilities."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure CORS
cors_origins_raw = os.getenv(
    "CORS_ORIGINS",
    "https://enterprise-support-ai-rag-agent.vercel.app,http://localhost:8501,http://127.0.0.1:8501,http://localhost:3000,http://127.0.0.1:3000",
)
cors_origins = [origin.strip() for origin in cors_origins_raw.split(",") if origin.strip()]
cors_origin_regex = os.getenv(
    "CORS_ORIGIN_REGEX",
    r"^https:\/\/.*\.vercel\.app$|^https:\/\/.*\.onrender\.com$|^http:\/\/localhost(:\d+)?$|^http:\/\/127\.0\.0\.1(:\d+)?$",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================================
# GLOBAL EXCEPTION HANDLERS
# =====================================================================

@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError):
    """Sanitized handler for database exceptions preventing credential leakage."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "A database error occurred while processing your request.",
            "error_type": "DatabaseError",
        },
    )


# =====================================================================
# 1. SYSTEM HEALTH & ROOT ENDPOINTS
# =====================================================================

@app.get(
    "/",
    tags=["System"],
    summary="API Root & Service Information",
    description="Returns service metadata, health status, and active documentation endpoints.",
)
async def root():
    return {
        "name": "Enterprise Support AI Agent API",
        "status": "healthy",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Service Health Check",
    description="Returns the service health status and API version.",
)
async def health_check():
    return HealthResponse(status="healthy", version="1.0.0")


# =====================================================================
# 2. RAG QUESTION ENDPOINT
# =====================================================================

@app.post(
    "/api/v1/ask",
    response_model=AskResponse,
    tags=["RAG Knowledge Base"],
    summary="Ask Enterprise Policy Question",
    description=(
        "Answers enterprise policy questions strictly from retrieved policy documents "
        "using hybrid retrieval (Dense ChromaDB + Sparse BM25 + Cross-Encoder Reranker)."
    ),
    responses={
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
async def ask_policy_question(payload: AskRequest):
    question = payload.question

    # 1. Execute frozen hybrid retrieval pipeline
    results, stats = retrieve(
        query=question,
        config=DEFAULT_CONFIG,
        return_stats=True,
    )

    contexts = [doc for doc, score, meta in results]

    # 2. Generate grounded answer
    answer = generate_answer(question, contexts)

    # 3. Assess refusal state
    is_refusal = (
        not results
        or "not available in the provided documents" in answer.lower()
    )

    # 4. Extract structured citations
    sources = []
    if not is_refusal:
        for idx, (doc, score, meta) in enumerate(results, start=1):
            sources.append(
                CitationSource(
                    rank=idx,
                    title=meta.get("title", "Document"),
                    source_file=meta.get("source", "Unknown file"),
                    chunk_uid=meta.get("chunk_uid", f"chunk_{idx}"),
                    rerank_score=round(float(meta.get("rerank_score", score)), 3),
                    snippet=doc.strip(),
                )
            )

    return AskResponse(
        question=question,
        answer=answer,
        is_refusal=is_refusal,
        sources=sources,
    )


# =====================================================================
# 3. SQL EMPLOYEE ENDPOINT
# =====================================================================

@app.get(
    "/api/v1/employees/{employee_id}",
    response_model=EmployeeResponse,
    tags=["Structured Operational Data"],
    summary="Get Employee Profile",
    description="Retrieves an employee's details and direct manager profile from PostgreSQL.",
    responses={
        404: {"model": ErrorResponse, "description": "Employee Not Found"},
        500: {"model": ErrorResponse, "description": "Database Error"},
    },
)
async def get_employee_endpoint(employee_id: str):
    emp = get_employee_summary(employee_id)
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee '{employee_id}' not found.",
        )
    return emp


# =====================================================================
# 4. SQL LEAVE ENDPOINT
# =====================================================================

@app.get(
    "/api/v1/employees/{employee_id}/leave",
    response_model=EmployeeLeaveResponse,
    tags=["Structured Operational Data"],
    summary="Get Employee Leave Balances",
    description="Retrieves an employee's PTO allocation, used days, remaining days, and category breakdown.",
    responses={
        404: {"model": ErrorResponse, "description": "Employee Not Found"},
        500: {"model": ErrorResponse, "description": "Database Error"},
    },
)
async def get_employee_leave_endpoint(employee_id: str):
    leave_summary = get_employee_leave_summary(employee_id)
    if not leave_summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee '{employee_id}' not found.",
        )
    return leave_summary


# =====================================================================
# 5. SQL TRAVEL ENDPOINT
# =====================================================================

@app.get(
    "/api/v1/employees/{employee_id}/travel",
    response_model=EmployeeTravelResponse,
    tags=["Structured Operational Data"],
    summary="Get Employee Travel Summary",
    description="Retrieves an employee's travel expense totals, status rollups, and category breakdown.",
    responses={
        404: {"model": ErrorResponse, "description": "Employee Not Found"},
        500: {"model": ErrorResponse, "description": "Database Error"},
    },
)
async def get_employee_travel_endpoint(employee_id: str):
    travel_summary = get_employee_travel_summary(employee_id)
    if not travel_summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee '{employee_id}' not found.",
        )
    return travel_summary


# =====================================================================
# 6. MULTI-TURN CONVERSATIONAL AGENT ENDPOINTS (PHASE 6)
# =====================================================================

@app.post(
    "/api/v1/agent/chat",
    response_model=AgentChatResponse,
    tags=["Conversational Agent"],
    summary="Multi-Turn Agent Conversation",
    description=(
        "Executes a multi-turn conversation with the Enterprise Support AI Agent. "
        "Maintains isolated in-memory session history, coordinates tool calls across "
        "PostgreSQL operational records and hybrid RAG policies, and returns synthesized answers with citations."
    ),
    responses={
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
async def agent_chat_endpoint(payload: AgentChatRequest):
    try:
        agent_res = run_agent(
            user_query=payload.message,
            session_id=payload.session_id,
        )

        # Map steps to response schema
        steps_response = [
            AgentStepResponse(
                step_number=s.step_number,
                tool_name=s.tool_name,
                tool_args=s.tool_args,
                tool_result=s.tool_result,
                status=s.status,
                duration_ms=s.duration_ms,
                error=s.error,
            )
            for s in agent_res.steps
        ]

        # Map execution trace if present
        trace_response = None
        if agent_res.trace is not None:
            trace_response = AgentExecutionTraceResponse(
                session_id=agent_res.trace.session_id,
                total_steps=agent_res.trace.total_steps,
                total_duration_ms=agent_res.trace.total_duration_ms,
                used_rag=agent_res.trace.used_rag,
                status=agent_res.trace.status,
                tools_invoked=agent_res.trace.tools_invoked,
            )

        # Map citations to CitationSource schema
        citations_response: list[CitationSource] = []
        for c in agent_res.citations:
            try:
                citations_response.append(
                    CitationSource(
                        rank=int(c.get("rank", 1)),
                        title=str(c.get("title", "Document")),
                        source_file=str(c.get("source_file", "Unknown file")),
                        chunk_uid=str(c.get("chunk_uid", "chunk")),
                        rerank_score=float(c.get("rerank_score", 0.0)),
                        snippet=str(c.get("snippet", "")),
                    )
                )
            except Exception:
                continue

        return AgentChatResponse(
            session_id=agent_res.session_id or payload.session_id,
            query=agent_res.query,
            answer=agent_res.final_answer,
            status=agent_res.status,
            steps=steps_response,
            total_steps=agent_res.total_steps,
            duration_ms=agent_res.duration_ms,
            used_rag=agent_res.used_rag,
            citations=citations_response,
            trace=trace_response,
        )

    except DatabaseError:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "A database error occurred while the agent was processing your inquiry.",
                "error_type": "DatabaseError",
            },
        )
    except Exception as e:
        logger.error(f"Unhandled error in agent_chat_endpoint: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal error occurred while processing the agent conversation.",
                "error_type": "AgentError",
            },
        )


@app.post(
    "/api/v1/agent/sessions/{session_id}/clear",
    response_model=SessionClearResponse,
    tags=["Conversational Agent"],
    summary="Clear Conversation Session History",
    description="Clears all conversational context and message history for the given session ID.",
)
async def clear_session_endpoint(session_id: str):
    clean_id = session_id.strip()
    default_session_store.clear_session(clean_id)
    delete_thread_checkpoints(get_default_checkpointer(), clean_id)
    return SessionClearResponse(
        session_id=clean_id,
        status="cleared",
        message=f"Session '{clean_id}' conversation history has been cleared.",
    )


@app.delete(
    "/api/v1/agent/sessions/{session_id}",
    response_model=SessionClearResponse,
    tags=["Conversational Agent"],
    summary="Delete Conversation Session",
    description="Deletes the conversation session completely from in-memory storage.",
)
async def delete_session_endpoint(session_id: str):
    clean_id = session_id.strip()
    default_session_store.delete_session(clean_id)
    delete_thread_checkpoints(get_default_checkpointer(), clean_id)
    return SessionClearResponse(
        session_id=clean_id,
        status="deleted",
        message=f"Session '{clean_id}' has been deleted.",
    )


# =====================================================================
# 7. HUMAN-IN-THE-LOOP APPROVAL ENDPOINT (PHASE 7 TASK 4)
# =====================================================================

@app.post(
    "/api/v1/agent/approvals/{approval_id}",
    response_model=ApprovalDecisionResponse,
    tags=["Conversational Agent"],
    summary="Submit Human Approval Decision",
    description="Submits an explicit operator decision ('approve' or 'reject') to resume an approval-paused agent workflow.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid Decision or Missing Request"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
async def submit_approval_decision_endpoint(approval_id: str, payload: ApprovalDecisionRequest):
    clean_appr_id = approval_id.strip()
    clean_decision = payload.decision.strip().lower()

    if clean_decision not in ("approve", "reject"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision must be explicitly 'approve' or 'reject'.",
        )

    res = resume_multi_agent_approval(
        approval_id=clean_appr_id,
        decision=clean_decision,
        expected_session_id=payload.session_id,
    )

    if res.status == "error":
        lower_ans = res.final_answer.lower()
        if "not found" in lower_ans or "expired" in lower_ans:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=res.final_answer,
            )
        if "authorization" in lower_ans or "does not belong" in lower_ans:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=res.final_answer,
            )
        if "already" in lower_ans or "invalid" in lower_ans or "not in a pending state" in lower_ans or "mismatch" in lower_ans:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=res.final_answer,
            )

    trace_response = None
    if res.trace is not None:
        trace_response = AgentExecutionTraceResponse(
            session_id=res.trace.session_id,
            total_steps=res.trace.total_steps,
            total_duration_ms=res.trace.total_duration_ms,
            used_rag=res.trace.used_rag,
            status=res.trace.status,
            tools_invoked=res.trace.tools_invoked,
        )

    return ApprovalDecisionResponse(
        approval_id=clean_appr_id,
        decision=clean_decision,
        status=res.status,
        answer=res.final_answer,
        duration_ms=res.duration_ms,
        trace=trace_response,
    )

