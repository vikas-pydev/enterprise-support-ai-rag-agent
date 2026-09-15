'use client';

import React from 'react';
import { BookOpen, Bot, Sparkles, Database, CheckCircle2, Clock, ShieldAlert, Cpu } from 'lucide-react';

export type AppMode = 'rag' | 'agent';

interface ModeSelectorProps {
  activeMode: AppMode;
  onSelectMode: (mode: AppMode) => void;
}

export function ModeSelector({ activeMode, onSelectMode }: ModeSelectorProps) {
  return (
    <div
      role="tablist"
      aria-label="Application Workspace Selector"
      className="w-full grid grid-cols-1 md:grid-cols-2 gap-4"
    >
      {/* Mode 1: Policy Assistant */}
      <button
        type="button"
        role="tab"
        id="tab-policy"
        aria-selected={activeMode === 'rag'}
        aria-controls="panel-policy"
        onClick={() => onSelectMode('rag')}
        className={`relative text-left p-5 rounded-3xl border transition-all duration-200 outline-none cursor-pointer ${
          activeMode === 'rag'
            ? 'bg-white dark:bg-slate-900 border-cyan-500/80 shadow-[0_0_25px_rgba(6,182,212,0.15)] ring-2 ring-cyan-500/30'
            : 'bg-white/60 dark:bg-slate-900/40 border-slate-200 dark:border-slate-800/80 hover:bg-slate-50 dark:hover:bg-slate-900/80 hover:border-slate-300 dark:hover:border-slate-700/80'
        }`}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div
              className={`p-2.5 rounded-2xl border ${
                activeMode === 'rag'
                  ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-600 dark:text-cyan-400'
                  : 'bg-slate-100 dark:bg-slate-800/60 border-slate-200 dark:border-slate-700/50 text-slate-500 dark:text-slate-400'
              }`}
            >
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  Policy Assistant
                </h3>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-cyan-100 dark:bg-cyan-950/80 border border-cyan-200 dark:border-cyan-500/30 text-cyan-700 dark:text-cyan-300">
                  Hybrid RAG
                </span>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5 font-medium">
                Grounded company policy search
              </p>
            </div>
          </div>

          {activeMode === 'rag' && (
            <span className="flex h-2.5 w-2.5 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-cyan-500" />
            </span>
          )}
        </div>

        <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/60 flex flex-wrap gap-2 text-[11px] text-slate-600 dark:text-slate-400 font-medium">
          <span className="inline-flex items-center gap-1 bg-slate-100 dark:bg-slate-800/50 px-2 py-0.5 rounded-lg border border-slate-200 dark:border-slate-700/40">
            <Sparkles className="w-3 h-3 text-cyan-500 dark:text-cyan-400" /> ChromaDB + BM25
          </span>
          <span className="inline-flex items-center gap-1 bg-slate-100 dark:bg-slate-800/50 px-2 py-0.5 rounded-lg border border-slate-200 dark:border-slate-700/40">
            <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400" /> Cross-Encoder Rerank
          </span>
          <span className="inline-flex items-center gap-1 bg-slate-100 dark:bg-slate-800/50 px-2 py-0.5 rounded-lg border border-slate-200 dark:border-slate-700/40">
            <ShieldAlert className="w-3 h-3 text-amber-600 dark:text-amber-400" /> Refusal Safeguards
          </span>
        </div>
      </button>

      {/* Mode 2: AI Agent */}
      <button
        type="button"
        role="tab"
        id="tab-agent"
        aria-selected={activeMode === 'agent'}
        aria-controls="panel-agent"
        onClick={() => onSelectMode('agent')}
        className={`relative text-left p-5 rounded-3xl border transition-all duration-200 outline-none cursor-pointer ${
          activeMode === 'agent'
            ? 'bg-white dark:bg-slate-900 border-indigo-500/80 shadow-[0_0_25px_rgba(99,102,241,0.15)] ring-2 ring-indigo-500/30'
            : 'bg-white/60 dark:bg-slate-900/40 border-slate-200 dark:border-slate-800/80 hover:bg-slate-50 dark:hover:bg-slate-900/80 hover:border-slate-300 dark:hover:border-slate-700/80'
        }`}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div
              className={`p-2.5 rounded-2xl border ${
                activeMode === 'agent'
                  ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-600 dark:text-indigo-400'
                  : 'bg-slate-100 dark:bg-slate-800/60 border-slate-200 dark:border-slate-700/50 text-slate-500 dark:text-slate-400'
              }`}
            >
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  Enterprise AI Agent
                </h3>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-100 dark:bg-indigo-950/80 border border-indigo-200 dark:border-indigo-500/30 text-indigo-700 dark:text-indigo-300">
                  LangGraph Multi-Agent
                </span>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5 font-medium">
                Multi-step enterprise task assistant
              </p>
            </div>
          </div>

          {activeMode === 'agent' && (
            <span className="flex h-2.5 w-2.5 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-indigo-500" />
            </span>
          )}
        </div>

        <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/60 flex flex-wrap gap-2 text-[11px] text-slate-600 dark:text-slate-400 font-medium">
          <span className="inline-flex items-center gap-1 bg-slate-100 dark:bg-slate-800/50 px-2 py-0.5 rounded-lg border border-slate-200 dark:border-slate-700/40">
            <Database className="w-3 h-3 text-indigo-500 dark:text-indigo-400" /> PostgreSQL Tools
          </span>
          <span className="inline-flex items-center gap-1 bg-slate-100 dark:bg-slate-800/50 px-2 py-0.5 rounded-lg border border-slate-200 dark:border-slate-700/40">
            <Clock className="w-3 h-3 text-cyan-500 dark:text-cyan-400" /> Checkpoints
          </span>
          <span className="inline-flex items-center gap-1 bg-slate-100 dark:bg-slate-800/50 px-2 py-0.5 rounded-lg border border-slate-200 dark:border-slate-700/40">
            <ShieldAlert className="w-3 h-3 text-amber-500 dark:text-amber-400" /> Human Approval
          </span>
        </div>
      </button>
    </div>
  );
}

