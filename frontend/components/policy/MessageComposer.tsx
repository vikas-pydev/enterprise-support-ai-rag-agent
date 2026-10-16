'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, CornerDownLeft, Trash2 } from 'lucide-react';

interface MessageComposerProps {
  onSendMessage: (message: string) => void;
  isLoading: boolean;
  loadingStage?: string;
  placeholder?: string;
}

export function MessageComposer({
  onSendMessage,
  isLoading,
  loadingStage,
  placeholder = 'Ask a question about internal company policies...',
}: MessageComposerProps) {
  const [input, setInput] = useState<string>('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea height up to a max
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
    }
  }, [input]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    onSendMessage(trimmed);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const isOverLimit = input.length > 1000;
  const canSubmit = input.trim().length > 0 && !isLoading && !isOverLimit;

  return (
    <div className="w-full relative">
      {/* Loading Status Pill */}
      {isLoading && (
        <div className="mb-2 flex items-center justify-center gap-2 text-xs text-[#368F88] dark:text-[#A9DED5] font-mono animate-pulse">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          <span>{loadingStage || 'Searching policy knowledge base & generating grounded answer...'}</span>
        </div>
      )}

      {/* Composer Input Box */}
      <form
        onSubmit={handleSubmit}
        className={`relative rounded-2xl border transition-colors ${
          isLoading
            ? 'bg-[#F8F6F2] dark:bg-[#1B1E24] border-[#E9E5DF] dark:border-[#2F3540] opacity-80'
            : isOverLimit
            ? 'bg-[#FFFFFF] dark:bg-[#1B1E24] border-rose-400 ring-1 ring-rose-400/30'
            : 'bg-[#FFFFFF] dark:bg-[#1B1E24] border-[#E9E5DF] dark:border-[#2F3540] hover:border-[#A9DED5]/70 dark:hover:border-[#368F88]/70 focus-within:border-[#A9DED5] dark:focus-within:border-[#368F88] focus-within:ring-2 focus-within:ring-[#A9DED5]/30 dark:focus-within:ring-[#368F88]/20 shadow-[0_1px_3px_rgba(38,49,66,0.03)]'
        }`}
      >
        <textarea
          ref={textareaRef}
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          aria-label="Policy Question Input"
          placeholder={isLoading ? 'Awaiting assistant response...' : placeholder}
          className="w-full bg-transparent px-4 pt-3 pb-10 text-xs sm:text-sm text-[#263142] dark:text-[#EBEFF5] placeholder-[#9299A3] dark:placeholder-[#6E7887] resize-none outline-none focus:outline-none min-h-[52px] max-h-[180px] leading-relaxed"
        />

        {/* Bottom Toolbar inside composer */}
        <div className="absolute bottom-2.5 left-4 right-3 flex items-center justify-between pointer-events-none">
          {/* Character Count & Shortcut Hint */}
          <div className="flex items-center gap-2 text-[11px] font-mono text-[#9299A3] dark:text-[#6E7887] pointer-events-auto select-none">
            <span className="hidden sm:inline-flex items-center gap-1">
              <CornerDownLeft className="w-3 h-3 text-[#9299A3] dark:text-[#6E7887]" />
              <span>Enter to send, Shift+Enter for newline</span>
            </span>
            {input.length > 0 && (
              <span className={`text-[10px] font-medium ${isOverLimit ? 'text-rose-600 font-bold' : 'text-[#697582] dark:text-[#9CA6B5]'}`}>
                {input.length}/1000
              </span>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-1.5 pointer-events-auto">
            {input.length > 0 && !isLoading && (
              <button
                type="button"
                onClick={() => setInput('')}
                className="p-1.5 rounded-lg text-[#9299A3] hover:text-[#263142] dark:hover:text-[#EBEFF5] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] transition-colors cursor-pointer"
                title="Clear input"
                aria-label="Clear input"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}

            <button
              type="submit"
              disabled={!canSubmit}
              aria-label="Send Policy Question"
              className={`inline-flex items-center justify-center p-2 rounded-xl font-medium transition-colors ${
                canSubmit
                  ? 'bg-[#368F88] hover:bg-[#2B7771] text-white shadow-[0_1px_2px_rgba(38,49,66,0.05)] cursor-pointer'
                  : 'bg-[#F8F6F2] dark:bg-[#21252D] text-[#9299A3] dark:text-[#6E7887] cursor-not-allowed opacity-60'
              }`}
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin text-white" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
