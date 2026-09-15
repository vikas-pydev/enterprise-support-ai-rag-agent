'use client';

import React, { useState } from 'react';
import { Header } from '@/components/Header';
import { ModeSelector, AppMode } from '@/components/ModeSelector';
import { PolicyChatWorkspace } from '@/components/policy/PolicyChatWorkspace';
import { AgentChatWorkspace } from '@/components/agent/AgentChatWorkspace';
import { SystemInfoCard } from '@/components/SystemInfoCard';
import { ShieldCheck, Sparkles, ExternalLink, ArrowUpRight } from 'lucide-react';

export default function Home() {
  const [activeMode, setActiveMode] = useState<AppMode>('rag');

  return (
    <div className="flex flex-col min-h-screen">
      {/* Top Application Header */}
      <Header activeMode={activeMode} onModeSelect={setActiveMode} />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 space-y-6 sm:space-y-8">
        {/* Welcome / Overview Hero Banner */}
        <section
          aria-label="Welcome Overview"
          className="relative rounded-3xl border border-slate-200 dark:border-slate-800/80 bg-gradient-to-br from-white via-slate-50 to-slate-100 dark:from-slate-900 dark:via-slate-950 dark:to-slate-900 p-6 sm:p-8 overflow-hidden shadow-xl"
        >
          <div className="absolute top-0 right-0 -mt-8 -mr-8 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
          <div className="relative z-10 max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-50 dark:bg-indigo-950/80 border border-indigo-200 dark:border-indigo-500/30 text-indigo-700 dark:text-indigo-300 mb-3">
              <Sparkles className="w-3.5 h-3.5 text-cyan-500 dark:text-cyan-400" />
              <span>Enterprise AI Platform</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight leading-tight">
              Enterprise Knowledge Base &amp; Conversational Agent
            </h2>
            <p className="mt-2.5 text-xs sm:text-sm text-slate-600 dark:text-slate-300 leading-relaxed font-normal">
              Unified enterprise AI assistant powered by hybrid RAG (ChromaDB + BM25 + Cross-Encoder), PostgreSQL structured data, LangGraph multi-agent coordination, durable thread checkpointing, and human-in-the-loop governance.
            </p>
          </div>
        </section>

        {/* Workspace Selector */}
        <section aria-label="Workspace Selection" className="space-y-2.5">
          <div className="flex items-center justify-between px-1">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Active Application Workspace
            </h2>
            <span className="text-xs text-slate-500 dark:text-slate-400">
              Selected: <strong className="text-slate-900 dark:text-white capitalize">{activeMode === 'rag' ? 'Policy Assistant' : 'Enterprise AI Agent'}</strong>
            </span>
          </div>
          <ModeSelector activeMode={activeMode} onSelectMode={setActiveMode} />
        </section>

        {/* Active Mode Workspace Presentation */}
        <section
          id={activeMode === 'rag' ? 'panel-policy' : 'panel-agent'}
          role="tabpanel"
          aria-labelledby={activeMode === 'rag' ? 'tab-policy' : 'tab-agent'}
        >
          {activeMode === 'rag' ? (
            <PolicyChatWorkspace />
          ) : (
            <AgentChatWorkspace />
          )}
        </section>

        {/* Secondary Developer / Architecture Diagnostics */}
        <section aria-label="Technical Architecture Diagnostics">
          <SystemInfoCard />
        </section>
      </main>

      {/* Global Application Footer */}
      <footer className="border-t border-slate-200 dark:border-slate-800/80 bg-white dark:bg-slate-950 py-6 mt-12 transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500 dark:text-slate-400">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
            <span>Enterprise Support AI Agent &bull; Next.js 16 + TypeScript + Tailwind CSS</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="hidden sm:inline">Streamlit UI available at port 8501</span>
            <a
              href="http://127.0.0.1:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-cyan-600 dark:hover:text-cyan-300 transition-colors flex items-center gap-1 text-cyan-600 dark:text-cyan-400 font-medium"
            >
              <span>Swagger API Docs</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}

