'use client';

import React, { useState } from 'react';
import { CitationSource } from '@/types/api';
import { CitationCard } from './CitationCard';
import { BookMarked, ChevronDown, ChevronUp } from 'lucide-react';

interface CitationListProps {
  sources: CitationSource[];
}

export function CitationList({ sources }: CitationListProps) {
  const [isOpen, setIsOpen] = useState<boolean>(true);

  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-800/80">
      <div className="flex items-center justify-between mb-3">
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-2 text-xs font-bold text-slate-800 dark:text-slate-300 hover:text-slate-950 dark:hover:text-white transition-colors cursor-pointer"
        >
          <BookMarked className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
          <span>Verifiable Sources</span>
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold font-mono bg-cyan-100 dark:bg-cyan-950/80 text-cyan-700 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-500/30">
            {sources.length}
          </span>
          <span className="text-slate-400 dark:text-slate-500 text-[11px] ml-1 font-normal">
            {isOpen ? '(Click to collapse)' : '(Click to expand)'}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          aria-label={isOpen ? 'Collapse sources list' : 'Expand sources list'}
          className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 text-xs p-1 cursor-pointer"
        >
          {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {isOpen && (
        <div className="space-y-2.5 animate-in fade-in duration-150">
          {sources.map((src, index) => (
            <CitationCard key={src.chunk_uid || index} source={src} />
          ))}
        </div>
      )}
    </div>
  );
}

