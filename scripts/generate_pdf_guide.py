"""
Generates an executive-grade, colorful, story-driven PDF report:
'Enterprise AI Agent Mastery Guide & Monetization Blueprint'
Saved directly to the user's Downloads folder.
"""

import os
import subprocess
import sys
from pathlib import Path

DOWNLOADS_DIR = Path(os.getenv("DOWNLOADS_DIR", str(Path.home() / "Downloads")))
OUTPUT_PDF = DOWNLOADS_DIR / "Enterprise_AI_Agent_Mastery_Guide.pdf"
HTML_PATH = DOWNLOADS_DIR / "temp_report_source.html"

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Enterprise AI Agent Mastery Guide & Monetization Blueprint</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

  @page {
    size: A4 portrait;
    margin: 14mm 12mm 14mm 12mm;
  }

  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }

  body {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: #1E293B;
    background: #FFFFFF;
    line-height: 1.55;
    font-size: 13px;
  }

  /* Cover Page */
  .cover {
    height: 100%;
    min-height: 260mm;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    background: linear-gradient(145deg, #0F172A 0%, #1E1B4B 50%, #311042 100%);
    color: #F8FAFC;
    padding: 35mm 22mm 25mm 22mm;
    border-radius: 16px;
    position: relative;
    overflow: hidden;
    page-break-after: always;
  }

  .cover::before {
    content: "";
    position: absolute;
    top: -80px;
    right: -80px;
    width: 320px;
    height: 320px;
    background: radial-gradient(circle, rgba(99, 102, 241, 0.45) 0%, rgba(147, 51, 234, 0) 70%);
    border-radius: 50%;
  }

  .cover::after {
    content: "";
    position: absolute;
    bottom: -60px;
    left: -60px;
    width: 280px;
    height: 280px;
    background: radial-gradient(circle, rgba(6, 182, 212, 0.35) 0%, rgba(59, 130, 246, 0) 70%);
    border-radius: 50%;
  }

  .cover-tag {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.25);
    backdrop-filter: blur(8px);
    padding: 6px 14px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #A5B4FC;
    width: fit-content;
  }

  .cover-title {
    font-size: 34px;
    font-weight: 800;
    line-height: 1.18;
    margin-top: 24px;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #FFFFFF 30%, #C7D2FE 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .cover-subtitle {
    font-size: 16px;
    color: #CBD5E1;
    font-weight: 400;
    margin-top: 14px;
    line-height: 1.45;
  }

  .cover-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 28px;
  }

  .badge-item {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(99, 102, 241, 0.35);
    padding: 8px 14px;
    border-radius: 8px;
    font-size: 11px;
    font-weight: 600;
    color: #E2E8F0;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .cover-footer {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    border-top: 1px solid rgba(255, 255, 255, 0.15);
    padding-top: 20px;
    font-size: 11px;
    color: #94A3B8;
  }

  /* Page Sections */
  .page-break {
    page-break-before: always;
  }

  .section {
    margin-bottom: 22px;
    break-inside: avoid;
  }

  .chapter-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 2px solid #E2E8F0;
  }

  .chapter-num {
    background: linear-gradient(135deg, #4F46E5, #7C3AED);
    color: #FFFFFF;
    font-size: 12px;
    font-weight: 800;
    padding: 4px 10px;
    border-radius: 6px;
    letter-spacing: 0.05em;
  }

  .chapter-title {
    font-size: 20px;
    font-weight: 800;
    color: #0F172A;
    letter-spacing: -0.01em;
  }

  /* Story Banner */
  .story-card {
    background: linear-gradient(135deg, #F8FAFC 0%, #EEF2FF 100%);
    border-left: 4px solid #6366F1;
    border-radius: 0 12px 12px 0;
    padding: 14px 18px;
    margin-bottom: 18px;
    box-shadow: 0 2px 8px rgba(99, 102, 241, 0.06);
  }

  .story-title {
    font-weight: 700;
    color: #3730A3;
    font-size: 13px;
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 6px;
  }

  .story-body {
    font-style: italic;
    color: #475569;
    font-size: 12.5px;
  }

  /* Content Cards & Grids */
  .grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    margin-bottom: 16px;
  }

  .grid-3 {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 12px;
    margin-bottom: 16px;
  }

  .card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 14px;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.03);
    break-inside: avoid;
  }

  .card-primary {
    border-top: 3px solid #4F46E5;
  }

  .card-success {
    border-top: 3px solid #10B981;
  }

  .card-warning {
    border-top: 3px solid #F59E0B;
  }

  .card-info {
    border-top: 3px solid #06B6D4;
  }

  .card h4 {
    font-size: 13.5px;
    font-weight: 700;
    color: #0F172A;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .card p, .card li {
    font-size: 12px;
    color: #475569;
  }

  .card ul {
    list-style: none;
    margin-top: 6px;
  }

  .card ul li {
    position: relative;
    padding-left: 14px;
    margin-bottom: 4px;
  }

  .card ul li::before {
    content: "•";
    position: absolute;
    left: 2px;
    color: #6366F1;
    font-weight: bold;
  }

  /* Architecture Box */
  .arch-box {
    background: #0F172A;
    color: #F8FAFC;
    padding: 16px;
    border-radius: 10px;
    margin-bottom: 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    line-height: 1.45;
  }

  .arch-box .highlight {
    color: #38BDF8;
    font-weight: 600;
  }

  .arch-box .accent {
    color: #A78BFA;
    font-weight: 600;
  }

  .arch-box .green {
    color: #34D399;
  }

  /* Code Block */
  .code-block {
    background: #1E293B;
    color: #F1F5F9;
    border-radius: 8px;
    padding: 12px 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    margin-bottom: 14px;
    overflow-x: hidden;
    position: relative;
  }

  .code-header {
    display: flex;
    justify-content: space-between;
    font-size: 10px;
    text-transform: uppercase;
    color: #94A3B8;
    font-weight: 700;
    margin-bottom: 8px;
    border-bottom: 1px solid #334155;
    padding-bottom: 4px;
  }

  .code-cmd {
    color: #38BDF8;
    font-weight: 600;
  }

  .code-comment {
    color: #64748B;
  }

  /* Table */
  table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 16px;
    font-size: 11.5px;
    break-inside: avoid;
  }

  th {
    background: #F1F5F9;
    color: #1E293B;
    font-weight: 700;
    text-align: left;
    padding: 8px 10px;
    border: 1px solid #CBD5E1;
  }

  td {
    padding: 8px 10px;
    border: 1px solid #E2E8F0;
    color: #334155;
    vertical-align: middle;
  }

  tr:nth-child(even) td {
    background: #F8FAFC;
  }

  /* Highlight pill */
  .pill {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
  }

  .pill-green {
    background: #DCFCE7;
    color: #15803D;
  }

  .pill-blue {
    background: #DBEAFE;
    color: #1D4ED8;
  }

  .pill-purple {
    background: #F3E8FF;
    color: #7E22CE;
  }

  .pill-amber {
    background: #FEF3C7;
    color: #B45309;
  }

  /* Money Cards */
  .money-card {
    background: linear-gradient(135deg, #FFFFFF 0%, #F0FDF4 100%);
    border: 1px solid #BBF7D0;
    border-radius: 12px;
    padding: 14px;
    margin-bottom: 12px;
    box-shadow: 0 2px 6px rgba(22, 163, 74, 0.08);
    break-inside: avoid;
  }

  .money-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 6px;
  }

  .money-title {
    font-size: 14px;
    font-weight: 800;
    color: #14532D;
  }

  .money-price {
    font-size: 15px;
    font-weight: 800;
    color: #16A34A;
    background: #DCFCE7;
    padding: 2px 10px;
    border-radius: 6px;
  }

  .money-desc {
    font-size: 12px;
    color: #374151;
    margin-bottom: 8px;
  }

  .step-num {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 22px;
    height: 22px;
    background: #4F46E5;
    color: white;
    border-radius: 50%;
    font-size: 11px;
    font-weight: 700;
    margin-right: 6px;
  }

  .checklist {
    list-style: none;
  }

  .checklist li {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: #1E293B;
    padding: 6px 0;
    border-bottom: 1px dashed #E2E8F0;
  }

  .checkbox {
    width: 15px;
    height: 15px;
    border: 2px solid #4F46E5;
    border-radius: 4px;
    display: inline-block;
  }
