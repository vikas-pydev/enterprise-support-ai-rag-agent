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
        className="inline-flex items-center gap-1.5 text-[#697582] dark:text-[#9CA6B5] hover:text-[#263142] dark:hover:text-[#EBEFF5] transition-colors font-mono select-none cursor-pointer"
      >
        <Info className="w-3 h-3 text-[#368F88] dark:text-[#A9DED5]" />
        <span>Retrieval &amp; Grounding Details</span>
        {isOpen ? <ChevronUp className="w-3 h-3 ml-0.5" /> : <ChevronDown className="w-3 h-3 ml-0.5" />}
      </button>

      {isOpen && (
        <div className="mt-2 p-3 rounded-2xl bg-[#F8F6F2] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540] grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 text-[#263142] dark:text-[#EBEFF5] font-mono animate-in fade-in duration-150">
          <div className="flex items-center gap-2">
            <Layers className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5] flex-shrink-0" />
            <div>
              <div className="text-[10px] text-[#9299A3] dark:text-[#6E7887]">Retrieval Pipeline</div>
              <div className="text-[11px] font-semibold text-[#263142] dark:text-[#EBEFF5]">Hybrid Dense + BM25</div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Cpu className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5] flex-shrink-0" />
            <div>
              <div className="text-[10px] text-[#9299A3] dark:text-[#6E7887]">Reranker Model</div>
              <div className="text-[11px] font-semibold text-[#263142] dark:text-[#EBEFF5]">Cross-Encoder (MiniLM)</div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <FileSearch className="w-3.5 h-3.5 text-[#2F855A] dark:text-[#34D399] flex-shrink-0" />
            <div>
              <div className="text-[10px] text-[#9299A3] dark:text-[#6E7887]">Grounded Citations</div>
              <div className="text-[11px] font-semibold text-[#2F855A] dark:text-[#34D399]">
                {sources.length} {sources.length === 1 ? 'passage' : 'passages'}
              </div>
            </div>
          </div>

          {bestScore !== null && (
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-3.5 h-3.5 text-[#B45309] dark:text-[#FBBF24] flex-shrink-0" />
              <div>
                <div className="text-[10px] text-[#9299A3] dark:text-[#6E7887]">Max Rerank Score</div>
                <div className="text-[11px] font-semibold text-[#B45309] dark:text-[#FBBF24]">{bestScore.toFixed(3)}</div>
              </div>
            </div>
          )}

          {durationMs !== undefined && (
            <div className="flex items-center gap-2">
              <Timer className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5] flex-shrink-0" />
              <div>
                <div className="text-[10px] text-[#9299A3] dark:text-[#6E7887]">Total Latency</div>
                <div className="text-[11px] font-semibold text-[#368F88] dark:text-[#A9DED5]">{durationMs} ms</div>
              </div>
            </div>
          )}

          <div className="flex items-center gap-2">
            <ShieldCheck className={`w-3.5 h-3.5 flex-shrink-0 ${isRefusal ? 'text-[#9B1C1C] dark:text-[#F87171]' : 'text-[#2F855A] dark:text-[#34D399]'}`} />
            <div>
              <div className="text-[10px] text-[#9299A3] dark:text-[#6E7887]">Grounding Verdict</div>
              <div className={`text-[11px] font-semibold ${isRefusal ? 'text-[#9B1C1C] dark:text-[#F87171]' : 'text-[#2F855A] dark:text-[#34D399]'}`}>
                {isRefusal ? 'Refusal (No Evidence)' : 'Evidence Supported'}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
