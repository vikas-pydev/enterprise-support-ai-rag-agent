'use client';

import React, { useState } from 'react';
import { CitationSource } from '@/types/api';
import { CitationCard } from './CitationCard';
import { BookMarked, ChevronDown, ChevronUp } from 'lucide-react';

interface CitationListProps {
  sources: CitationSource[];
  onSelectCitation?: (source: CitationSource) => void;
  selectedCitationUid?: string | null;
}

export function CitationList({
  sources,
  onSelectCitation,
  selectedCitationUid,
}: CitationListProps) {
  const [isOpen, setIsOpen] = useState<boolean>(true);

  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <div className="mt-4 pt-4 border-t border-[#E9E5DF] dark:border-[#2F3540]">
      <div className="flex items-center justify-between mb-3">
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-2 text-xs font-semibold text-[#263142] dark:text-[#EBEFF5] hover:text-[#368F88] dark:hover:text-[#A9DED5] transition-colors cursor-pointer"
        >
          <BookMarked className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5]" />
          <span>Verifiable Sources</span>
          <span className="px-2 py-0.2 rounded-full text-[10px] font-medium font-mono bg-[#E5F5F1] dark:bg-[#1A2D2A] text-[#263142] dark:text-[#A9DED5] border border-[#C7E9E2] dark:border-[#244742]">
            {sources.length}
          </span>
          <span className="text-[#9299A3] dark:text-[#6E7887] text-[11px] ml-1 font-normal">
            {isOpen ? '(Click to collapse)' : '(Click to expand)'}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          aria-label={isOpen ? 'Collapse sources list' : 'Expand sources list'}
          className="text-[#9299A3] hover:text-[#263142] dark:hover:text-[#EBEFF5] text-xs p-1 cursor-pointer"
        >
          {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {isOpen && (
        <div className="space-y-2.5 animate-in fade-in duration-150">
          {sources.map((src, index) => (
            <CitationCard
              key={src.chunk_uid || index}
              source={src}
              onSelectCitation={onSelectCitation}
              isSelected={selectedCitationUid === src.chunk_uid}
            />
          ))}
        </div>
      )}
    </div>
  );
}