</style>
</head>
<body>

<!-- COVER PAGE -->
<div class="cover">
  <div>
    <div class="cover-tag">🚀 Production Blueprint & Strategic Playbook</div>
    <h1 class="cover-title">Enterprise Support<br>AI Agent System</h1>
    <p class="cover-subtitle">
      A Complete Hands-On Guide to Architecture, Local Execution, 100% Free Cloud Deployment, Recruiter Demonstrations & High-Yield Monetization.
    </p>

    <div class="cover-badges">
      <div class="badge-item">⚡ LangGraph Multi-Agent Engine</div>
      <div class="badge-item">🔍 Hybrid RAG (MiniLM + BM25)</div>
      <div class="badge-item">🎯 Cross-Encoder Reranker</div>
      <div class="badge-item">🛡️ Human-in-the-Loop (HITL) Gate</div>
      <div class="badge-item">🐘 PostgreSQL 16 State</div>
      <div class="badge-item">⚛️ Next.js 16 + React 19 UI</div>
      <div class="badge-item">💸 $0/Month Cloud Blueprint</div>
    </div>
  </div>

  <div class="cover-footer">
    <div>
      <strong>Author & Solutions Architect:</strong> AI Engineering Team<br>
      <strong>Stack:</strong> FastAPI • Next.js • PostgreSQL • ChromaDB • Groq
    </div>
    <div style="text-align: right;">
      <strong>Classification:</strong> Confidential Enterprise Asset<br>
      <strong>Date of Issue:</strong> September 2026
    </div>
  </div>
