'use client';

import React, { useState } from 'react';
import { PolicyChatMessage } from '@/types/chat';
import { CitationSource } from '@/types/api';
import { CitationList } from './CitationList';
import { RetrievalDetails } from './RetrievalDetails';
import { ShieldAlert, User, Bot, Copy, Check, AlertTriangle } from 'lucide-react';

interface ChatMessageProps {
  message: PolicyChatMessage;
  onSelectCitation?: (source: CitationSource) => void;
  selectedCitationUid?: string | null;
}

export function ChatMessage({
  message,
  onSelectCitation,
  selectedCitationUid,
}: ChatMessageProps) {
  const [isCopied, setIsCopied] = useState<boolean>(false);
  const isUser = message.role === 'user';

  const handleCopyAnswer = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch {
      setIsCopied(false);
    }
  };

  const formatTimestamp = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  // User Message Rendering
  if (isUser) {
    return (
      <div className="flex items-start justify-end gap-3 max-w-4xl ml-auto">
        <div className="flex flex-col items-end max-w-2xl">
          <div className="flex items-center gap-1.5 text-[11px] text-[#697582] dark:text-[#9CA6B5] mb-1 font-normal">
            <span>You</span>
            <span>&bull;</span>
            <span>{formatTimestamp(message.timestamp)}</span>
          </div>

          <div className="p-4 rounded-2xl rounded-tr-sm bg-[#E5F5F1] text-[#263142] dark:bg-[#1A2D2A] dark:text-[#EBEFF5] shadow-[0_1px_2px_rgba(38,49,66,0.03)] text-xs sm:text-sm leading-relaxed whitespace-pre-wrap break-words border border-[#C7E9E2] dark:border-[#244742]">
            {message.content}
          </div>
        </div>

        <div className="w-8 h-8 rounded-xl bg-[#E5F5F1] dark:bg-[#1A2D2A] text-[#368F88] dark:text-[#A9DED5] border border-[#C7E9E2] dark:border-[#244742] flex items-center justify-center flex-shrink-0 shadow-[0_1px_2px_rgba(38,49,66,0.03)]">
          <User className="w-4 h-4" />
        </div>
      </div>
    );
  }

  // Assistant Message Rendering
  return (
    <div className="flex items-start gap-3.5 max-w-4xl mr-auto w-full">
      {/* Assistant Avatar */}
      <div className="w-8 h-8 rounded-xl bg-[#E5F5F1] dark:bg-[#1A2D2A] border border-[#C7E9E2] dark:border-[#244742] flex items-center justify-center text-[#368F88] dark:text-[#A9DED5] flex-shrink-0 shadow-[0_1px_2px_rgba(38,49,66,0.03)]">
        <Bot className="w-4 h-4" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-[#263142] dark:text-[#EBEFF5]">Policy Assistant</span>
            <span className="px-2 py-0.2 rounded-full text-[10px] font-mono font-medium bg-[#E5F5F1] dark:bg-[#1A2D2A] text-[#263142] dark:text-[#A9DED5] border border-[#C7E9E2] dark:border-[#244742]">
              Grounded RAG
            </span>
            <span className="text-[11px] text-[#9299A3] dark:text-[#6E7887]">&bull; {formatTimestamp(message.timestamp)}</span>
          </div>

          {/* Copy Answer Action */}
          <button
            type="button"
            onClick={handleCopyAnswer}
            aria-label="Copy Answer"
            title={isCopied ? 'Copied!' : 'Copy Answer'}
            className="flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-medium text-[#697582] dark:text-[#9CA6B5] hover:text-[#263142] dark:hover:text-[#EBEFF5] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] transition-colors cursor-pointer"
          >
            {isCopied ? (
              <>
                <Check className="w-3.5 h-3.5 text-[#2F855A] dark:text-[#34D399]" />
                <span className="text-[#2F855A] dark:text-[#34D399] font-medium">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>

        {/* Card Container */}
        <div className="rounded-2xl rounded-tl-sm border border-[#E9E5DF] dark:border-[#2F3540] bg-[#FFFEFC] dark:bg-[#21252D] p-5 shadow-[0_1px_3px_rgba(38,49,66,0.03)] transition-colors">
          {/* Refusal Alert Banner */}
          {message.isRefusal && (
            <div className="mb-4 p-3.5 rounded-xl bg-[#FEF3C7] dark:bg-[#393425] border border-[#FDE68A] dark:border-[#4A462B] text-[#78350F] dark:text-[#FBBF24] flex items-start gap-3">
              <ShieldAlert className="w-5 h-5 text-[#B45309] dark:text-[#FBBF24] flex-shrink-0 mt-0.5" />
              <div className="text-xs">
                <div className="font-semibold text-[#78350F] dark:text-[#FBBF24] mb-0.5">
                  Knowledge Base Refusal
                </div>
                <div className="text-[#78350F]/90 dark:text-[#FBBF24]/90 leading-relaxed font-normal">
                  Insufficient supporting evidence was retrieved from the internal knowledge base. The assistant strictly avoids hallucinating answers when documented policy facts are not found.
                </div>
              </div>
            </div>
          )}

          {/* Error Banner */}
          {message.error && (
            <div className="mb-4 p-3.5 rounded-xl bg-[#FDE8E8] dark:bg-[#3D2525] border border-[#FBD5D5] dark:border-[#522828] text-[#9B1C1C] dark:text-[#F87171] flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-[#C53030] dark:text-[#F87171] flex-shrink-0 mt-0.5" />
              <div className="text-xs">
                <div className="font-semibold text-[#9B1C1C] dark:text-[#F87171] mb-0.5">Service Error</div>
                <div className="text-[#9B1C1C]/90 dark:text-[#F87171]/90 font-normal">{message.error}</div>
              </div>
            </div>
          )}

          {/* Answer Text with Markdown / Line Break Rendering */}
          <div className="text-xs sm:text-sm text-[#263142] dark:text-[#EBEFF5] leading-relaxed whitespace-pre-wrap break-words font-normal">
            {message.content}
          </div>

          {/* Source Citations */}
          {message.sources && message.sources.length > 0 && (
            <CitationList
              sources={message.sources}
              onSelectCitation={onSelectCitation}
              selectedCitationUid={selectedCitationUid}
            />
          )}

          {/* Retrieval Details */}
          <RetrievalDetails
            sources={message.sources}
            isRefusal={message.isRefusal}
            durationMs={message.durationMs}
          />
        </div>
      </div>
    </div>
  );
}
