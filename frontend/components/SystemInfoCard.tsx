'use client';

import React, { useState } from 'react';
import { apiClient } from '@/lib/api/client';
import {
  Database,
  ShieldCheck,
  Cpu,
  Layers,
  Network,
  Terminal,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  CheckCircle2,
  Code2,
} from 'lucide-react';

export function SystemInfoCard() {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const baseUrl = apiClient.getBaseUrl();

  const endpoints = [
    { method: 'GET', path: '/health', tag: 'System', desc: 'Health check & semantic versioning' },
    { method: 'POST', path: '/api/v1/ask', tag: 'Hybrid RAG', desc: 'Grounded policy Q&A with citations' },
    { method: 'GET', path: '/api/v1/employees/{id}', tag: 'PostgreSQL', desc: 'Employee profile & manager lookup' },
    { method: 'GET', path: '/api/v1/employees/{id}/leave', tag: 'PostgreSQL', desc: 'PTO allocations & category balances' },
    { method: 'GET', path: '/api/v1/employees/{id}/travel', tag: 'PostgreSQL', desc: 'Travel expense summaries & claims' },
    { method: 'POST', path: '/api/v1/agent/chat', tag: 'LangGraph', desc: 'Multi-turn supervisor & tool reasoning' },
    { method: 'POST', path: '/api/v1/agent/sessions/{id}/clear', tag: 'Sessions', desc: 'Clear conversational history' },
    { method: 'DELETE', path: '/api/v1/agent/sessions/{id}', tag: 'Sessions', desc: 'Delete active session checkpoints' },
    { method: 'POST', path: '/api/v1/agent/approvals/{id}', tag: 'HITL', desc: 'Resume workflow with approval/rejection' },
  ];

  const techStack = [
    { name: 'Next.js 16 (App Router)', category: 'Frontend', color: 'bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 border-slate-300 dark:border-slate-700' },
    { name: 'TypeScript 5', category: 'Language', color: 'bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-blue-500/30' },
    { name: 'Tailwind CSS 4', category: 'Styling', color: 'bg-cyan-50 dark:bg-cyan-950/60 text-cyan-700 dark:text-cyan-300 border-cyan-300 dark:border-cyan-500/30' },
    { name: 'FastAPI', category: 'REST API', color: 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border-emerald-300 dark:border-emerald-500/30' },
    { name: 'LangGraph Multi-Agent', category: 'Orchestration', color: 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border-indigo-300 dark:border-indigo-500/30' },
    { name: 'Hybrid RAG (ChromaDB + BM25)', category: 'Retrieval', color: 'bg-violet-50 dark:bg-violet-950/60 text-violet-700 dark:text-violet-300 border-violet-300 dark:border-violet-500/30' },
    { name: 'Cross-Encoder Reranker', category: 'Reranking', color: 'bg-purple-50 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border-purple-300 dark:border-purple-500/30' },
    { name: 'PostgreSQL & psycopg3', category: 'Structured Data', color: 'bg-sky-50 dark:bg-sky-950/60 text-sky-700 dark:text-sky-300 border-sky-300 dark:border-sky-500/30' },
    { name: 'Durable Checkpointing', category: 'State', color: 'bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border-amber-300 dark:border-amber-500/30' },
    { name: 'Human-in-the-Loop Gate', category: 'Governance', color: 'bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border-rose-300 dark:border-rose-500/30' },
  ];

  return (
    <section aria-label="System Architecture & Developer Diagnostics" className="rounded-3xl border border-slate-200 dark:border-slate-800/90 bg-white/70 dark:bg-slate-900/40 backdrop-blur-md overflow-hidden transition-all shadow-lg">
      {/* Header Accordion Toggle */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        className="w-full px-6 py-4 flex items-center justify-between gap-4 bg-slate-50 dark:bg-slate-900/70 hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors text-left cursor-pointer"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-600 dark:text-cyan-400">
            <Network className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white tracking-wide">
                System Architecture &amp; Technical Overview
              </h3>
              <span className="hidden sm:inline-flex px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-100 dark:bg-indigo-950/80 border border-indigo-200 dark:border-indigo-500/30 text-indigo-700 dark:text-indigo-300">
                Recruiter &amp; Engineer Showcase
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Explore the end-to-end AI engineering architecture, tech stack &amp; REST service layer
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400">
          <span className="text-xs font-semibold hidden md:inline">
            {isOpen ? 'Hide Architecture Details' : 'View Architecture Details'}
          </span>
          {isOpen ? (
            <ChevronDown className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-slate-400" />
          )}
        </div>
      </button>

      {/* Collapsible Architecture Body */}
      {isOpen && (
        <div className="p-6 space-y-6 border-t border-slate-200 dark:border-slate-800/80 animate-in fade-in duration-200 text-slate-900 dark:text-slate-100">
          {/* Subsystem Pillars */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
            <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 text-cyan-600 dark:text-cyan-400 mb-2">
                  <Layers className="w-4 h-4" />
                  <span className="text-xs font-bold text-slate-900 dark:text-white">Hybrid Retrieval RAG</span>
                </div>
                <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                  Dense ChromaDB embeddings + Sparse BM25 fused with Reciprocal Rank Fusion ($k=60$) and scored via Cross-Encoder reranker with deterministic chunk citations.
                </p>
              </div>
              <span className="mt-3 text-[10px] font-mono text-cyan-600 dark:text-cyan-400/80">/api/v1/ask</span>
            </div>

            <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400 mb-2">
                  <Database className="w-4 h-4" />
                  <span className="text-xs font-bold text-slate-900 dark:text-white">PostgreSQL Operations</span>
                </div>
                <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                  Relational schema modeling employees, departments, PTO leave balance categories, and multi-currency travel expense claims with parameterized SQL safety.
                </p>
              </div>
              <span className="mt-3 text-[10px] font-mono text-indigo-600 dark:text-indigo-400/80">/api/v1/employees/*</span>
            </div>

            <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 mb-2">
                  <Cpu className="w-4 h-4" />
                  <span className="text-xs font-bold text-slate-900 dark:text-white">LangGraph Multi-Agent</span>
                </div>
                <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                  Centralized Supervisor routing to specialized workers (HR Policy, Employee Records, Travel &amp; Expense) with sandboxed tool permissions and cycle protection.
                </p>
              </div>
              <span className="mt-3 text-[10px] font-mono text-emerald-600 dark:text-emerald-400/80">/api/v1/agent/chat</span>
            </div>

            <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400 mb-2">
                  <ShieldCheck className="w-4 h-4" />
                  <span className="text-xs font-bold text-slate-900 dark:text-white">State &amp; HITL Governance</span>
                </div>
                <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                  Durable thread checkpointing with PostgreSQL/SQLite backend and deterministic human approval gates for executive records or confidential requests.
                </p>
              </div>
              <span className="mt-3 text-[10px] font-mono text-amber-600 dark:text-amber-400/80">/api/v1/agent/approvals/*</span>
            </div>
          </div>

          {/* Tech Stack Pills */}
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3 flex items-center gap-1.5">
              <Code2 className="w-3.5 h-3.5 text-indigo-500 dark:text-indigo-400" />
              <span>Production Technology Stack</span>
            </h4>
            <div className="flex flex-wrap gap-2">
              {techStack.map((tech) => (
                <span
                  key={tech.name}
                  className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-medium border ${tech.color}`}
                >
                  <CheckCircle2 className="w-3 h-3 opacity-70" />
                  <span>{tech.name}</span>
                  <span className="text-[10px] opacity-70 font-mono">({tech.category})</span>
                </span>
              ))}
            </div>
          </div>

          {/* Integrated REST Endpoint Matrix */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                <span>Configured FastAPI REST Endpoints ({endpoints.length})</span>
              </h4>
              <a
                href={`${baseUrl}/docs`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs font-semibold text-cyan-600 dark:text-cyan-400 hover:text-cyan-500 inline-flex items-center gap-1"
              >
                <span>Interactive Swagger UI</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">
              {endpoints.map((ep, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800/80 flex flex-col justify-between text-xs hover:border-slate-300 dark:hover:border-slate-700 transition-colors"
                >
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <span
                      className={`font-mono font-bold text-[10px] px-2 py-0.5 rounded-md ${
                        ep.method === 'GET'
                          ? 'bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-500/30'
                          : ep.method === 'POST'
                          ? 'bg-cyan-100 dark:bg-cyan-950/80 text-cyan-700 dark:text-cyan-300 border border-cyan-300 dark:border-cyan-500/30'
                          : 'bg-rose-100 dark:bg-rose-950/80 text-rose-700 dark:text-rose-300 border border-rose-300 dark:border-rose-500/30'
                      }`}
                    >
                      {ep.method}
                    </span>
                    <span className="font-mono text-[11px] text-slate-800 dark:text-slate-300 font-medium truncate">
                      {ep.path}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-1">{ep.desc}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