</div>

<!-- CHAPTER 1: THE STORY & ARCHITECTURE -->
<div class="section">
  <div class="chapter-header">
    <span class="chapter-num">CHAPTER 1</span>
    <h2 class="chapter-title">The Story: Why Enterprise AI Needs a Shield</h2>
  </div>

  <div class="story-card">
    <div class="story-title">📖 The Real-World Conflict</div>
    <div class="story-body">
      "Last year, an employee asked a popular internal AI chatbot how many remote days were allowed per month. The naive LLM confidently answered: 'Unlimited! Enjoy working from the beach.' Three months later, HR was engulfed in chaos. In an enterprise, an AI hallucination is not a typo—it is legal, financial, and operational liability."
    </div>
  </div>

  <p style="margin-bottom: 14px; font-size: 12.5px; color: #334155;">
    This project was engineered to solve the <strong>Three Deadly Sins of Corporate LLM Deployments</strong>:
  </p>

  <div class="grid-3">
    <div class="card card-warning">
      <h4>🚫 1. Hallucinations</h4>
      <p>Standard LLMs guess policies when ungrounded. Our system pairs <strong>Dense Embeddings</strong> + <strong>Sparse BM25</strong> + <strong>Cross-Encoder Reranker</strong> to force an explicit <em>"I don't know"</em> refusal if internal verification fails.</p>
    </div>
    <div class="card card-primary">
      <h4>🛡️ 2. Runaway Actions</h4>
      <p>Autonomous agents querying salary tables or triggering payouts destroy compliance. Our <strong>LangGraph Human-in-the-Loop (HITL)</strong> interceptor halts the graph until a human manager approves or rejects the action.</p>
    </div>
    <div class="card card-info">
      <h4>🔄 3. State Amnesia</h4>
      <p>Chatbots forget mid-turn state during server restarts. We use <strong>PostgreSQL Durable Checkpointing (PostgresSaver)</strong> so approval workflows survive cloud cold starts without data loss.</p>
    </div>
  </div>

  <h3 style="font-size: 14px; font-weight: 700; color: #0F172A; margin: 16px 0 8px 0;">The Master Orchestration Flow</h3>
  <div class="arch-box">
<span class="highlight">[User Browser / Evaluator]</span> ──(HTTP)──&gt; <span class="highlight">[FastAPI Gateway (:8000)]</span>
                                       │
                                       ▼
                       <span class="accent">[LangGraph Supervisor Router]</span>
                        ├──&gt; <span class="green">[HR Policy Worker]</span> ──&gt; Hybrid RAG (Chroma + BM25 + CrossEncoder)
                        ├──&gt; <span class="green">[Employee Records]</span> ──&gt; PostgreSQL Schema (Profiles, Managers)
                        └──&gt; <span class="green">[Travel &amp; Expense]</span>  ──&gt; PostgreSQL Ledger (Budgets, Per Diem)
                                       │
            <span class="accent">IF Sensitive Action (e.g. Salary E1000) ──&gt; [HITL Approval Gate] ──&gt; PAUSE STATE</span>
                                       │ (Awaiting Human Decision via UI)
                        <span class="green">[PostgresSaver Checkpointer]</span> (Preserves Graph State)
  </div>
