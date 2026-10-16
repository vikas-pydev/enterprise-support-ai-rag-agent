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
        <div className="flex items-center gap-2 text-xs text-[#368F88] dark:text-[#A9DED5] animate-pulse px-2 font-mono">
          <Loader2 className="w-3.5 h-3.5 animate-spin text-[#368F88] dark:text-[#A9DED5]" />
          <span className="font-medium">{loadingStage}</span>
        </div>
      )}

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="relative flex items-end gap-2">
        <div className="relative flex-1 rounded-2xl border border-[#E9E5DF] dark:border-[#2F3540] bg-[#FFFFFF] dark:bg-[#1B1E24] focus-within:border-[#A9DED5] dark:focus-within:border-[#368F88] focus-within:ring-2 focus-within:ring-[#A9DED5]/30 dark:focus-within:ring-[#368F88]/20 transition-colors shadow-[0_1px_2px_rgba(38,49,66,0.02)]">
          <textarea
            ref={textareaRef}
            rows={1}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            placeholder={placeholder}
            className="w-full px-4 py-3 pr-10 text-xs sm:text-sm text-[#263142] dark:text-[#EBEFF5] placeholder-[#9299A3] dark:placeholder-[#6E7887] bg-transparent resize-none outline-none leading-relaxed disabled:opacity-50 min-h-[50px] max-h-[160px]"
          />

          {/* Quick Clear Button */}
          {inputText && !isLoading && (
            <button
              type="button"
              onClick={() => {
                setInputText('');
                if (textareaRef.current) textareaRef.current.style.height = 'auto';
              }}
              className="absolute right-3 top-3 text-[#9299A3] hover:text-[#263142] dark:text-[#6E7887] dark:hover:text-[#EBEFF5] p-1 rounded transition-colors cursor-pointer"
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
          className="h-11 px-4 sm:px-5 rounded-xl bg-[#368F88] hover:bg-[#2B7771] disabled:bg-[#F8F6F2] dark:disabled:bg-[#21252D] disabled:text-[#9299A3] dark:disabled:text-[#6E7887] disabled:cursor-not-allowed text-white text-xs font-semibold shadow-[0_1px_2px_rgba(38,49,66,0.05)] transition-colors flex items-center justify-center gap-1.5 flex-shrink-0 cursor-pointer"
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
      <div className="flex items-center justify-between px-2 text-[11px] text-[#697582] dark:text-[#9CA6B5] select-none">
        <div className="flex items-center gap-1.5">
          <Bot className="w-3 h-3 text-[#368F88] dark:text-[#A9DED5]" />
          <span>Multi-turn session active &bull; Supervisor routes across SQL &amp; RAG tools</span>
        </div>
        <div className="hidden sm:inline-block font-mono text-[10px] text-[#9299A3] dark:text-[#6E7887]">
          Enter to send, Shift+Enter for newline
        </div>
      </div>
    </div>
  );
}
