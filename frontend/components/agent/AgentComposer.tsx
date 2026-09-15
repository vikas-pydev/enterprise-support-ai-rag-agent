'use client';

import React, { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { Send, Loader2, X, Bot } from 'lucide-react';

interface AgentComposerProps {
  onSendMessage: (queryText: string) => void;
  isLoading: boolean;
  loadingStage?: string;
  placeholder?: string;
}

export function AgentComposer({
  onSendMessage,
  isLoading,
  loadingStage,
  placeholder = 'Ask the enterprise agent (e.g., "How much has E1001 spent on travel and who is their manager?")...',
}: AgentComposerProps) {
  const [inputText, setInputText] = useState<string>('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea based on input content
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const scrollHeight = textareaRef.current.scrollHeight;
      const maxHeight = 160;
      textareaRef.current.style.height = `${Math.min(scrollHeight, maxHeight)}px`;
    }
  }, [inputText]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = inputText.trim();
    if (!trimmed || isLoading) return;

    onSendMessage(trimmed);
    setInputText('');

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="w-full space-y-2">
      {/* Loading Stage Indicator */}
      {isLoading && loadingStage && (
        <div className="flex items-center gap-2 text-xs text-indigo-600 dark:text-indigo-400 animate-pulse px-2">
          <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-600 dark:text-indigo-400" />
          <span className="font-medium">{loadingStage}</span>
        </div>
      )}

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="relative flex items-end gap-2">
        <div className="relative flex-1 rounded-2xl border border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900/90 focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-500/20 dark:focus-within:ring-indigo-500/40 transition-all shadow-xs">
          <textarea
            ref={textareaRef}
            rows={1}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            placeholder={placeholder}
            className="w-full px-4 py-3.5 pr-10 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 bg-transparent resize-none outline-none leading-relaxed disabled:opacity-50"
          />

          {/* Quick Clear Button */}
          {inputText && !isLoading && (
            <button
              type="button"
              onClick={() => {
                setInputText('');
                if (textareaRef.current) textareaRef.current.style.height = 'auto';
              }}
              className="absolute right-3 top-3.5 text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 p-1 rounded transition-colors"
              title="Clear input"
              aria-label="Clear input"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={!inputText.trim() || isLoading}
          className="h-12 px-5 rounded-2xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-200 dark:disabled:bg-slate-800 disabled:text-slate-400 dark:disabled:text-slate-600 disabled:cursor-not-allowed text-white text-xs font-semibold shadow-lg shadow-indigo-600/25 transition-all flex items-center justify-center gap-2 flex-shrink-0 cursor-pointer"
          title="Send query to agent"
          aria-label="Send query to agent"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin text-white" />
              <span className="hidden sm:inline">Executing...</span>
            </>
          ) : (
            <>
              <Send className="w-4 h-4 text-white" />
              <span className="hidden sm:inline">Send</span>
            </>
          )}
        </button>
      </form>

      {/* Helper Footer */}
      <div className="flex items-center justify-between px-2 text-[11px] text-slate-500">
        <div className="flex items-center gap-1.5">
          <Bot className="w-3 h-3 text-indigo-500 dark:text-indigo-400" />
          <span>Multi-turn session active &bull; Supervisor routes across SQL &amp; RAG tools</span>
        </div>
        <div className="hidden sm:inline-block">
          Press <kbd className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-300 dark:border-slate-700 font-mono text-[10px]">Enter</kbd> to send, <kbd className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-300 dark:border-slate-700 font-mono text-[10px]">Shift+Enter</kbd> for newline
        </div>
      </div>
    </div>
  );
}