</div>

<!-- CHAPTER 2: HOW TO RUN IT -->
<div class="section page-break">
  <div class="chapter-header">
    <span class="chapter-num">CHAPTER 2</span>
    <h2 class="chapter-title">The Flight Deck: How to Run the System</h2>
  </div>

  <p style="margin-bottom: 12px; font-size: 12.5px; color: #334155;">
    You have two launch methods: <strong>One-Click Docker Compose</strong> (recommended for demos) and <strong>Native Local Execution</strong> (for active code development).
  </p>

  <div class="card card-primary" style="margin-bottom: 16px;">
    <h4 style="color: #4F46E5;"><span class="step-num">A</span> Method 1: The 60-Second Docker Flight Check (Recommended)</h4>
    <p style="margin-bottom: 10px;">Docker spins up the entire 3-tier enterprise constellation in isolated containers with persistence.</p>
    
    <div class="code-block">
      <div class="code-header"><span>PowerShell (Run from project root)</span><span>Step 1 of 2</span></div>
      <span class="code-comment"># Ensure .env contains your GROQ_API_KEY</span><br>
      <span class="code-cmd">docker-compose up --build -d</span>
    </div>

    <div class="code-block">
      <div class="code-header"><span>Verification Endpoints</span><span>Step 2 of 2</span></div>
      <span class="code-comment"># Verify all three tiers are healthy:</span><br>
      • <span style="color:#A5B4FC;">Frontend UI:</span> http://localhost:3000<br>
      • <span style="color:#A5B4FC;">Backend Swagger API Docs:</span> http://localhost:8000/docs<br>
      • <span style="color:#A5B4FC;">FastAPI Health Check:</span> http://localhost:8000/health
    </div>
  </div>

  <div class="card card-info">
    <h4 style="color: #0284C7;"><span class="step-num">B</span> Method 2: Native Developer Flight Check</h4>
    <p style="margin-bottom: 8px;">Run directly in your local Python and Node.js virtual environments:</p>
    
    <div class="code-block">
      <div class="code-header"><span>Terminal 1: Backend & Database Setup</span><span>Port 8000</span></div>
      <span class="code-comment"># 1. Activate venv & install packages</span><br>
      <span class="code-cmd">.\.venv\Scripts\Activate.ps1</span><br>
      <span class="code-cmd">pip install -r requirements.txt</span><br><br>
      <span class="code-comment"># 2. Initialize DB Schema & Seed Demo Records</span><br>
      <span class="code-cmd">python -c "from app.database import init_db, seed_db; init_db(); seed_db()"</span><br><br>
      <span class="code-comment"># 3. Ingest Policy Documents into ChromaDB & BM25</span><br>
      <span class="code-cmd">python -c "from app.vector_store import ingest_directory; ingest_directory('data/documents', reset=True)"</span><br><br>
      <span class="code-comment"># 4. Launch FastAPI REST Server</span><br>
      <span class="code-cmd">uvicorn app.api.main:app --reload --port 8000</span>
    </div>

    <div class="code-block">
      <div class="code-header"><span>Terminal 2: Next.js Modern Frontend</span><span>Port 3000</span></div>
      <span class="code-cmd">cd frontend</span><br>
      <span class="code-cmd">npm install</span><br>
      <span class="code-cmd">npm run dev</span><br>
      <span class="code-comment"># Open browser at http://localhost:3000</span>
    </div>
  </div>
</div>

