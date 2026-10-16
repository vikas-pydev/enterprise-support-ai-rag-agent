'use client';

import React, { useState } from 'react';
import {
  BookOpen,
  Bot,
  Sparkles,
  ArrowRight,
  Search,
  CheckCircle2,
  Database,
  Send,
  CornerDownLeft,
} from 'lucide-react';
import { INDEXED_POLICY_DOCUMENTS } from '@/lib/knowledge/documents';

interface WorkspaceHomeProps {
  onSelectWorkspace: (workspace: 'rag' | 'agent', initialPrompt?: string) => void;
  onOpenKnowledgeBase?: () => void;
}

export function WorkspaceHome({
  onSelectWorkspace,
  onOpenKnowledgeBase,
}: WorkspaceHomeProps) {
  const [promptText, setPromptText] = useState<string>('');

  const handlePromptSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = promptText.trim();
    if (!trimmed) return;

    // Intelligent query dispatch: if query references employee records/travel spend/approval, route to agent; else policy assistant
    const lower = trimmed.toLowerCase();
    if (
      lower.includes('employee') ||
      lower.includes('e100') ||
      lower.includes('manager') ||
      lower.includes('spent') ||
      lower.includes('spend') ||
      lower.includes('salary') ||
      lower.includes('compensation') ||
      lower.includes('approve')
    ) {
      onSelectWorkspace('agent', trimmed);
    } else {
      onSelectWorkspace('rag', trimmed);
    }
  };

  const policyExamples = [
    'What is the meal per diem allowance for domestic travel?',
    'How much does the company match 401(k) contributions?',
    'What are the core collaboration hours for remote employees?',
    'How many annual leave days do employees receive per calendar year?',
  ];

  const agentExamples = [
    "Show employee E1001's profile and manager.",
    'How much has E1001 spent on travel claims?',
    'How many annual leave days does E1001 have left?',
    'Show confidential compensation details for employee E1000.',
  ];

  return (
    <div className="max-w-6xl w-full mx-auto px-4 sm:px-6 py-4 sm:py-8 space-y-7 animate-in fade-in duration-150">
      {/* 1. Concise Product Welcome Banner */}
      <section
        aria-label="Welcome Overview"
        className="rounded-2xl border border-[#E9E5DF] dark:border-[#2F3540] bg-[#FFFEFC] dark:bg-[#21252D] p-6 sm:p-8 shadow-[0_2px_8px_rgba(38,49,66,0.03)]"
      >
        <div className="max-w-3xl space-y-3">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-[#E5F5F1] dark:bg-[#1A2D2A] border border-[#C7E9E2] dark:border-[#244742] text-[#263142] dark:text-[#A9DED5]">
            <Sparkles className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5]" />
            <span>Enterprise Knowledge &amp; Workflow Platform</span>
          </div>

          {/* Understated Editorial Serif Headline */}
          <h1 className="font-serif text-2xl sm:text-3xl text-[#263142] dark:text-[#EBEFF5] tracking-tight font-normal leading-snug">
            Enterprise Support AI Agent
          </h1>

          <p className="text-xs sm:text-sm text-[#697582] dark:text-[#9CA6B5] leading-relaxed font-normal">
            Unified enterprise assistant combining hybrid policy retrieval (ChromaDB + BM25 + Cross-Encoder), PostgreSQL operational records, LangGraph multi-agent orchestration, and human-in-the-loop governance.
          </p>
        </div>

        {/* 2. Unified Prompt Composer */}
        <div className="mt-6">
          <form
            onSubmit={handlePromptSubmit}
            className="relative rounded-2xl border border-[#E9E5DF] dark:border-[#2F3540] bg-[#FFFFFF] dark:bg-[#1B1E24] focus-within:border-[#A9DED5] focus-within:ring-2 focus-within:ring-[#A9DED5]/30 dark:focus-within:border-[#368F88] dark:focus-within:ring-[#368F88]/20 transition-all shadow-[0_1px_3px_rgba(38,49,66,0.03)]"
          >
            <div className="flex items-center gap-3 px-4 pt-3.5 pb-2">
              <Search className="w-4 h-4 text-[#9299A3] dark:text-[#6E7887] flex-shrink-0" />
              <input
                type="text"
                value={promptText}
                onChange={(e) => setPromptText(e.target.value)}
                placeholder="Ask about company policies, employee profiles, leave balances, or travel..."
                className="w-full bg-transparent text-xs sm:text-sm text-[#263142] dark:text-[#EBEFF5] placeholder-[#9299A3] dark:placeholder-[#6E7887] outline-none"
              />
            </div>

            <div className="flex items-center justify-between px-4 pb-3 pt-1 border-t border-[#E9E5DF]/60 dark:border-[#2F3540]/60">
              <span className="text-[11px] font-mono text-[#9299A3] dark:text-[#6E7887] flex items-center gap-1">
                <CornerDownLeft className="w-3 h-3 text-[#9299A3] dark:text-[#6E7887]" />
                <span>Enter to dispatch to the appropriate workspace</span>
              </span>

              <button
                type="submit"
                disabled={!promptText.trim()}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-[#368F88] hover:bg-[#2B7771] disabled:opacity-40 text-white transition-colors cursor-pointer shadow-[0_1px_2px_rgba(38,49,66,0.05)]"
              >
                <span>Submit</span>
                <Send className="w-3 h-3" />
              </button>
            </div>
          </form>
        </div>
      </section>

      {/* 3. Two Primary Modular Workspace Cards */}
      <section aria-label="Workspace Selection" className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-[#697582] dark:text-[#9CA6B5]">
            Select an Enterprise Workspace
          </h2>
          <span className="text-xs text-[#9299A3] dark:text-[#6E7887]">
            2 specialized workspaces available
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Card 1: Policy Assistant */}
          <div className="rounded-2xl border border-[#E9E5DF] dark:border-[#2F3540] bg-[#FFFEFC] dark:bg-[#21252D] p-6 flex flex-col justify-between shadow-[0_1px_3px_rgba(38,49,66,0.03)] hover:border-[#A9DED5] dark:hover:border-[#368F88] transition-colors">
            <div className="space-y-4">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  {/* Pastel Mint Icon Container */}
                  <div className="p-2.5 rounded-xl bg-[#E5F5F1] dark:bg-[#1A2D2A] border border-[#C7E9E2] dark:border-[#244742] text-[#368F88] dark:text-[#A9DED5]">
                    <BookOpen className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-[#263142] dark:text-[#EBEFF5]">
                      Policy Assistant
                    </h3>
                    <p className="text-xs text-[#697582] dark:text-[#9CA6B5]">
                      Document-grounded enterprise policy research
                    </p>
                  </div>
                </div>

                <span className="px-2 py-0.5 rounded-md text-[10px] font-mono font-medium bg-[#F8F6F2] dark:bg-[#1B1E24] text-[#697582] dark:text-[#9CA6B5] border border-[#E9E5DF] dark:border-[#2F3540]">
                  Hybrid RAG
                </span>
              </div>

              <p className="text-xs text-[#697582] dark:text-[#9CA6B5] leading-relaxed font-normal">
                Ask questions about company policies and inspect verifiable supporting evidence synthesized strictly from indexed documentation.
              </p>

              {/* Supported Capabilities */}
              <div className="space-y-1.5 pt-2 border-t border-[#E9E5DF]/60 dark:border-[#2F3540]/60">
                <div className="text-[10px] font-semibold uppercase tracking-wider text-[#9299A3] dark:text-[#6E7887]">
                  Supported Features
                </div>
                <div className="flex flex-wrap gap-1.5 text-[11px] text-[#697582] dark:text-[#9CA6B5]">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-[#F8F6F2] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540]">
                    <CheckCircle2 className="w-3 h-3 text-[#368F88] dark:text-[#A9DED5]" />
                    ChromaDB + BM25 Fusion
                  </span>
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-[#F8F6F2] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540]">
                    <CheckCircle2 className="w-3 h-3 text-[#368F88] dark:text-[#A9DED5]" />
                    Cross-Encoder Reranking
                  </span>
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-[#F8F6F2] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540]">
                    <CheckCircle2 className="w-3 h-3 text-[#368F88] dark:text-[#A9DED5]" />
                    Verifiable Citations
                  </span>
                </div>
              </div>

              {/* Sample Questions */}
              <div className="space-y-1.5 pt-2">
                <div className="text-[10px] font-semibold uppercase tracking-wider text-[#9299A3] dark:text-[#6E7887]">
                  Example Inquiries
                </div>
                <div className="space-y-1">
                  {policyExamples.slice(0, 2).map((q, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => onSelectWorkspace('rag', q)}
                      className="w-full text-left p-2 rounded-lg text-[11px] text-[#263142] dark:text-[#EBEFF5] hover:text-[#368F88] dark:hover:text-[#A9DED5] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] transition-colors flex items-center justify-between group cursor-pointer"
                    >
                      <span className="truncate">&ldquo;{q}&rdquo;</span>
                      <ArrowRight className="w-3 h-3 text-[#9299A3] group-hover:text-[#368F88] dark:group-hover:text-[#A9DED5] flex-shrink-0 ml-1 transition-transform group-hover:translate-x-0.5" />
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Launch Action */}
            <div className="mt-5 pt-4 border-t border-[#E9E5DF]/60 dark:border-[#2F3540]/60">
              <button
                type="button"
                onClick={() => onSelectWorkspace('rag')}
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-medium bg-[#368F88] hover:bg-[#2B7771] text-white transition-colors cursor-pointer shadow-[0_1px_2px_rgba(38,49,66,0.05)]"
              >
                <span>Open Policy Assistant Workspace</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Card 2: Enterprise AI Agent */}
          <div className="rounded-2xl border border-[#E9E5DF] dark:border-[#2F3540] bg-[#FFFEFC] dark:bg-[#21252D] p-6 flex flex-col justify-between shadow-[0_1px_3px_rgba(38,49,66,0.03)] hover:border-[#DCCEEF] dark:hover:border-[#368F88] transition-colors">
            <div className="space-y-4">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  {/* Pastel Lavender Icon Container */}
                  <div className="p-2.5 rounded-xl bg-[#DCCEEF] dark:bg-[#39344D] border border-[#CBB8E3] dark:border-[#4A4463] text-[#5A4384] dark:text-[#DCCEEF]">
                    <Bot className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-[#263142] dark:text-[#EBEFF5]">
                      Enterprise AI Agent
                    </h3>
                    <p className="text-xs text-[#697582] dark:text-[#9CA6B5]">
                      Multi-agent coordinator &amp; structured tool execution
                    </p>
                  </div>
                </div>

                <span className="px-2 py-0.5 rounded-md text-[10px] font-mono font-medium bg-[#F8F6F2] dark:bg-[#1B1E24] text-[#697582] dark:text-[#9CA6B5] border border-[#E9E5DF] dark:border-[#2F3540]">
                  LangGraph
                </span>
              </div>

              <p className="text-xs text-[#697582] dark:text-[#9CA6B5] leading-relaxed font-normal">
                Complete structured tasks using specialized domain workers (HR Policy, Employee Records, Travel &amp; Expenses) with human-in-the-loop approval gates.
              </p>

              {/* Supported Capabilities */}
              <div className="space-y-1.5 pt-2 border-t border-[#E9E5DF]/60 dark:border-[#2F3540]/60">
                <div className="text-[10px] font-semibold uppercase tracking-wider text-[#9299A3] dark:text-[#6E7887]">
                  Supported Features
                </div>
                <div className="flex flex-wrap gap-1.5 text-[11px] text-[#697582] dark:text-[#9CA6B5]">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-[#F8F6F2] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540]">
                    <CheckCircle2 className="w-3 h-3 text-[#368F88] dark:text-[#A9DED5]" />
                    Supervisor Task Routing
                  </span>
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-[#F8F6F2] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540]">
                    <CheckCircle2 className="w-3 h-3 text-[#368F88] dark:text-[#A9DED5]" />
                    PostgreSQL Operations
                  </span>
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-[#F8F6F2] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540]">
                    <CheckCircle2 className="w-3 h-3 text-[#368F88] dark:text-[#A9DED5]" />
                    Human Authorization Gate
                  </span>
                </div>
              </div>

              {/* Sample Tasks */}
              <div className="space-y-1.5 pt-2">
                <div className="text-[10px] font-semibold uppercase tracking-wider text-[#9299A3] dark:text-[#6E7887]">
                  Example Tasks
                </div>
                <div className="space-y-1">
                  {agentExamples.slice(0, 2).map((q, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => onSelectWorkspace('agent', q)}
                      className="w-full text-left p-2 rounded-lg text-[11px] text-[#263142] dark:text-[#EBEFF5] hover:text-[#368F88] dark:hover:text-[#A9DED5] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] transition-colors flex items-center justify-between group cursor-pointer"
                    >
                      <span className="truncate">&ldquo;{q}&rdquo;</span>
                      <ArrowRight className="w-3 h-3 text-[#9299A3] group-hover:text-[#368F88] dark:group-hover:text-[#A9DED5] flex-shrink-0 ml-1 transition-transform group-hover:translate-x-0.5" />
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Launch Action */}
            <div className="mt-5 pt-4 border-t border-[#E9E5DF]/60 dark:border-[#2F3540]/60">
              <button
                type="button"
                onClick={() => onSelectWorkspace('agent')}
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-medium bg-[#368F88] hover:bg-[#2B7771] text-white transition-colors cursor-pointer shadow-[0_1px_2px_rgba(38,49,66,0.05)]"
              >
                <span>Open Enterprise AI Agent Workspace</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* 4. Knowledge Base Summary Strip */}
      <section
        aria-label="Indexed Knowledge Base Documents"
        className="rounded-2xl border border-[#E9E5DF] dark:border-[#2F3540] bg-[#FFFEFC] dark:bg-[#21252D] p-5 shadow-[0_1px_3px_rgba(38,49,66,0.03)]"
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-[#368F88] dark:text-[#A9DED5]" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-[#263142] dark:text-[#EBEFF5]">
              Indexed Knowledge Sources ({INDEXED_POLICY_DOCUMENTS.length} Documents)
            </h3>
          </div>
          {onOpenKnowledgeBase && (
            <button
              type="button"
              onClick={onOpenKnowledgeBase}
              className="text-xs font-medium text-[#368F88] dark:text-[#A9DED5] hover:text-[#2B7771] flex items-center gap-1 cursor-pointer"
            >
              <span>Explore Knowledge Base</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
          {INDEXED_POLICY_DOCUMENTS.map((doc, idx) => {
            // Subtle pastel colors for each document card icon
            const pastelColors = [
              'bg-[#E5F5F1] text-[#368F88] border-[#C7E9E2]',
              'bg-[#DCCEEF] text-[#5A4384] border-[#CBB8E3]',
              'bg-[#F7C9B8] text-[#9A4927] border-[#F1B5A0]',
              'bg-[#CFE5D6] text-[#2F855A] border-[#B7D9C2]',
            ];
            const pastel = pastelColors[idx % pastelColors.length];

            return (
              <button
                key={doc.id}
                type="button"
                onClick={() => onSelectWorkspace('rag')}
                className="text-left p-3 rounded-xl bg-[#F8F6F2] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540] hover:border-[#A9DED5] dark:hover:border-[#368F88] transition-colors cursor-pointer group"
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className={`font-mono text-[9px] font-bold px-1.5 py-0.2 rounded border ${pastel}`}>
                    {doc.fileType}
                  </span>
                  <span className="text-[10px] font-mono text-[#697582] dark:text-[#9CA6B5]">
                    {doc.chunkCount} chunks
                  </span>
                </div>
                <div className="text-xs font-semibold text-[#263142] dark:text-[#EBEFF5] truncate group-hover:text-[#368F88] dark:group-hover:text-[#A9DED5] transition-colors">
                  {doc.title}
                </div>
                <div className="text-[10px] text-[#9299A3] dark:text-[#6E7887] font-mono mt-0.5 truncate">
                  {doc.filename}
                </div>
              </button>
            );
          })}
        </div>
      </section>
    </div>
  );
}
