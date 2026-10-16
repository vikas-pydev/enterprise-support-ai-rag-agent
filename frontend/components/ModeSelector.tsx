'use client';

import React from 'react';
import { BookOpen, Bot, Sparkles, Database, CheckCircle2, Clock, ShieldAlert } from 'lucide-react';

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
      className="w-full grid grid-cols-1 md:grid-cols-2 gap-3.5 select-none"
    >
      {/* Mode 1: Policy Assistant */}
      <button
        type="button"
        role="tab"
        id="tab-policy"
        aria-selected={activeMode === 'rag'}
        aria-controls="panel-policy"
        onClick={() => onSelectMode('rag')}
        className={`relative text-left p-4 sm:p-5 rounded-2xl border transition-colors outline-none cursor-pointer shadow-[0_1px_3px_rgba(38,49,66,0.03)] ${
          activeMode === 'rag'
            ? 'bg-[#FFFEFC] dark:bg-[#21252D] border-[#368F88] ring-1 ring-[#368F88]/30'
            : 'bg-[#FFFEFC] dark:bg-[#21252D] border-[#E9E5DF] dark:border-[#2F3540] hover:border-[#A9DED5] dark:hover:border-[#368F88]'
        }`}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div
              className={`p-2 rounded-xl border ${
                activeMode === 'rag'
                  ? 'bg-[#E5F5F1] dark:bg-[#1A2D2A] border-[#C7E9E2] dark:border-[#244742] text-[#368F88] dark:text-[#A9DED5]'
                  : 'bg-[#F8F6F2] dark:bg-[#1B1E24] border-[#E9E5DF] dark:border-[#2F3540] text-[#697582] dark:text-[#9CA6B5]'
              }`}
            >
              <BookOpen className="w-4 h-4 sm:w-5 sm:h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm sm:text-base font-semibold text-[#263142] dark:text-[#EBEFF5]">
                  Policy Assistant
                </h3>
                <span className="px-2 py-0.2 rounded-full text-[10px] font-mono font-medium bg-[#E5F5F1] dark:bg-[#1A2D2A] border border-[#C7E9E2] dark:border-[#244742] text-[#263142] dark:text-[#A9DED5]">
                  Hybrid RAG
                </span>
              </div>
              <p className="text-xs text-[#697582] dark:text-[#9CA6B5] mt-0.5 font-normal">
                Grounded company policy search
              </p>
            </div>
          </div>

          {activeMode === 'rag' && (
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#368F88] opacity-60" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#368F88]" />
            </span>
          )}
        </div>

        <div className="mt-3.5 pt-3 border-t border-[#E9E5DF]/60 dark:border-[#2F3540]/60 flex flex-wrap gap-1.5 text-[11px] text-[#697582] dark:text-[#9CA6B5] font-normal">
          <span className="inline-flex items-center gap-1 bg-[#F8F6F2] dark:bg-[#1B1E24] px-2 py-0.5 rounded-md border border-[#E9E5DF] dark:border-[#2F3540]">
            <Sparkles className="w-3 h-3 text-[#368F88] dark:text-[#A9DED5]" /> ChromaDB + BM25
          </span>
          <span className="inline-flex items-center gap-1 bg-[#F8F6F2] dark:bg-[#1B1E24] px-2 py-0.5 rounded-md border border-[#E9E5DF] dark:border-[#2F3540]">
            <CheckCircle2 className="w-3 h-3 text-[#368F88] dark:text-[#A9DED5]" /> Cross-Encoder Rerank
          </span>
          <span className="inline-flex items-center gap-1 bg-[#F8F6F2] dark:bg-[#1B1E24] px-2 py-0.5 rounded-md border border-[#E9E5DF] dark:border-[#2F3540]">
            <ShieldAlert className="w-3 h-3 text-[#368F88] dark:text-[#A9DED5]" /> Refusal Safeguards
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
        className={`relative text-left p-4 sm:p-5 rounded-2xl border transition-colors outline-none cursor-pointer shadow-[0_1px_3px_rgba(38,49,66,0.03)] ${
          activeMode === 'agent'
            ? 'bg-[#FFFEFC] dark:bg-[#21252D] border-[#368F88] ring-1 ring-[#368F88]/30'
            : 'bg-[#FFFEFC] dark:bg-[#21252D] border-[#E9E5DF] dark:border-[#2F3540] hover:border-[#A9DED5] dark:hover:border-[#368F88]'
        }`}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div
              className={`p-2 rounded-xl border ${
                activeMode === 'agent'
                  ? 'bg-[#DCCEEF] dark:bg-[#39344D] border-[#CBB8E3] dark:border-[#4A4463] text-[#5A4384] dark:text-[#DCCEEF]'
                  : 'bg-[#F8F6F2] dark:bg-[#1B1E24] border-[#E9E5DF] dark:border-[#2F3540] text-[#697582] dark:text-[#9CA6B5]'
              }`}
            >
              <Bot className="w-4 h-4 sm:w-5 sm:h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm sm:text-base font-semibold text-[#263142] dark:text-[#EBEFF5]">
                  Enterprise AI Agent
                </h3>
                <span className="px-2 py-0.2 rounded-full text-[10px] font-mono font-medium bg-[#F8F6F2] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540] text-[#697582] dark:text-[#9CA6B5]">
                  LangGraph
                </span>
              </div>
              <p className="text-xs text-[#697582] dark:text-[#9CA6B5] mt-0.5 font-normal">
                Multi-step enterprise task assistant
              </p>
            </div>
          </div>

          {activeMode === 'agent' && (
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#368F88] opacity-60" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#368F88]" />
            </span>
          )}
        </div>

        <div className="mt-3.5 pt-3 border-t border-[#E9E5DF]/60 dark:border-[#2F3540]/60 flex flex-wrap gap-1.5 text-[11px] text-[#697582] dark:text-[#9CA6B5] font-normal">
          <span className="inline-flex items-center gap-1 bg-[#F8F6F2] dark:bg-[#1B1E24] px-2 py-0.5 rounded-md border border-[#E9E5DF] dark:border-[#2F3540]">
            <Database className="w-3 h-3 text-[#368F88] dark:text-[#A9DED5]" /> PostgreSQL Tools
          </span>
          <span className="inline-flex items-center gap-1 bg-[#F8F6F2] dark:bg-[#1B1E24] px-2 py-0.5 rounded-md border border-[#E9E5DF] dark:border-[#2F3540]">
            <Clock className="w-3 h-3 text-[#368F88] dark:text-[#A9DED5]" /> Checkpoints
          </span>
          <span className="inline-flex items-center gap-1 bg-[#F8F6F2] dark:bg-[#1B1E24] px-2 py-0.5 rounded-md border border-[#E9E5DF] dark:border-[#2F3540]">
            <ShieldAlert className="w-3 h-3 text-[#368F88] dark:text-[#A9DED5]" /> Human Approval
          </span>
        </div>
      </button>
    </div>
  );
}