<!-- CHAPTER 3: HOW TO USE & TEST -->
<div class="section page-break">
  <div class="chapter-header">
    <span class="chapter-num">CHAPTER 3</span>
    <h2 class="chapter-title">The Field Mission: How to Use & Showcase</h2>
  </div>

  <p style="margin-bottom: 14px; font-size: 12.5px; color: #334155;">
    Once on <strong>http://localhost:3000</strong>, execute these four choreographed demo missions to showcase the full range of enterprise capabilities.
  </p>

  <div class="grid-2">
    <div class="card card-success">
      <h4><span class="pill pill-green">Demo 1</span> Grounded Policy Q&amp;A</h4>
      <p style="margin-bottom: 6px;"><strong>Select:</strong> Policy Assistant Mode</p>
      <p style="margin-bottom: 6px;"><strong>Ask:</strong> <em>"What is the meal per diem allowance for domestic travel?"</em></p>
      <ul>
        <li><strong>Output:</strong> Exact $75/day rate.</li>
        <li><strong>Highlight:</strong> Expand citations to show <code>travel_policy.md</code>, chunk UID, and Cross-Encoder score &gt; 2.5.</li>
      </ul>
    </div>

    <div class="card card-warning">
      <h4><span class="pill pill-amber">Demo 2</span> Zero-Hallucination Refusal</h4>
      <p style="margin-bottom: 6px;"><strong>Select:</strong> Policy Assistant Mode</p>
      <p style="margin-bottom: 6px;"><strong>Ask:</strong> <em>"What is our pet insurance reimbursement policy?"</em></p>
      <ul>
        <li><strong>Output:</strong> Crisp, amber Refusal Card.</li>
        <li><strong>Highlight:</strong> Reranker drops low-relevance chunks below threshold. The LLM explicitly states the policy does not exist.</li>
      </ul>
    </div>

    <div class="card card-primary">
      <h4><span class="pill pill-blue">Demo 3</span> Multi-Domain Cross-Query</h4>
      <p style="margin-bottom: 6px;"><strong>Select:</strong> AI Agent Mode</p>
      <p style="margin-bottom: 6px;"><strong>Ask:</strong> <em>"How much has E1001 spent on travel and what is the domestic meal allowance?"</em></p>
      <ul>
        <li><strong>Output:</strong> SQL ledger query + RAG synthesis.</li>
        <li><strong>Highlight:</strong> Timeline shows supervisor calling Travel Worker, then Policy Worker, and merging answers seamlessly.</li>
      </ul>
    </div>

    <div class="card card-info">
      <h4><span class="pill pill-purple">Demo 4</span> Human-in-the-Loop (HITL)</h4>
      <p style="margin-bottom: 6px;"><strong>Select:</strong> AI Agent Mode</p>
      <p style="margin-bottom: 6px;"><strong>Ask:</strong> <em>"Show confidential salary records for employee E1000."</em></p>
      <ul>
        <li><strong>Output:</strong> Workflow halts. Amber Approval Card appears.</li>
        <li><strong>Highlight:</strong> State saved in PostgreSQL. Click <strong>Approve</strong> to proceed or <strong>Reject</strong> to terminate with zero leaks!</li>
      </ul>
    </div>
  </div>
</div>

<!-- CHAPTER 4: DEPLOYING 100% FREELY -->
<div class="section">
  <div class="chapter-header">
    <span class="chapter-num">CHAPTER 4</span>
    <h2 class="chapter-title">The Zero-Dollar Heist: Deploy for $0/Month</h2>
  </div>

  <p style="margin-bottom: 12px; font-size: 12.5px; color: #334155;">
    You can deploy this multi-agent system to public internet URLs without paying a single dollar using the <strong>Zero-Cost Modern Cloud Architecture</strong>:
  </p>

  <table>
    <thead>
      <tr>
        <th>Tier / Role</th>
        <th>Free Cloud Provider</th>
        <th>Free Allocation</th>
        <th>Engineering Configuration</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Frontend Web UI</strong></td>
        <td><span class="pill pill-blue">Vercel Hobby</span></td>
        <td>100 GB Bandwidth / Mo (Unlimited visits)</td>
        <td>Deploy <code>./frontend</code> directly; Set <code>NEXT_PUBLIC_API_BASE_URL</code></td>
      </tr>
      <tr>
        <td><strong>Relational Database</strong></td>
        <td><span class="pill pill-green">Neon Serverless</span></td>
        <td>0.5 GB Storage, Postgres 16, Auto-suspend</td>
        <td>Initialize schema and LangGraph tables with pooled connection string</td>
      </tr>
      <tr>
        <td><strong>LLM Inference</strong></td>
        <td><span class="pill pill-purple">Groq Cloud API</span></td>
        <td>30 Requests / Min (Llama 3.3 70B)</td>
        <td>Zero local RAM overhead; sub-second completion latency</td>
      </tr>
      <tr>
        <td><strong>Backend API (Choice 1)</strong></td>
        <td><span class="pill pill-green">Hugging Face Spaces</span></td>
        <td><strong>2 vCPU + 16 GB RAM (100% FREE)</strong></td>
        <td>Easiest free deployment; handles PyTorch &amp; CrossEncoder with ease</td>
      </tr>
      <tr>
        <td><strong>Backend API (Choice 2)</strong></td>
        <td><span class="pill pill-amber">Render Free Web</span></td>
        <td>750 Hours / Mo (512 MB RAM limit)</td>
        <td>Requires ONNX Runtime model optimization to prevent 512MB OOM</td>
      </tr>
    </tbody>
  </table>

  <div class="card card-success">
    <h4 style="color: #15803D;">💡 Pro Deployment Recommendation: The Hugging Face + Vercel Duo</h4>
    <p style="font-size: 12px; color: #1E293B;">
      While Render Free provides 512 MB RAM, <strong>Hugging Face Spaces offers 16 GB RAM completely free</strong> for Docker containers. Deploying the backend Dockerfile to Hugging Face Spaces and the Next.js frontend to Vercel provides a blazing-fast, rock-solid, 100% free production showcase!
    </p>
  </div>
