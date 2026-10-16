'use client';

import React, { useState } from 'react';
import { CitationSource } from '@/types/api';
import { FileText, Copy, Check, ChevronDown, ChevronUp, Hash } from 'lucide-react';

interface CitationCardProps {
  source: CitationSource;
  defaultExpanded?: boolean;
  onSelectCitation?: (source: CitationSource) => void;
  isSelected?: boolean;
}

export function CitationCard({
  source,
  defaultExpanded = true,
  onSelectCitation,
  isSelected = false,
}: CitationCardProps) {
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

  const handleCardClick = () => {
    setIsExpanded(!isExpanded);
    if (onSelectCitation) {
      onSelectCitation(source);
    }
  };

  return (
    <div
      className={`rounded-2xl border transition-colors text-xs overflow-hidden ${
        isSelected
          ? 'bg-[#E5F5F1] dark:bg-[#1A2D2A] border-[#A9DED5] dark:border-[#368F88] ring-1 ring-[#368F88]/20'
          : 'bg-[#FFFEFC] dark:bg-[#21252D] border-[#E9E5DF] dark:border-[#2F3540] hover:border-[#A9DED5]/60 dark:hover:border-[#368F88]/60 shadow-[0_1px_2px_rgba(38,49,66,0.02)]'
      }`}
    >
      {/* Header bar */}
      <div
        onClick={handleCardClick}
        className="flex items-center justify-between p-3 cursor-pointer select-none bg-[#FCFAF7] dark:bg-[#1B1E24] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] transition-colors"
      >
        <div className="flex items-center gap-2.5 min-w-0 pr-2">
          {/* Rank Badge */}
          <span className="flex-shrink-0 flex items-center justify-center w-5 h-5 rounded-md bg-[#E5F5F1] dark:bg-[#1A2D2A] border border-[#C7E9E2] dark:border-[#244742] text-[#368F88] dark:text-[#A9DED5] font-mono text-[10px] font-bold">
            #{source.rank}
          </span>

          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-[#263142] dark:text-[#EBEFF5] truncate">
                {source.title || 'Document'}
              </span>
              <span className="font-mono text-[10px] text-[#697582] dark:text-[#9CA6B5] bg-[#F8F6F2] dark:bg-[#21252D] px-1.5 py-0.5 rounded border border-[#E9E5DF] dark:border-[#2F3540] flex-shrink-0 font-medium">
                Score: {typeof source.rerank_score === 'number' ? source.rerank_score.toFixed(3) : source.rerank_score}
              </span>
            </div>
            <div className="flex items-center gap-2 text-[10px] text-[#697582] dark:text-[#9CA6B5] font-mono mt-0.5 truncate">
              <span className="flex items-center gap-1 truncate">
                <FileText className="w-3 h-3 text-[#9299A3] dark:text-[#6E7887] flex-shrink-0" />
                <span className="truncate">{source.source_file}</span>
              </span>
              <span>&bull;</span>
              <span className="flex items-center gap-1 text-[#9299A3] dark:text-[#6E7887] flex-shrink-0">
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
            className="p-1.5 rounded-lg text-[#9299A3] hover:text-[#263142] dark:hover:text-[#EBEFF5] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] transition-colors cursor-pointer"
          >
            {isCopied ? (
              <Check className="w-3.5 h-3.5 text-[#2F855A] dark:text-[#34D399]" />
            ) : (
              <Copy className="w-3.5 h-3.5" />
            )}
          </button>
          <div className="text-[#9299A3] dark:text-[#6E7887] p-0.5">
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </div>
        </div>
      </div>

      {/* Snippet Content */}
      {isExpanded && (
        <div className="p-3.5 border-t border-[#E9E5DF] dark:border-[#2F3540] bg-[#FFFFFF] dark:bg-[#21252D]">
          <blockquote className="text-[#263142] dark:text-[#EBEFF5] text-xs font-normal leading-relaxed whitespace-pre-wrap pl-3 border-l-2 border-[#368F88] italic">
            &ldquo;{source.snippet.trim()}&rdquo;
          </blockquote>
        </div>
      )}
    </div>
  );
}
