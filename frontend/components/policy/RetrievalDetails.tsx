'use client';

import React, { useState } from 'react';
import { CitationSource } from '@/types/api';
import { ShieldCheck, Info, ChevronDown, ChevronUp, Cpu, Layers, Timer, FileSearch } from 'lucide-react';

interface RetrievalDetailsProps {
  sources?: CitationSource[];
  isRefusal?: boolean;
  durationMs?: number;
}

export function RetrievalDetails({ sources = [], isRefusal = false, durationMs }: RetrievalDetailsProps) {
  const [isOpen, setIsOpen] = useState<boolean>(false);

  const bestScore = sources.length > 0
    ? Math.max(...sources.map((s) => s.rerank_score))
    : null;

  return (
    <div className="mt-3 pt-2 text-[11px]">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        className="inline-flex items-center gap-1.5 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 transition-colors font-mono select-none cursor-pointer"
      >
        <Info className="w-3 h-3 text-cyan-600 dark:text-cyan-400" />
        <span>Retrieval &amp; Grounding Details</span>
        {isOpen ? <ChevronUp className="w-3 h-3 ml-0.5" /> : <ChevronDown className="w-3 h-3 ml-0.5" />}
      </button>

      {isOpen && (
        <div className="mt-2 p-3 rounded-2xl bg-slate-50 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800/80 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 text-slate-700 dark:text-slate-300 font-mono animate-in fade-in duration-150">
          <div className="flex items-center gap-2">
            <Layers className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400 flex-shrink-0" />
            <div>
              <div className="text-[10px] text-slate-500 dark:text-slate-400">Retrieval Pipeline</div>
              <div className="text-[11px] font-bold text-slate-900 dark:text-slate-200">Hybrid Dense + BM25</div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Cpu className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400 flex-shrink-0" />
            <div>
              <div className="text-[10px] text-slate-500 dark:text-slate-400">Reranker Model</div>
              <div className="text-[11px] font-bold text-slate-900 dark:text-slate-200">Cross-Encoder (MiniLM)</div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <FileSearch className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
            <div>
              <div className="text-[10px] text-slate-500 dark:text-slate-400">Grounded Citations</div>
              <div className="text-[11px] font-bold text-emerald-700 dark:text-emerald-300">
                {sources.length} {sources.length === 1 ? 'passage' : 'passages'}
              </div>
            </div>
          </div>

          {bestScore !== null && (
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 flex-shrink-0" />
              <div>
                <div className="text-[10px] text-slate-500 dark:text-slate-400">Max Rerank Score</div>
                <div className="text-[11px] font-bold text-amber-700 dark:text-amber-300">{bestScore.toFixed(3)}</div>
              </div>
            </div>
          )}

          {durationMs !== undefined && (
            <div className="flex items-center gap-2">
              <Timer className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400 flex-shrink-0" />
              <div>
                <div className="text-[10px] text-slate-500 dark:text-slate-400">Total Latency</div>
                <div className="text-[11px] font-bold text-cyan-700 dark:text-cyan-300">{durationMs} ms</div>
              </div>
            </div>
          )}

          <div className="flex items-center gap-2">
            <ShieldCheck className={`w-3.5 h-3.5 flex-shrink-0 ${isRefusal ? 'text-rose-600 dark:text-rose-400' : 'text-emerald-600 dark:text-emerald-400'}`} />
            <div>
              <div className="text-[10px] text-slate-500 dark:text-slate-400">Grounding Verdict</div>
              <div className={`text-[11px] font-bold ${isRefusal ? 'text-rose-700 dark:text-rose-300' : 'text-emerald-700 dark:text-emerald-300'}`}>
                {isRefusal ? 'Refusal (No Evidence)' : 'Evidence Supported'}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

