'use client';

import React, { useState } from 'react';
import {
  Files,
  Search,
  FileText,
  ChevronLeft,
  ChevronRight,
  Database,
} from 'lucide-react';
import { INDEXED_POLICY_DOCUMENTS, PolicyDocument } from '@/lib/knowledge/documents';

interface KnowledgeBasePanelProps {
  selectedDocumentId?: string | null;
  onSelectDocument: (doc: PolicyDocument) => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export function KnowledgeBasePanel({
  selectedDocumentId,
  onSelectDocument,
  isCollapsed = false,
  onToggleCollapse,
}: KnowledgeBasePanelProps) {
  const [searchQuery, setSearchQuery] = useState<string>('');

  const filteredDocs = INDEXED_POLICY_DOCUMENTS.filter((doc) => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    return (
      doc.title.toLowerCase().includes(query) ||
      doc.filename.toLowerCase().includes(query) ||
      doc.category.toLowerCase().includes(query) ||
      doc.summary.toLowerCase().includes(query)
    );
  });

  if (isCollapsed) {
    return (
      <div className="w-12 border-r border-[#E9E5DF] dark:border-[#2F3540] bg-[#FCFAF7] dark:bg-[#1B1E24] flex flex-col items-center py-4 select-none">
        <button
          type="button"
          onClick={onToggleCollapse}
          title="Expand Knowledge Base Panel"
          aria-label="Expand Knowledge Base Panel"
          className="p-2 rounded-xl text-[#697582] hover:text-[#263142] dark:text-[#9CA6B5] dark:hover:text-[#EBEFF5] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] transition-colors cursor-pointer"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
        <div className="writing-vertical text-[11px] font-semibold text-[#9299A3] dark:text-[#6E7887] tracking-wider uppercase mt-8 rotate-180">
          Knowledge Base
        </div>
      </div>
    );
  }

  return (
    <aside
      aria-label="Indexed Policy Documents"
      className="w-72 lg:w-80 flex-shrink-0 border-r border-[#E9E5DF] dark:border-[#2F3540] bg-[#FCFAF7] dark:bg-[#1B1E24] flex flex-col justify-between overflow-hidden transition-colors select-none"
    >
      {/* Panel Header */}
      <div className="p-3.5 border-b border-[#E9E5DF] dark:border-[#2F3540] bg-[#FCFAF7] dark:bg-[#1B1E24] space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Files className="w-4 h-4 text-[#368F88] dark:text-[#A9DED5]" />
            <h3 className="text-xs font-semibold text-[#263142] dark:text-[#EBEFF5] uppercase tracking-wider">
              Knowledge Base
            </h3>
            <span className="px-1.5 py-0.2 rounded text-[10px] font-mono font-medium bg-[#E5F5F1] dark:bg-[#1A2D2A] text-[#263142] dark:text-[#A9DED5] border border-[#C7E9E2] dark:border-[#244742]">
              {INDEXED_POLICY_DOCUMENTS.length} Docs
            </span>
          </div>

          {onToggleCollapse && (
            <button
              type="button"
              onClick={onToggleCollapse}
              title="Collapse Panel"
              aria-label="Collapse Knowledge Base Panel"
              className="p-1 rounded-lg text-[#9299A3] hover:text-[#263142] dark:hover:text-[#EBEFF5] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] transition-colors cursor-pointer"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Document Search / Filter */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-[#9299A3] dark:text-[#6E7887] absolute left-2.5 top-2.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter indexed policies..."
            className="w-full pl-8 pr-3 py-1.5 rounded-xl bg-[#FFFFFF] dark:bg-[#21252D] border border-[#E9E5DF] dark:border-[#2F3540] text-xs text-[#263142] dark:text-[#EBEFF5] placeholder-[#9299A3] dark:placeholder-[#6E7887] outline-none focus:border-[#A9DED5] focus:ring-1 focus:ring-[#A9DED5]/40 transition-colors"
          />
        </div>
      </div>

      {/* Document List */}
      <div className="flex-1 overflow-y-auto p-2.5 space-y-2 scrollbar-thin">
        {filteredDocs.length === 0 ? (
          <div className="text-center py-8 text-xs text-[#9299A3] dark:text-[#6E7887]">
            No policy documents match &ldquo;{searchQuery}&rdquo;
          </div>
        ) : (
          filteredDocs.map((doc, idx) => {
            const isSelected = selectedDocumentId === doc.id;
            const pastelColors = [
              'bg-[#E5F5F1] text-[#368F88] border-[#C7E9E2]',
              'bg-[#DCCEEF] text-[#5A4384] border-[#CBB8E3]',
              'bg-[#F7C9B8] text-[#9A4927] border-[#F1B5A0]',
              'bg-[#CFE5D6] text-[#2F855A] border-[#B7D9C2]',
            ];
            const pastel = pastelColors[idx % pastelColors.length];

            return (
              <button
                key={doc.id}
                type="button"
                onClick={() => onSelectDocument(doc)}
                className={`w-full text-left p-3 rounded-xl border transition-colors cursor-pointer group flex flex-col justify-between gap-1.5 shadow-[0_1px_2px_rgba(38,49,66,0.02)] ${
                  isSelected
                    ? 'bg-[#E5F5F1] dark:bg-[#1A2D2A] border-[#A9DED5] dark:border-[#368F88] ring-1 ring-[#368F88]/30'
                    : 'bg-[#FFFEFC] dark:bg-[#21252D] border-[#E9E5DF] dark:border-[#2F3540] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] hover:border-[#A9DED5]/60 dark:hover:border-[#368F88]/60'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between gap-1 mb-1">
                    <span className={`inline-flex items-center gap-1 font-mono text-[9px] uppercase font-bold px-1.5 py-0.2 rounded border ${pastel}`}>
                      <FileText className="w-3 h-3" />
                      <span>{doc.fileType}</span>
                    </span>
                    <span className="text-[10px] font-mono text-[#697582] dark:text-[#9CA6B5] bg-[#F8F6F2] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540] px-1.5 py-0.2 rounded">
                      {doc.chunkCount} chunks
                    </span>
                  </div>

                  <div className="text-xs font-semibold text-[#263142] dark:text-[#EBEFF5] group-hover:text-[#368F88] dark:group-hover:text-[#A9DED5] transition-colors line-clamp-1">
                    {doc.title}
                  </div>

                  <div className="text-[10px] text-[#9299A3] dark:text-[#6E7887] font-mono mt-0.5 truncate">
                    {doc.filename}
                  </div>
                </div>

                <div className="text-[10px] text-[#697582] dark:text-[#9CA6B5] line-clamp-2 leading-relaxed pt-1 border-t border-[#E9E5DF]/60 dark:border-[#2F3540]/60 font-normal">
                  {doc.summary}
                </div>
              </button>
            );
          })
        )}
      </div>

      {/* Footer Info */}
      <div className="p-3 border-t border-[#E9E5DF] dark:border-[#2F3540] bg-[#FCFAF7] dark:bg-[#1B1E24] text-[10px] text-[#697582] dark:text-[#9CA6B5] flex items-center justify-between">
        <span className="flex items-center gap-1">
          <Database className="w-3 h-3 text-[#368F88] dark:text-[#A9DED5]" />
          <span>ChromaDB Vector Store</span>
        </span>
        <span className="font-mono text-[#9299A3] dark:text-[#6E7887]">13 Chunks</span>
      </div>
    </aside>
  );
}