</div>

<!-- CHAPTER 5: HOW TO EARN MONEY -->
<div class="section page-break">
  <div class="chapter-header">
    <span class="chapter-num">CHAPTER 5</span>
    <h2 class="chapter-title">The Monetization Playbook: How to Earn Cash</h2>
  </div>

  <p style="margin-bottom: 12px; font-size: 12.5px; color: #334155;">
    This is not an academic homework assignment—it is a commercially viable enterprise software platform. Here are the 5 highest-converting ways to turn this codebase into income:
  </p>

  <div class="money-card">
    <div class="money-header">
      <span class="money-title">1. High-Ticket B2B Client Implementations</span>
      <span class="money-price">$2,500 – $7,500 / Client</span>
    </div>
    <div class="money-desc">
      Every company with 30 to 500 employees wastes dozens of HR/IT hours every week answering repetitive questions like <em>"What is our parental leave?"</em>, <em>"How do I submit travel receipts?"</em>, and <em>"Who manages payroll?"</em>
    </div>
    <ul class="card ul">
      <li><strong>The Offer:</strong> "I will set up a private, zero-hallucination AI Assistant on your company handbooks and internal database with an executive approval dashboard."</li>
      <li><strong>Execution:</strong> Replace the 4 policy files with the client's PDFs, connect their Postgres/SQL database, and deploy to their cloud.</li>
      <li><strong>Recurring Upsell:</strong> Charge <strong>$350 – $750/month</strong> for maintenance, doc ingestion, and model updates.</li>
    </ul>
  </div>

  <div class="money-card">
    <div class="money-header">
      <span class="money-title">2. Vertical Niche Micro-SaaS Product</span>
      <span class="money-price">$99 – $299 / Month / Account</span>
    </div>
    <div class="money-desc">
      Rebrand and market this exact architecture to specific high-compliance industries where accuracy is paramount:
    </div>
    <div class="grid-3" style="margin-top: 8px;">
      <div style="background: white; border: 1px solid #CBD5E1; padding: 8px; border-radius: 6px; font-size: 11px;">
        <strong>🏥 Dental &amp; Medical Clinics</strong><br>
        Staff SOPs, OSHA disinfection rules, equipment checkout logs.
      </div>
      <div style="background: white; border: 1px solid #CBD5E1; padding: 8px; border-radius: 6px; font-size: 11px;">
        <strong>⚖️ Boutique Law Firms</strong><br>
        Case precedent search, partner hourly billing guidelines, intake SOPs.
      </div>
      <div style="background: white; border: 1px solid #CBD5E1; padding: 8px; border-radius: 6px; font-size: 11px;">
        <strong>🍔 Multi-Unit Franchisees</strong><br>
        Store ops manuals, food safety checklists, manager shift guidelines.
      </div>
    </div>
  </div>

  <div class="money-card">
    <div class="money-header">
      <span class="money-title">3. Upwork / Freelance Elite Positioning</span>
      <span class="money-price">$75 – $150 / Hour</span>
    </div>
    <div class="money-desc">
      Generic "Python / Prompt Engineering" freelancers face fierce price competition. Rebrand your profile as an <strong>"Enterprise LangGraph &amp; Production RAG Architect"</strong>:
    </div>
    <p style="font-size: 11.5px; color: #475569; margin-top: 4px;">
      Target clients searching for <em>"Fix LLM hallucination"</em>, <em>"LangGraph Human in the loop"</em>, or <em>"RAG with Cross-Encoder &amp; BM25"</em>. Point them to your live deployed Vercel demo—your proposal closes immediately!
    </p>
  </div>

  <div class="money-card">
    <div class="money-header">
      <span class="money-title">4. Land a Senior AI Engineering Role</span>
      <span class="money-price">$130,000 – $210,000 / Year</span>
    </div>
    <div class="money-desc">
      95% of candidates present basic Streamlit wrappers with naive LangChain chains that break in production. Demonstrating <strong>durable PostgreSQL checkpoints</strong>, <strong>Next.js 16 UI</strong>, <strong>deterministic security gates</strong>, and <strong>Docker multi-stage optimization</strong> instantly establishes you as an elite engineering hire.
    </div>
  </div>
