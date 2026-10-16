'use client';

import React, { useState } from 'react';
import {
  X,
  Layers,
  Database,
  Cpu,
  ShieldCheck,
  ExternalLink,
  Network,
  GitBranch,
  FileSearch,
  Sparkles,
  Lock,
} from 'lucide-react';
import { apiClient } from '@/lib/api/client';

interface ArchitectureModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ArchitectureModal({ isOpen, onClose }: ArchitectureModalProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'rag' | 'agent' | 'database' | 'api'>('overview');
  const baseUrl = apiClient.getBaseUrl();

  if (!isOpen) return null;

  const endpoints = [
    { method: 'GET', path: '/health', tag: 'System', desc: 'Health status & semantic API versioning' },
    { method: 'POST', path: '/api/v1/ask', tag: 'Hybrid RAG', desc: 'Grounded policy Q&A with verifiable chunk citations' },
    { method: 'GET', path: '/api/v1/employees/{id}', tag: 'PostgreSQL', desc: 'Employee official record & manager reporting line' },
    { method: 'GET', path: '/api/v1/employees/{id}/leave', tag: 'PostgreSQL', desc: 'PTO allocations & category leave balances' },
    { method: 'GET', path: '/api/v1/employees/{id}/travel', tag: 'PostgreSQL', desc: 'Travel expense summaries & claim history' },
    { method: 'POST', path: '/api/v1/agent/chat', tag: 'LangGraph', desc: 'Multi-turn supervisor & tool reasoning loop' },
    { method: 'POST', path: '/api/v1/agent/sessions/{id}/clear', tag: 'Sessions', desc: 'Clear conversational session memory' },
    { method: 'DELETE', path: '/api/v1/agent/sessions/{id}', tag: 'Sessions', desc: 'Delete active session checkpoints' },
    { method: 'POST', path: '/api/v1/agent/approvals/{id}', tag: 'HITL', desc: 'Authorize or reject gated operational action' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-[#263142]/40 backdrop-blur-xs animate-in fade-in duration-150">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="arch-modal-title"
        className="relative w-full max-w-4xl max-h-[90vh] flex flex-col rounded-3xl border border-[#E9E5DF] dark:border-[#2F3540] bg-[#FFFEFC] dark:bg-[#21252D] shadow-2xl overflow-hidden transition-colors text-[#263142] dark:text-[#EBEFF5]"
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E9E5DF] dark:border-[#2F3540] bg-[#FCFAF7] dark:bg-[#1B1E24]">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-[#E5F5F1] dark:bg-[#1A2D2A] border border-[#C7E9E2] dark:border-[#244742] text-[#368F88] dark:text-[#A9DED5]">
              <Network className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 id="arch-modal-title" className="text-base sm:text-lg font-semibold">
                  System Architecture &amp; Technical Reference
                </h2>
                <span className="hidden sm:inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium bg-[#E5F5F1] dark:bg-[#1A2D2A] text-[#263142] dark:text-[#A9DED5] border border-[#C7E9E2] dark:border-[#244742]">
                  Technical Overview
                </span>
              </div>
              <p className="text-xs text-[#697582] dark:text-[#9CA6B5]">
                End-to-end architecture, multi-agent graph, retrieval engineering, and REST contracts
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close Architecture Modal"
            className="p-1.5 rounded-xl text-[#9299A3] hover:text-[#263142] dark:hover:text-[#EBEFF5] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Navigation Tabs */}
        <div className="flex items-center gap-2 px-6 py-2.5 border-b border-[#E9E5DF] dark:border-[#2F3540] bg-[#F8F6F2] dark:bg-[#1B1E24] overflow-x-auto text-xs font-medium">
          <button
            type="button"
            onClick={() => setActiveTab('overview')}
            className={`px-3 py-1.5 rounded-lg transition-colors cursor-pointer ${
              activeTab === 'overview'
                ? 'bg-[#368F88] text-white shadow-xs font-semibold'
                : 'text-[#697582] dark:text-[#9CA6B5] hover:text-[#263142] dark:hover:text-[#EBEFF5]'
            }`}
          >
            Architecture Overview
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('rag')}
            className={`px-3 py-1.5 rounded-lg transition-colors cursor-pointer ${
              activeTab === 'rag'
                ? 'bg-[#368F88] text-white shadow-xs font-semibold'
                : 'text-[#697582] dark:text-[#9CA6B5] hover:text-[#263142] dark:hover:text-[#EBEFF5]'
            }`}
          >
            Hybrid RAG Pipeline
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('agent')}
            className={`px-3 py-1.5 rounded-lg transition-colors cursor-pointer ${
              activeTab === 'agent'
                ? 'bg-[#368F88] text-white shadow-xs font-semibold'
                : 'text-[#697582] dark:text-[#9CA6B5] hover:text-[#263142] dark:hover:text-[#EBEFF5]'
            }`}
          >
            LangGraph Multi-Agent
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('database')}
            className={`px-3 py-1.5 rounded-lg transition-colors cursor-pointer ${
              activeTab === 'database'
                ? 'bg-[#368F88] text-white shadow-xs font-semibold'
                : 'text-[#697582] dark:text-[#9CA6B5] hover:text-[#263142] dark:hover:text-[#EBEFF5]'
            }`}
          >
            PostgreSQL Schema
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('api')}
            className={`px-3 py-1.5 rounded-lg transition-colors cursor-pointer ${
              activeTab === 'api'
                ? 'bg-[#368F88] text-white shadow-xs font-semibold'
                : 'text-[#697582] dark:text-[#9CA6B5] hover:text-[#263142] dark:hover:text-[#EBEFF5]'
            }`}
          >
            REST API Matrix
          </button>
        </div>

        {/* Modal Body (Scrollable) */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 text-sm">
          {/* TAB 1: OVERVIEW */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <div className="p-4 rounded-2xl bg-[#F8F6F2] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540]">
                <h3 className="text-sm font-semibold flex items-center gap-2 mb-2 text-[#368F88] dark:text-[#A9DED5]">
                  <Sparkles className="w-4 h-4" /> System Vision &amp; Core Pillars
                </h3>
                <p className="text-xs text-[#697582] dark:text-[#9CA6B5] leading-relaxed font-normal">
                  The <strong>Enterprise Support AI Agent</strong> is an enterprise-grade platform uniting unstructured policy document search (RAG) and structured business records (PostgreSQL) under a coordinated multi-agent supervisor graph built with LangGraph, FastAPI, and Next.js 16.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                <div className="p-4 rounded-2xl bg-[#F8F6F2] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540]">
                  <div className="flex items-center gap-2 text-[#368F88] dark:text-[#A9DED5] font-semibold text-xs mb-1.5">
                    <Layers className="w-4 h-4" /> Hybrid RAG Engine
                  </div>
                  <p className="text-xs text-[#697582] dark:text-[#9CA6B5] leading-relaxed font-normal">
                    Dense ChromaDB + Sparse BM25 fused via Reciprocal Rank Fusion ($k=60$) and reranked with Cross-Encoder (MiniLM). Features deterministic chunk citations and explicit refusal safeguards.
                  </p>
                </div>

                <div className="p-4 rounded-2xl bg-[#F8F6F2] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540]">
                  <div className="flex items-center gap-2 text-[#368F88] dark:text-[#A9DED5] font-semibold text-xs mb-1.5">
                    <Cpu className="w-4 h-4" /> Multi-Agent Supervisor
                  </div>
                  <p className="text-xs text-[#697582] dark:text-[#9CA6B5] leading-relaxed font-normal">
                    Supervisor router orchestrates specialized workers (HR Policy, Employee Records, Travel &amp; Expense) with sandboxed tool invocation and loop-prevention gates.
                  </p>
                </div>

                <div className="p-4 rounded-2xl bg-[#F8F6F2] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540]">
                  <div className="flex items-center gap-2 text-[#368F88] dark:text-[#A9DED5] font-semibold text-xs mb-1.5">
                    <Database className="w-4 h-4" /> PostgreSQL Structured Layer
                  </div>
                  <p className="text-xs text-[#697582] dark:text-[#9CA6B5] leading-relaxed font-normal">
                    Relational schema managing employee profiles, PTO categories, and travel expense claims with parameterized SQL safety and ACID transaction guarantees.
                  </p>
                </div>

                <div className="p-4 rounded-2xl bg-[#F8F6F2] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540]">
                  <div className="flex items-center gap-2 text-[#368F88] dark:text-[#A9DED5] font-semibold text-xs mb-1.5">
                    <ShieldCheck className="w-4 h-4" /> Checkpointing &amp; HITL
                  </div>
                  <p className="text-xs text-[#697582] dark:text-[#9CA6B5] leading-relaxed font-normal">
                    Durable thread checkpointing with PostgreSQL/SQLite persistence and deterministic Human-in-the-Loop authorization gates for sensitive enterprise queries.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: HYBRID RAG */}
          {activeTab === 'rag' && (
            <div className="space-y-4">
              <div className="p-4 rounded-2xl bg-[#F8F6F2] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540] space-y-3">
                <h3 className="text-sm font-semibold text-[#368F88] dark:text-[#A9DED5] flex items-center gap-2">
                  <FileSearch className="w-4 h-4" /> Two-Stage Retrieval &amp; Refusal Architecture
                </h3>
                <div className="space-y-2 text-xs text-[#697582] dark:text-[#9CA6B5] font-normal leading-relaxed">
                  <p>
                    1. <strong>Dense Semantic Search</strong>: Embeds queries via <code>sentence-transformers/all-MiniLM-L6-v2</code> and queries ChromaDB with cosine similarity.
                  </p>
                  <p>
                    2. <strong>Sparse Lexical Search</strong>: In-memory BM25Okapi captures exact policy codes, alphanumeric IDs, and acronyms.
                  </p>
                  <p>
                    3. <strong>Reciprocal Rank Fusion (RRF)</strong>: Merges ranking lists using standard $k=60$ reciprocal scoring.
                  </p>
                  <p>
                    4. <strong>Cross-Encoder Reranking</strong>: <code>cross-encoder/ms-marco-MiniLM-L-6-v2</code> scores cross-attention relevance. Passages below <code>rerank_threshold = -1.0</code> are dropped.
                  </p>
                  <p>
                    5. <strong>Deterministic Refusal</strong>: When context is empty or below threshold, the system deterministically refuses to guess or hallucinate.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: LANGGRAPH MULTI-AGENT */}
          {activeTab === 'agent' && (
            <div className="space-y-4">
              <div className="p-4 rounded-2xl bg-[#F8F6F2] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540] space-y-3">
                <h3 className="text-sm font-semibold text-[#368F88] dark:text-[#A9DED5] flex items-center gap-2">
                  <GitBranch className="w-4 h-4" /> Supervisor-Worker Orchestration Graph
                </h3>
                <p className="text-xs text-[#697582] dark:text-[#9CA6B5] leading-relaxed font-normal">
                  LangGraph coordinates user inquiries through an iterative graph flow:
                </p>
                <div className="p-3 rounded-xl bg-[#FFFFFF] dark:bg-[#21252D] border border-[#E9E5DF] dark:border-[#2F3540] font-mono text-xs text-[#368F88] dark:text-[#A9DED5]">
                  User Inquiry &rarr; Supervisor Router &rarr; Domain Worker &rarr; Tool Execution &rarr; Final Synthesis
                </div>
                <ul className="text-xs text-[#697582] dark:text-[#9CA6B5] space-y-1.5 list-disc pl-5 font-normal">
                  <li><strong>HR Policy Worker</strong>: Specialized in general company policies and handbook guidelines.</li>
                  <li><strong>Employee Records Worker</strong>: Retrieves profiles, reporting lines, and PTO balances.</li>
                  <li><strong>Travel &amp; Expense Worker</strong>: Analyzes claims, expense rollups, and flight budgets.</li>
                  <li><strong>Human Gate</strong>: Intercepts confidential queries with an approval checkpoint.</li>
                </ul>
              </div>
            </div>
          )}

          {/* TAB 4: DATABASE SCHEMA */}
          {activeTab === 'database' && (
            <div className="space-y-4">
              <div className="p-4 rounded-2xl bg-[#F8F6F2] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540] space-y-3">
                <h3 className="text-sm font-semibold text-[#368F88] dark:text-[#A9DED5] flex items-center gap-2">
                  <Database className="w-4 h-4" /> Normalized Relational Schema
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                  <div className="p-3 rounded-xl bg-[#FFFFFF] dark:bg-[#21252D] border border-[#E9E5DF] dark:border-[#2F3540]">
                    <div className="font-mono font-semibold text-[#368F88] dark:text-[#A9DED5] mb-1">employees</div>
                    <p className="text-[11px] text-[#697582] dark:text-[#9CA6B5]">
                      employee_id (PK), name, email, department, job_title, manager_employee_id (FK), created_at
                    </p>
                  </div>
                  <div className="p-3 rounded-xl bg-[#FFFFFF] dark:bg-[#21252D] border border-[#E9E5DF] dark:border-[#2F3540]">
                    <div className="font-mono font-semibold text-[#368F88] dark:text-[#A9DED5] mb-1">leave_balances</div>
                    <p className="text-[11px] text-[#697582] dark:text-[#9CA6B5]">
                      employee_id (FK), leave_type, total_days, used_days, remaining_days, updated_at
                    </p>
                  </div>
                  <div className="p-3 rounded-xl bg-[#FFFFFF] dark:bg-[#21252D] border border-[#E9E5DF] dark:border-[#2F3540]">
                    <div className="font-mono font-semibold text-[#368F88] dark:text-[#A9DED5] mb-1">travel_expenses</div>
                    <p className="text-[11px] text-[#697582] dark:text-[#9CA6B5]">
                      employee_id (FK), expense_date, category, amount, currency, status, description
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: REST API MATRIX */}
          {activeTab === 'api' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-[#697582] dark:text-[#9CA6B5]">
                  FastAPI Endpoints ({endpoints.length})
                </span>
                <a
                  href={`${baseUrl}/docs`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs font-medium text-[#368F88] dark:text-[#A9DED5] hover:underline inline-flex items-center gap-1"
                >
                  <span>Interactive Swagger UI</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                {endpoints.map((ep, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-[#F8F6F2] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540] flex flex-col justify-between text-xs"
                  >
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <span
                        className={`font-mono font-semibold text-[10px] px-2 py-0.5 rounded-md ${
                          ep.method === 'GET'
                            ? 'bg-[#CFE5D6] dark:bg-[#2C3B32] text-[#2F855A] dark:text-[#34D399] border border-[#B7D9C2] dark:border-[#3A4D42]'
                            : ep.method === 'POST'
                            ? 'bg-[#E5F5F1] dark:bg-[#1A2D2A] text-[#368F88] dark:text-[#A9DED5] border border-[#C7E9E2] dark:border-[#244742]'
                            : 'bg-[#FDE8E8] dark:bg-[#3D2525] text-[#9B1C1C] dark:text-[#F87171] border border-[#FBD5D5] dark:border-[#522828]'
                        }`}
                      >
                        {ep.method}
                      </span>
                      <span className="font-mono text-[11px] text-[#263142] dark:text-[#EBEFF5] font-medium truncate">
                        {ep.path}
                      </span>
                    </div>
                    <div className="text-[11px] text-[#697582] dark:text-[#9CA6B5] line-clamp-1 font-normal">{ep.desc}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 border-t border-[#E9E5DF] dark:border-[#2F3540] bg-[#FCFAF7] dark:bg-[#1B1E24] flex items-center justify-between text-xs text-[#697582] dark:text-[#9CA6B5]">
          <div className="flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5]" />
            <span>Built strictly with sanitized, non-leaking client architecture</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl bg-[#FFFFFF] dark:bg-[#21252D] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] border border-[#E9E5DF] dark:border-[#2F3540] text-[#263142] dark:text-[#EBEFF5] font-medium transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
