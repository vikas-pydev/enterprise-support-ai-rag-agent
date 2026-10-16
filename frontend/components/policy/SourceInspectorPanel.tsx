'use client';

import React, { useState } from 'react';
import { CitationSource } from '@/types/api';
import { PolicyDocument } from '@/lib/knowledge/documents';
import {
  FileText,
  X,
  Copy,
  Check,
  Hash,
  ShieldCheck,
  BookOpen,
  Info,
} from 'lucide-react';

interface SourceInspectorPanelProps {
  selectedCitation?: CitationSource | null;
  selectedDocument?: PolicyDocument | null;
  onClose: () => void;
  isOpen: boolean;
}

export function SourceInspectorPanel({
  selectedCitation,
  selectedDocument,
  onClose,
  isOpen,
}: SourceInspectorPanelProps) {
  const [copied, setCopied] = useState<boolean>(false);

  if (!isOpen) return null;

  const copyText = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  return (
    <aside
      aria-label="Source Inspector and Document Preview"
      className="w-80 lg:w-96 flex-shrink-0 border-l border-[#E9E5DF] dark:border-[#2F3540] bg-[#FCFAF7] dark:bg-[#1B1E24] flex flex-col justify-between overflow-hidden shadow-sm select-none"
    >
      {/* Panel Header */}
      <div className="p-3.5 border-b border-[#E9E5DF] dark:border-[#2F3540] bg-[#FCFAF7] dark:bg-[#1B1E24] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-[#368F88] dark:text-[#A9DED5]" />
          <h3 className="text-xs font-semibold text-[#263142] dark:text-[#EBEFF5] uppercase tracking-wider">
            {selectedCitation ? 'Citation Inspector' : selectedDocument ? 'Document Preview' : 'Source Inspector'}
          </h3>
        </div>

        <button
          type="button"
          onClick={onClose}
          aria-label="Close Source Inspector"
          title="Close Panel"
          className="p-1 rounded-lg text-[#9299A3] hover:text-[#263142] dark:hover:text-[#EBEFF5] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] transition-colors cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Main Panel Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs select-text scrollbar-thin">
        {selectedCitation ? (
          /* Citation Detail View */
          <div className="space-y-4 animate-in fade-in duration-150">
            {/* Citation Header Card */}
            <div className="p-3.5 rounded-xl border border-[#E9E5DF] dark:border-[#2F3540] bg-[#FFFEFC] dark:bg-[#21252D] space-y-2">
              <div className="flex items-center justify-between gap-2">
                <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-md font-mono text-[10px] font-bold bg-[#E5F5F1] dark:bg-[#1A2D2A] text-[#263142] dark:text-[#A9DED5] border border-[#C7E9E2] dark:border-[#244742]">
                  Rank #{selectedCitation.rank}
                </span>

                <span className="font-mono text-[10px] text-[#697582] dark:text-[#9CA6B5] bg-[#F8F6F2] dark:bg-[#1B1E24] px-2 py-0.5 rounded border border-[#E9E5DF] dark:border-[#2F3540] font-medium">
                  Rerank Score: {typeof selectedCitation.rerank_score === 'number' ? selectedCitation.rerank_score.toFixed(3) : selectedCitation.rerank_score}
                </span>
              </div>

              <div>
                <h4 className="text-sm font-semibold text-[#263142] dark:text-[#EBEFF5]">
                  {selectedCitation.title || 'Referenced Document'}
                </h4>
                <div className="flex items-center gap-2 text-[10px] font-mono text-[#697582] dark:text-[#9CA6B5] mt-1">
                  <span className="flex items-center gap-1 truncate">
                    <FileText className="w-3 h-3 text-[#9299A3] dark:text-[#6E7887] flex-shrink-0" />
                    <span className="truncate">{selectedCitation.source_file}</span>
                  </span>
                  <span>&bull;</span>
                  <span className="flex items-center gap-0.5">
                    <Hash className="w-2.5 h-2.5 text-[#9299A3] dark:text-[#6E7887]" />
                    <span>{selectedCitation.chunk_uid}</span>
                  </span>
                </div>
              </div>
            </div>

            {/* Retrieved Excerpt Passage */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-[#697582] dark:text-[#9CA6B5]">
                  Retrieved Passage Excerpt
                </span>
                <button
                  type="button"
                  onClick={() => copyText(selectedCitation.snippet)}
                  className="flex items-center gap-1 text-[10px] text-[#697582] hover:text-[#263142] dark:text-[#9CA6B5] dark:hover:text-[#EBEFF5] transition-colors cursor-pointer"
                >
                  {copied ? (
                    <>
                      <Check className="w-3 h-3 text-[#2F855A] dark:text-[#34D399]" />
                      <span className="text-[#2F855A] dark:text-[#34D399] font-medium">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3" />
                      <span>Copy Excerpt</span>
                    </>
                  )}
                </button>
              </div>

              <div className="p-3.5 rounded-xl border border-[#E9E5DF] dark:border-[#2F3540] bg-[#FFFEFC] dark:bg-[#21252D]">
                <blockquote className="text-xs text-[#263142] dark:text-[#EBEFF5] leading-relaxed whitespace-pre-wrap pl-3 border-l-2 border-[#368F88] italic">
                  &ldquo;{selectedCitation.snippet.trim()}&rdquo;
                </blockquote>
              </div>
            </div>

            {/* Retrieval Metadata */}
            <div className="space-y-1.5 pt-2 border-t border-[#E9E5DF] dark:border-[#2F3540]">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-[#697582] dark:text-[#9CA6B5] flex items-center gap-1">
                <Info className="w-3 h-3 text-[#368F88] dark:text-[#A9DED5]" />
                <span>Grounding Verification</span>
              </div>
              <div className="p-3 rounded-xl bg-[#FFFEFC] dark:bg-[#21252D] border border-[#E9E5DF] dark:border-[#2F3540] space-y-1.5 text-[11px] font-mono text-[#697582] dark:text-[#9CA6B5]">
                <div className="flex justify-between">
                  <span>Pipeline:</span>
                  <span className="font-semibold text-[#263142] dark:text-[#EBEFF5]">ChromaDB + BM25 + Cross-Encoder</span>
                </div>
                <div className="flex justify-between">
                  <span>Source File:</span>
                  <span className="font-semibold text-[#263142] dark:text-[#EBEFF5]">{selectedCitation.source_file}</span>
                </div>
                <div className="flex justify-between">
                  <span>Chunk UID:</span>
                  <span className="font-semibold text-[#263142] dark:text-[#EBEFF5]">{selectedCitation.chunk_uid}</span>
                </div>
              </div>
            </div>
          </div>
        ) : selectedDocument ? (
          /* Full Document Preview View */
          <div className="space-y-4 animate-in fade-in duration-150">
            {/* Document Header Card */}
            <div className="p-3.5 rounded-xl border border-[#E9E5DF] dark:border-[#2F3540] bg-[#FFFEFC] dark:bg-[#21252D] space-y-2">
              <div className="flex items-center justify-between">
                <span className="px-2 py-0.5 rounded font-mono text-[10px] uppercase font-bold bg-[#E5F5F1] dark:bg-[#1A2D2A] text-[#263142] dark:text-[#A9DED5] border border-[#C7E9E2] dark:border-[#244742]">
                  {selectedDocument.category}
                </span>
                <span className="text-[10px] font-mono text-[#9299A3] dark:text-[#6E7887]">
                  v{selectedDocument.version}
                </span>
              </div>

              <div>
                <h4 className="text-sm font-semibold text-[#263142] dark:text-[#EBEFF5]">
                  {selectedDocument.title}
                </h4>
                <div className="text-[10px] font-mono text-[#697582] dark:text-[#9CA6B5] mt-0.5">
                  data/documents/{selectedDocument.filename}
                </div>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-[#E9E5DF]/60 dark:border-[#2F3540]/60 text-[10px] text-[#697582] dark:text-[#9CA6B5] font-mono">
                <span>{selectedDocument.chunkCount} indexed chunks</span>
                <span>Ingested: 2026-10-16</span>
              </div>
            </div>

            {/* Document Full Text Content */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-[#697582] dark:text-[#9CA6B5]">
                  Full Document Content
                </span>
                <button
                  type="button"
                  onClick={() => copyText(selectedDocument.fullContent)}
                  className="flex items-center gap-1 text-[10px] text-[#697582] hover:text-[#263142] dark:text-[#9CA6B5] dark:hover:text-[#EBEFF5] transition-colors cursor-pointer"
                >
                  {copied ? (
                    <>
                      <Check className="w-3 h-3 text-[#2F855A] dark:text-[#34D399]" />
                      <span className="text-[#2F855A] dark:text-[#34D399] font-medium">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3" />
                      <span>Copy All</span>
                    </>
                  )}
                </button>
              </div>

              <div className="p-3.5 rounded-xl border border-[#E9E5DF] dark:border-[#2F3540] bg-[#FFFEFC] dark:bg-[#21252D] font-sans text-xs text-[#263142] dark:text-[#EBEFF5] whitespace-pre-wrap leading-relaxed max-h-[460px] overflow-y-auto scrollbar-thin">
                {selectedDocument.fullContent}
              </div>
            </div>
          </div>
        ) : (
          /* Empty / Guidance State */
          <div className="text-center py-12 px-4 space-y-3 text-[#9299A3] dark:text-[#6E7887]">
            <BookOpen className="w-8 h-8 mx-auto text-[#9299A3]/60 dark:text-[#6E7887]/60" />
            <div className="text-xs font-semibold text-[#263142] dark:text-[#EBEFF5]">
              No Document or Citation Selected
            </div>
            <p className="text-[11px] leading-relaxed font-normal">
              Click any source citation from an assistant answer or select a policy document from the Knowledge Base panel to inspect its full text and grounding details.
            </p>
          </div>
        )}
      </div>

      {/* Footer Notice */}
      <div className="p-3 border-t border-[#E9E5DF] dark:border-[#2F3540] bg-[#FCFAF7] dark:bg-[#1B1E24] text-[10px] text-[#697582] dark:text-[#9CA6B5] flex items-center gap-1.5">
        <ShieldCheck className="w-3.5 h-3.5 text-[#2F855A] dark:text-[#34D399] flex-shrink-0" />
        <span>Grounded in actual indexed repository document data</span>
      </div>
    </aside>
  );
}