</div>

<!-- CHAPTER 6: 24-HOUR ACTION BLUEPRINT -->
<div class="section page-break">
  <div class="chapter-header">
    <span class="chapter-num">CHAPTER 6</span>
    <h2 class="chapter-title">The 24-Hour Launch Checklist</h2>
  </div>

  <p style="margin-bottom: 14px; font-size: 12.5px; color: #334155;">
    Turn this plan into tangible results by completing these specific milestones today:
  </p>

  <ul class="checklist">
    <li>
      <span class="checkbox"></span>
      <div>
        <strong>Hour 1: Local Docker Flight</strong> — Run <code>docker-compose up -d</code>, verify Next.js UI on port 3000, test Policy Assistant and Agent mode.
      </div>
    </li>
    <li>
      <span class="checkbox"></span>
      <div>
        <strong>Hour 3: Deploy Free Cloud Stack</strong> — Create free Neon DB, deploy backend to Hugging Face Spaces / Render, and link frontend to Vercel.
      </div>
    </li>
    <li>
      <span class="checkbox"></span>
      <div>
        <strong>Hour 6: Record a 3-Minute Loom Demo</strong> — Walk through Grounded Citations, Refusal Cards, and the Human-in-the-Loop Approval gate.
      </div>
    </li>
    <li>
      <span class="checkbox"></span>
      <div>
        <strong>Hour 12: Publish LinkedIn / Portfolio Showcase</strong> — Post the Loom video + live Vercel link with the architecture diagram.
      </div>
    </li>
    <li>
      <span class="checkbox"></span>
      <div>
        <strong>Hour 24: Pitch 5 Local Businesses or Upwork Clients</strong> — Offer the "Zero-Hallucination Internal SOP Agent" solution.
      </div>
    </li>
  </ul>

  <div style="margin-top: 24px; padding: 18px; background: linear-gradient(135deg, #0F172A, #1E1B4B); border-radius: 12px; color: white; text-align: center;">
    <h3 style="font-size: 15px; margin-bottom: 6px; color: #A5B4FC;">🏆 Final Architect's Note</h3>
    <p style="font-size: 12px; color: #CBD5E1; max-width: 500px; margin: 0 auto;">
      You have in your hands a battle-tested, production-hardened multi-agent system. Execute the steps, showcase the live application, and start monetizing your AI engineering expertise today.
    </p>
  </div>
</div>

</body>
</html>
"""

def generate_pdf():
    print("1. Writing colorful HTML report source...")
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(HTML_CONTENT)
    print(f"   HTML created at: {HTML_PATH}")

    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    
    browser_exe = chrome_path if os.path.exists(chrome_path) else edge_path
    print(f"2. Using browser engine: {browser_exe}")

    print("3. Rendering high-resolution PDF via headless print engine...")
    cmd = [
        browser_exe,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={OUTPUT_PDF}",
        str(HTML_PATH)
    ]
    
    # Use PowerShell Start-Process with -Wait
    ps_cmd = f"Start-Process -FilePath '{browser_exe}' -ArgumentList '--headless=new', '--disable-gpu', '--no-pdf-header-footer', '--print-to-pdf=\"{OUTPUT_PDF}\"', '\"{HTML_PATH}\"' -Wait"
    result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True)
    
    if os.path.exists(OUTPUT_PDF):
        size_kb = os.path.getsize(OUTPUT_PDF) / 1024
        print(f"SUCCESS! PDF Report generated successfully at:\n{OUTPUT_PDF}\nSize: {size_kb:.2f} KB")
        # Clean up temp HTML
        try:
            os.remove(HTML_PATH)
        except Exception:
            pass
        return True
    else:
        print(f"ERROR: PDF was not generated. Stderr: {result.stderr}")
        return False

if __name__ == "__main__":
    success = generate_pdf()
    sys.exit(0 if success else 1)
