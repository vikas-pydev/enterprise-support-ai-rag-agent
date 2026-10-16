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
    { name: 'Next.js 16 (App Router)', category: 'Frontend' },
    { name: 'TypeScript 5', category: 'Language' },
    { name: 'Tailwind CSS 4', category: 'Styling' },
    { name: 'FastAPI', category: 'REST API' },
    { name: 'LangGraph Multi-Agent', category: 'Orchestration' },
    { name: 'Hybrid RAG (ChromaDB + BM25)', category: 'Retrieval' },
    { name: 'Cross-Encoder Reranker', category: 'Reranking' },
    { name: 'PostgreSQL & psycopg3', category: 'Structured Data' },
    { name: 'Durable Checkpointing', category: 'State' },
    { name: 'Human-in-the-Loop Gate', category: 'Governance' },
  ];

  return (
    <section aria-label="System Architecture & Developer Diagnostics" className="rounded-2xl border border-[#E9E5DF] dark:border-[#2F3540] bg-[#FFFEFC] dark:bg-[#21252D] overflow-hidden transition-colors shadow-[0_1px_3px_rgba(38,49,66,0.03)]">
      {/* Header Accordion Toggle */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        className="w-full px-6 py-4 flex items-center justify-between gap-4 bg-[#FCFAF7] dark:bg-[#1B1E24] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] transition-colors text-left cursor-pointer"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-[#E5F5F1] dark:bg-[#1A2D2A] border border-[#C7E9E2] dark:border-[#244742] text-[#368F88] dark:text-[#A9DED5]">
            <Network className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-[#263142] dark:text-[#EBEFF5] tracking-wide">
                System Architecture &amp; Technical Overview
              </h3>
              <span className="hidden sm:inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium bg-[#E5F5F1] dark:bg-[#1A2D2A] border border-[#C7E9E2] dark:border-[#244742] text-[#263142] dark:text-[#A9DED5]">
                Technical Reference
              </span>
            </div>
            <p className="text-xs text-[#697582] dark:text-[#9CA6B5] mt-0.5 font-normal">
              Explore the end-to-end AI engineering architecture, tech stack &amp; REST service layer
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-[#697582] dark:text-[#9CA6B5]">
          <span className="text-xs font-medium hidden md:inline">
            {isOpen ? 'Hide Architecture Details' : 'View Architecture Details'}
          </span>
          {isOpen ? (
            <ChevronDown className="w-4 h-4 text-[#368F88] dark:text-[#A9DED5]" />
          ) : (
            <ChevronRight className="w-4 h-4 text-[#9299A3] dark:text-[#6E7887]" />
          )}
        </div>
      </button>

      {/* Collapsible Architecture Body */}
      {isOpen && (
        <div className="p-6 space-y-6 border-t border-[#E9E5DF] dark:border-[#2F3540] animate-in fade-in duration-150 text-[#263142] dark:text-[#EBEFF5]">
          {/* Subsystem Pillars */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
            <div className="p-4 rounded-2xl bg-[#F8F6F2] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540] flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 text-[#368F88] dark:text-[#A9DED5] mb-2">
                  <Layers className="w-4 h-4" />
                  <span className="text-xs font-semibold text-[#263142] dark:text-[#EBEFF5]">Hybrid Retrieval RAG</span>
                </div>
                <p className="text-[11px] text-[#697582] dark:text-[#9CA6B5] leading-relaxed font-normal">
                  Dense ChromaDB embeddings + Sparse BM25 fused with Reciprocal Rank Fusion ($k=60$) and scored via Cross-Encoder reranker with deterministic chunk citations.
                </p>
              </div>
              <span className="mt-3 text-[10px] font-mono text-[#368F88] dark:text-[#A9DED5]">/api/v1/ask</span>
            </div>

            <div className="p-4 rounded-2xl bg-[#F8F6F2] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540] flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 text-[#368F88] dark:text-[#A9DED5] mb-2">
                  <Database className="w-4 h-4" />
                  <span className="text-xs font-semibold text-[#263142] dark:text-[#EBEFF5]">PostgreSQL Operations</span>
                </div>
                <p className="text-[11px] text-[#697582] dark:text-[#9CA6B5] leading-relaxed font-normal">
                  Relational schema modeling employees, departments, PTO leave balance categories, and multi-currency travel expense claims with parameterized SQL safety.
                </p>
              </div>
              <span className="mt-3 text-[10px] font-mono text-[#368F88] dark:text-[#A9DED5]">/api/v1/employees/*</span>
            </div>

            <div className="p-4 rounded-2xl bg-[#F8F6F2] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540] flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 text-[#368F88] dark:text-[#A9DED5] mb-2">
                  <Cpu className="w-4 h-4" />
                  <span className="text-xs font-semibold text-[#263142] dark:text-[#EBEFF5]">LangGraph Multi-Agent</span>
                </div>
                <p className="text-[11px] text-[#697582] dark:text-[#9CA6B5] leading-relaxed font-normal">
                  Centralized Supervisor routing to specialized workers (HR Policy, Employee Records, Travel &amp; Expense) with sandboxed tool permissions and cycle protection.
                </p>
              </div>
              <span className="mt-3 text-[10px] font-mono text-[#368F88] dark:text-[#A9DED5]">/api/v1/agent/chat</span>
            </div>

            <div className="p-4 rounded-2xl bg-[#F8F6F2] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540] flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 text-[#368F88] dark:text-[#A9DED5] mb-2">
                  <ShieldCheck className="w-4 h-4" />
                  <span className="text-xs font-semibold text-[#263142] dark:text-[#EBEFF5]">State &amp; HITL Governance</span>
                </div>
                <p className="text-[11px] text-[#697582] dark:text-[#9CA6B5] leading-relaxed font-normal">
                  Durable thread checkpointing with PostgreSQL/SQLite backend and deterministic human approval gates for executive records or confidential requests.
                </p>
              </div>
              <span className="mt-3 text-[10px] font-mono text-[#368F88] dark:text-[#A9DED5]">/api/v1/agent/approvals/*</span>
            </div>
          </div>

          {/* Tech Stack Pills */}
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-[#697582] dark:text-[#9CA6B5] mb-3 flex items-center gap-1.5">
              <Code2 className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5]" />
              <span>Production Technology Stack</span>
            </h4>
            <div className="flex flex-wrap gap-2">
              {techStack.map((tech) => (
                <span
                  key={tech.name}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-medium bg-[#F8F6F2] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540] text-[#263142] dark:text-[#EBEFF5]"
                >
                  <CheckCircle2 className="w-3 h-3 text-[#368F88] dark:text-[#A9DED5]" />
                  <span>{tech.name}</span>
                  <span className="text-[10px] text-[#9299A3] dark:text-[#6E7887] font-mono">({tech.category})</span>
                </span>
              ))}
            </div>
          </div>

          {/* Integrated REST Endpoint Matrix */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-[#697582] dark:text-[#9CA6B5] flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5]" />
                <span>Configured FastAPI REST Endpoints ({endpoints.length})</span>
              </h4>
              <a
                href={`${baseUrl}/docs`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs font-medium text-[#368F88] dark:text-[#A9DED5] hover:text-[#2B7771] inline-flex items-center gap-1"
              >
                <span>Interactive Swagger UI</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">
              {endpoints.map((ep, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-xl bg-[#F8F6F2] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540] flex flex-col justify-between text-xs hover:border-[#A9DED5] dark:hover:border-[#368F88] transition-colors"
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
        </div>
      )}
    </section>
  );
}
