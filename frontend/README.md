# Enterprise Support AI Agent — Modern Web Frontend

A modern, responsive, accessible, and type-safe Next.js web application for the **Enterprise Support AI Agent**.

This frontend serves as the primary showcase interface consuming the existing FastAPI backend services for hybrid RAG policy retrieval, structured PostgreSQL operational data queries, LangGraph multi-agent reasoning, durable session checkpointing, and human-in-the-loop approvals.

---

## 🛠️ Technology Stack

- **Framework**: [Next.js 16 (App Router)](https://nextjs.org/)
- **Core**: React 19, TypeScript 5
- **Styling**: [Tailwind CSS 4](https://tailwindcss.com/) with native Dark/Light mode theme system
- **Icons**: [Lucide React](https://lucide.dev/)
- **Client Architecture**: Strongly-typed API client (`lib/api/client.ts`) with sanitized error handling (`lib/api/errors.ts`)
- **State Management**: Zero heavy dependencies — clean native React state with localStorage persistence for theme preferences and active session IDs

---

## 🎨 Enterprise Product Shell & UX Features

- **Cohesive Product Shell**: Unified workspace header with brand identity, live backend health badge with diagnostic latency popover, theme toggle (Light / Dark / System), and an interactive **Architecture & Tech Specs** modal.
- **Accessible Navigation**: ARIA-compliant tablist (`role="tablist"`, `aria-selected`, `aria-controls`) for seamless mode switching between **Policy Assistant** and **Enterprise AI Agent** without full page reloads.
- **Live Backend Diagnostics**: Real-time health polling (`GET /health`) displaying ping latency, subsystem status, and actionable terminal recovery commands when backend is offline.
- **Interactive System Architecture Modal**: Recruiter/interviewer showcase modal detailing the end-to-end stack: Next.js frontend, FastAPI Gateway, Hybrid RAG (ChromaDB + BM25), PostgreSQL schema, LangGraph Multi-Agent supervisor, and Checkpointing persistence.

---

## 💬 Workspaces

### 1. Policy Assistant Workspace

The **Policy Assistant** workspace provides a grounded enterprise policy Q&A chat experience:

1. **Interactive Chat Workspace**: Clean, conversational thread interface with empty state onboarding, auto-scrolling, clear chat controls, and latency tracking.
2. **Grounded RAG Integration**: Consumes `POST /api/v1/ask` strictly using the hybrid retrieval pipeline (Dense ChromaDB + Sparse BM25 + Reciprocal Rank Fusion + Cross-Encoder Reranker).
3. **Verifiable Citations**: Expandable source citations with ranked document titles, source filenames, chunk UIDs, rerank relevance scores, and verbatim passage excerpts with one-click copy.
4. **Deterministic Refusal Safeguards**: Distinctive refusal alerts whenever internal policy evidence is insufficient, preventing hallucinations.
5. **Retrieval & Grounding Diagnostics**: Collapsible inspection panel showing pipeline stages, best rerank score, and latency metrics.
6. **Suggested Policy Inquiries**:
   - *"What is the meal per diem allowance for domestic travel?"*
   - *"How much does the company match 401(k) contributions?"*
   - *"What are the core collaboration hours for remote employees?"*
   - *"What is the company pet insurance reimbursement policy?"*

### 2. Enterprise AI Agent Workspace

The **Enterprise AI Agent** workspace provides a multi-turn, tool-calling assistant coordinating across SQL records, policy knowledge, and human governance:

1. **Multi-Turn Session State**: Isolated conversational sessions tracked by `session_id`. Follow-up questions (e.g., *"What is the leave balance for E1001?"* followed by *"What about their manager?"*) resolve conversational context automatically via the backend.
2. **Multi-Agent Workflow Timeline**: Visual, responsive execution diagram mapping the user inquiry from **Supervisor Router** -> **Specialized Workers** (`Employee Records`, `Travel & Expense`, `HR Policy`) -> **Tool Calls** -> **Final Synthesis**. Automatically adjusts to vertical layout on mobile devices.
3. **Collapsible Tool Activity**: Expandable inspection accordion displaying tool names, arguments, execution durations, and sanitized observation results formatted as syntax-highlighted JSON without exposing sensitive credentials or raw SQL.
4. **RAG Policy Evidence**: Seamless integration of verifiable policy citations whenever the agent invokes the `ask_policy` tool.
5. **Execution Summary Telemetry**: Compact summary card reporting execution status, latency, step count, workers involved, and citation counts.
6. **Human-in-the-Loop (HITL) Governance**: Interactive approval card when sensitive operations are gated (`pending_approval`), allowing human operators to **Approve & Continue** or **Reject** with review notes via `POST /api/v1/agent/approvals/{approval_id}`.
7. **Session Management Controls**:
   - **New Session**: Creates a fresh session ID for a clean thread.
   - **Clear History**: Two-step confirmation invoking `POST /api/v1/agent/sessions/{id}/clear` to reset memory & checkpoints.
   - **Delete Session**: Two-step confirmation invoking `DELETE /api/v1/agent/sessions/{id}` to purge session data.
8. **Categorized Technical Demo Prompts**:
   - 👤 Employee Profile: *"Show employee E1001's information."*
   - 🏖️ Leave Balances: *"How many annual leave days does E1001 have left?"*
   - ✈️ Travel Spend: *"How much has E1001 spent on travel?"*
   - 👔 Manager Hierarchy: *"Who is E1001's manager?"*
   - 🔄 Multi-Step Query: *"How much has E1001 spent on travel, and who is their manager?"*
   - 🌐 Cross-Domain: *"How much has E1001 spent on travel and what is the domestic meal allowance?"*
   - 🔐 HITL Approval: *"Show confidential compensation details for employee E1000."*

---

## 🏛️ Architecture

```text
┌─────────────────────────────────────────────────────────┐
│               Next.js Web Frontend                      │
│             TypeScript + Tailwind CSS                   │
│                                                         │
│  Components (Header, StatusBadge, PolicyChat, Agent...) │
│  API Client (EnterpriseApiClient singleton)             │
│  Typed Models (Health, Ask, AgentChat, Approvals)       │
│  Theme System (Dark / Light / System with CSS vars)     │
└────────────────────────────┬────────────────────────────┘
                             │
                             │ HTTP REST (JSON)
                             ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI REST Backend                       │
│              (http://127.0.0.1:8000)                    │
│                                                         │
│  GET  /health                                           │
│  POST /api/v1/ask                                       │
│  GET  /api/v1/employees/{id}                            │
│  GET  /api/v1/employees/{id}/leave                      │
│  GET  /api/v1/employees/{id}/travel                     │
│  POST /api/v1/agent/chat                                │
│  POST /api/v1/agent/sessions/{id}/clear                 │
│  DELETE /api/v1/agent/sessions/{id}                     │
│  POST /api/v1/agent/approvals/{approval_id}             │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
                    Existing AI System
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
     Hybrid RAG          LangGraph         PostgreSQL
  (ChromaDB + BM25)    (Multi-Agent)     (Enterprise DB)
```

---

## ⚙️ Environment Configuration

The API client reads the FastAPI backend location from `NEXT_PUBLIC_API_BASE_URL`.

Create `.env.local` (or copy from `.env.example`):

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

---

## 🚀 Getting Started

### 1. Start FastAPI Backend

In your main Python environment:

```bash
uvicorn app.api.main:app --reload --port 8000
```

### 2. Start Next.js Development Server

```bash
cd frontend
npm install
npm run dev
```

The application will be accessible at:
👉 **`http://localhost:3000`**

### 3. Build for Production

```bash
npm run build
npm start
```

---

## 🧪 Automated Testing Foundation

The frontend test suite is built with **Vitest**, **React Testing Library**, **jsdom**, and **@testing-library/jest-dom** for fast, 100% deterministic local unit and component verification without external network or backend dependencies.

### 1. Running Tests

From the `frontend/` directory:

```bash
# Run tests in interactive watch mode
npm test

# Run all tests once in CI/deterministic mode
npm run test:run

# Run tests with V8 code coverage report
npm run test:coverage
```

### 2. Test Architecture & Coverage

The test suite consists of **25 test files** comprising **112 test methods** covering:

- **API Client & Sanitization** (`__tests__/api/`): Unit tests for `EnterpriseApiClient` covering all REST endpoints (`/health`, `/api/v1/ask`, `/api/v1/employees/...`, `/api/v1/agent/chat`, `/api/v1/agent/approvals/{id}`, session clear/delete), HTTP methods, headers, 404/422/500 status codes, network failures, and sanitized user-facing error formatting without raw stack traces.
- **Type & Contract Verification** (`__tests__/contracts/`): Verifies frontend TypeScript interfaces (`api.ts`, `chat.ts`, `agent.ts`) correctly consume realistic FastAPI Pydantic response fixtures.
- **Policy Assistant Components** (`__tests__/policy/`): `MessageComposer`, `CitationCard`, `CitationList`, `RetrievalDetails`, `EmptyState`, `ChatMessage`, and `PolicyChatWorkspace`.
- **Enterprise AI Agent Components** (`__tests__/agent/`): `AgentComposer`, `AgentMessage`, `WorkflowTimeline`, `ToolActivity`, `ApprovalCard`, `ExecutionSummary`, `SessionControlBar`, `AgentEmptyState`, and `AgentChatWorkspace`.
- **Theme, Accessibility & Product Shell** (`__tests__/components/`): `ThemeToggle`, `ModeSelector` (ARIA tablist), `Header`, `BackendStatusBadge`, `SystemInfoCard`, and `ArchitectureModal`.

### 3. Isolation & Mock Boundaries

All frontend tests run in full isolation:
- **Zero Network / API Calls**: Global `fetch` is mocked deterministically via `vi.fn()`.
- **Browser APIs**: `window.matchMedia`, `navigator.clipboard`, and `Element.prototype.scrollIntoView` are mocked in `vitest.setup.ts`.
- **No External Services**: Zero Groq tokens, zero PostgreSQL queries, and zero ChromaDB operations are executed.
- **Automatic Teardown**: React component DOM trees and mock implementations are automatically reset between every test (`cleanup()`, `vi.clearAllMocks()`).

### 4. Integration Testing (FastAPI ↔ Next.js Boundary)

The integration test suite (`frontend/__tests__/integration/`) proves end-to-end communication between the Next.js typed API client and the actual FastAPI service layer:

- **Integration Architecture**:
  ```text
  Next.js Typed Client (EnterpriseApiClient)
          │ HTTP Request (fetch)
          ▼
  FastAPI Server (uvicorn on port 8089)
          │ Route dispatch & Pydantic validation
          ▼
  Deterministic Mock Backend (0 Groq tokens, 0 network, in-memory state)
          │ Pydantic serialization & exception handlers
          ▼
  Next.js Typed Client Error / Response Parsing
  ```

- **Integration Test Files**:
  - `__tests__/integration/api.integration.test.ts`: Tests `GET /health`, `GET /api/v1/employees/{id}`, `/leave`, `/travel`, missing employee 404s, database error 500 sanitization, and credential safety boundaries.
  - `__tests__/integration/policy.integration.test.ts`: Tests `POST /api/v1/ask` for grounded answers with structured citations, refusal states (`is_refusal: true`), FastAPI 422 validation errors (empty/whitespace queries), and 500 server error handling.
  - `__tests__/integration/agent.integration.test.ts`: Tests `POST /api/v1/agent/chat` (first turn, follow-up turn context continuity, multi-session isolation, 422 errors), `POST /api/v1/agent/approvals/{id}` (approve, reject, 403 session mismatch, 400 replay), session clear/delete, and secret masking.
- **Server Lifecycle**: Managed automatically via `globalSetup.ts` and `testServerHelper.ts` (boots Python server in `.venv` before test suites and shuts down cleanly after tests).
- **Mock vs Real Boundary**: Real HTTP networking, real FastAPI router, real Pydantic validation and response schemas, real CORS, and real error handlers; LLM synthesis and database lookups are deterministically mocked to avoid Groq token usage or live PostgreSQL dependencies.

### 5. Intentionally Deferred / Future Scope

The following areas are intentionally not included in this unit & integration test foundation:
- **End-to-End (E2E) Browser Automation**: Full-stack browser automation using Playwright or Cypress (scheduled for later dedicated tasks).
- **Live WebSocket / SSE Streaming**: Real-time server-sent events or streaming response chunks (current architecture uses synchronous REST endpoints).
- **Visual Regression Testing**: Pixel-by-pixel screenshot regression testing.

---

## 🧭 Project Structure

```text
frontend/
├── app/
│   ├── layout.tsx                # Root layout with fonts, theme script & metadata
│   ├── page.tsx                  # Landing dashboard & workspace switcher
│   └── globals.css               # Tailwind 4 styling, CSS theme vars, & scrollbars
├── components/
│   ├── Header.tsx                # Enterprise brand header with theme toggle & modal trigger
│   ├── ThemeToggle.tsx           # Dark/Light/System theme switcher with localStorage
│   ├── ArchitectureModal.tsx     # Technical specifications & system architecture modal
│   ├── BackendStatusBadge.tsx    # Live pinging FastAPI health status & latency popover
│   ├── ModeSelector.tsx          # Accessible ARIA tab switcher (Policy vs Agent)
│   ├── SystemInfoCard.tsx        # Collapsible diagnostics & API endpoint matrix
│   ├── policy/
│   │   ├── EmptyState.tsx        # Onboarding screen with verified policy queries
│   │   ├── CitationCard.tsx      # Source citation card with copy snippet
│   │   ├── CitationList.tsx      # Expandable container for verifiable sources
│   │   ├── RetrievalDetails.tsx  # Grounding diagnostics and rerank metrics
│   │   ├── ChatMessage.tsx       # User & Assistant chat message bubble formatting
│   │   ├── MessageComposer.tsx   # Multiline textarea with auto-resize & shortcut hints
│   │   ├── PolicyChatWorkspace.tsx # Full interactive Policy Assistant chat workspace
│   │   └── index.ts              # Policy components export
│   └── agent/
│       ├── AgentEmptyState.tsx   # Categorized technical demo query cards
│       ├── AgentMessage.tsx      # Polished agent response card with visual hierarchy
│       ├── WorkflowTimeline.tsx  # Responsive desktop & mobile multi-agent timeline
│       ├── ToolActivity.tsx      # Collapsible JSON tool execution inspector
│       ├── ExecutionSummary.tsx  # Status badges, step metrics, & worker tags
│       ├── ApprovalCard.tsx      # Enterprise HITL authorization card
│       ├── SessionControlBar.tsx # Session ID chip, two-step clear & delete controls
│       ├── AgentComposer.tsx     # Multiline composer with loading indicator & clear
│       ├── AgentChatWorkspace.tsx # Full Enterprise AI Agent chat workspace
│       └── index.ts              # Agent components export
├── lib/
│   └── api/
│       ├── client.ts             # Typed EnterpriseApiClient for all FastAPI endpoints
│       ├── errors.ts             # Sanitized error class (no leaks of DB / internal details)
│       └── index.ts              # Module exports
├── types/
│   ├── api.ts                    # TypeScript interfaces mirroring FastAPI Pydantic schemas
│   ├── chat.ts                   # Chat message and conversation state types
│   └── index.ts                  # Module exports
├── .env.example                  # Environment template
├── .env.local                    # Local environment overrides
├── package.json                  # Next.js dependencies & scripts
├── tsconfig.json                 # TypeScript configuration with `@/*` aliases
└── README.md                     # Frontend documentation
```

---

## ℹ️ Streamlit UI Compatibility

During the frontend migration phase, the legacy Streamlit showcase UI (`app/ui.py`) remains operational and available at `http://localhost:8501` as a secondary fallback.

