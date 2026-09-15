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
        <div className="mb-2 flex items-center justify-center gap-2 text-xs text-cyan-600 dark:text-cyan-400 font-mono animate-pulse">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          <span>{loadingStage || 'Searching policy knowledge base & generating grounded answer...'}</span>
        </div>
      )}

      {/* Composer Input Box */}
      <form
        onSubmit={handleSubmit}
        className={`relative rounded-3xl border transition-all duration-200 backdrop-blur-md ${
          isLoading
            ? 'bg-slate-100/60 dark:bg-slate-900/40 border-slate-200 dark:border-slate-800 opacity-80'
            : isOverLimit
            ? 'bg-white dark:bg-slate-900/80 border-rose-500/80 ring-1 ring-rose-500/30'
            : 'bg-white dark:bg-slate-900/80 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700/80 focus-within:border-cyan-500/80 focus-within:ring-2 focus-within:ring-cyan-500/30'
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
          className="w-full bg-transparent px-4 pt-3.5 pb-10 text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 resize-none outline-none focus:outline-none min-h-[56px] max-h-[180px]"
        />

        {/* Bottom Toolbar inside composer */}
        <div className="absolute bottom-2.5 left-4 right-3 flex items-center justify-between pointer-events-none">
          {/* Character Count & Shortcut Hint */}
          <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400 dark:text-slate-500 pointer-events-auto select-none">
            <span className="hidden sm:inline-flex items-center gap-1">
              <CornerDownLeft className="w-3 h-3 text-slate-400" />
              <span>Enter to send, Shift+Enter for newline</span>
            </span>
            {input.length > 0 && (
              <span className={`text-[10px] font-semibold ${isOverLimit ? 'text-rose-500 font-bold' : 'text-slate-500'}`}>
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
                className="p-1.5 rounded-xl text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
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
              className={`inline-flex items-center justify-center p-2 rounded-2xl font-medium transition-all ${
                canSubmit
                  ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-md shadow-cyan-500/20 hover:from-cyan-400 hover:to-blue-500 cursor-pointer active:scale-95'
                  : 'bg-slate-200 dark:bg-slate-800/80 text-slate-400 cursor-not-allowed opacity-60'
              }`}
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
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

