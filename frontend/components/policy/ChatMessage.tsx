'use client';

import React, { useState } from 'react';
import { PolicyChatMessage } from '@/types/chat';
import { CitationList } from './CitationList';
import { RetrievalDetails } from './RetrievalDetails';
import { ShieldAlert, User, Bot, Copy, Check, AlertTriangle } from 'lucide-react';

interface ChatMessageProps {
  message: PolicyChatMessage;
}

export function ChatMessage({ message }: ChatMessageProps) {
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
          <div className="flex items-center gap-1.5 text-[11px] text-slate-500 dark:text-slate-400 mb-1 font-medium">
            <span>You</span>
            <span>&bull;</span>
            <span>{formatTimestamp(message.timestamp)}</span>
          </div>

          <div className="p-4 rounded-3xl rounded-tr-sm bg-gradient-to-br from-cyan-600 to-blue-600 text-white shadow-lg shadow-cyan-600/15 text-sm leading-relaxed whitespace-pre-wrap break-words">
            {message.content}
          </div>
        </div>

        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white flex-shrink-0 shadow-md">
          <User className="w-4 h-4" />
        </div>
      </div>
    );
  }

  // Assistant Message Rendering
  return (
    <div className="flex items-start gap-3.5 max-w-4xl mr-auto w-full">
      {/* Assistant Avatar */}
      <div className="w-8 h-8 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700/80 flex items-center justify-center text-cyan-600 dark:text-cyan-400 flex-shrink-0 shadow-md">
        <Bot className="w-4 h-4" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-900 dark:text-white">Policy Assistant</span>
            <span className="px-2 py-0.2 rounded-full text-[10px] font-semibold bg-cyan-100 dark:bg-cyan-950/80 text-cyan-700 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-500/20">
              Grounded RAG
            </span>
            <span className="text-[11px] text-slate-500 dark:text-slate-400">&bull; {formatTimestamp(message.timestamp)}</span>
          </div>

          {/* Copy Answer Action */}
          <button
            type="button"
            onClick={handleCopyAnswer}
            aria-label="Copy Answer"
            title={isCopied ? 'Copied!' : 'Copy Answer'}
            className="flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-medium text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
          >
            {isCopied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                <span className="text-emerald-600 dark:text-emerald-400 font-semibold">Copied</span>
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
        <div className="rounded-3xl rounded-tl-sm border border-slate-200 dark:border-slate-800/90 bg-white/90 dark:bg-slate-900/60 p-5 shadow-xl backdrop-blur-sm transition-colors">
          {/* Refusal Alert Banner */}
          {message.isRefusal && (
            <div className="mb-4 p-3.5 rounded-2xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-500/30 text-amber-800 dark:text-amber-200 flex items-start gap-3">
              <ShieldAlert className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
              <div className="text-xs">
                <div className="font-bold text-amber-900 dark:text-amber-300 mb-0.5">
                  Knowledge Base Refusal
                </div>
                <div className="text-slate-700 dark:text-slate-300 leading-relaxed">
                  Insufficient supporting evidence was retrieved from the internal knowledge base. The assistant strictly avoids hallucinating answers when documented policy facts are not found.
                </div>
              </div>
            </div>
          )}

          {/* Error Banner */}
          {message.error && (
            <div className="mb-4 p-3.5 rounded-2xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-500/30 text-rose-800 dark:text-rose-200 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-rose-600 dark:text-rose-400 flex-shrink-0 mt-0.5" />
              <div className="text-xs">
                <div className="font-bold text-rose-900 dark:text-rose-300 mb-0.5">Service Error</div>
                <div className="text-rose-800 dark:text-rose-200/90">{message.error}</div>
              </div>
            </div>
          )}

          {/* Answer Text with Markdown / Line Break Rendering */}
          <div className="text-sm text-slate-800 dark:text-slate-200 leading-relaxed whitespace-pre-wrap break-words">
            {message.content}
          </div>

          {/* Source Citations */}
          {message.sources && message.sources.length > 0 && (
            <CitationList sources={message.sources} />
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

