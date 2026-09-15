'use client';

import React, { useState } from 'react';
import { CitationSource } from '@/types/api';
import { FileText, Copy, Check, ChevronDown, ChevronUp, Hash } from 'lucide-react';

interface CitationCardProps {
  source: CitationSource;
  defaultExpanded?: boolean;
}

export function CitationCard({ source, defaultExpanded = true }: CitationCardProps) {
  const [isExpanded, setIsExpanded] = useState<boolean>(defaultExpanded);
  const [isCopied, setIsCopied] = useState<boolean>(false);

  const handleCopyPassage = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(source.snippet);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch {
      setIsCopied(false);
    }
  };

  return (
    <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-950/70 overflow-hidden hover:border-slate-300 dark:hover:border-slate-700/80 transition-all text-xs">
      {/* Header bar */}
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center justify-between p-3 cursor-pointer select-none bg-slate-100/60 dark:bg-slate-900/40 hover:bg-slate-200/60 dark:hover:bg-slate-900/70 transition-colors"
      >
        <div className="flex items-center gap-2.5 min-w-0 pr-2">
          {/* Rank Badge */}
          <span className="flex-shrink-0 flex items-center justify-center w-5 h-5 rounded-md bg-cyan-100 dark:bg-cyan-950 border border-cyan-300 dark:border-cyan-500/30 text-cyan-700 dark:text-cyan-300 font-mono text-[10px] font-bold">
            #{source.rank}
          </span>

          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-800 dark:text-slate-200 truncate">
                {source.title || 'Document'}
              </span>
              <span className="font-mono text-[10px] text-cyan-700 dark:text-cyan-400 bg-cyan-50 dark:bg-cyan-950/60 px-1.5 py-0.5 rounded border border-cyan-200 dark:border-cyan-500/20 flex-shrink-0 font-semibold">
                Score: {typeof source.rerank_score === 'number' ? source.rerank_score.toFixed(3) : source.rerank_score}
              </span>
            </div>
            <div className="flex items-center gap-2 text-[10px] text-slate-500 dark:text-slate-400 font-mono mt-0.5 truncate">
              <span className="flex items-center gap-1 truncate">
                <FileText className="w-3 h-3 text-slate-400 flex-shrink-0" />
                <span className="truncate">{source.source_file}</span>
              </span>
              <span>&bull;</span>
              <span className="flex items-center gap-1 text-slate-400 flex-shrink-0">
                <Hash className="w-2.5 h-2.5" />
                <span>{source.chunk_uid}</span>
              </span>
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <button
            type="button"
            onClick={handleCopyPassage}
            aria-label="Copy source passage"
            title={isCopied ? 'Copied!' : 'Copy source snippet'}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors cursor-pointer"
          >
            {isCopied ? (
              <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
            ) : (
              <Copy className="w-3.5 h-3.5" />
            )}
          </button>
          <div className="text-slate-400 p-0.5">
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </div>
        </div>
      </div>

      {/* Snippet Content */}
      {isExpanded && (
        <div className="p-3.5 border-t border-slate-200 dark:border-slate-800/80 bg-white/90 dark:bg-slate-950/90">
          <blockquote className="text-slate-700 dark:text-slate-300 text-xs font-normal leading-relaxed whitespace-pre-wrap pl-3 border-l-2 border-cyan-500 italic">
            &ldquo;{source.snippet.trim()}&rdquo;
          </blockquote>
        </div>
      )}
    </div>
  );
}

