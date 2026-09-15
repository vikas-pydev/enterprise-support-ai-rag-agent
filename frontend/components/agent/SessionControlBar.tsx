'use client';

import React, { useState } from 'react';
import { KeyRound, Plus, Trash2, RotateCcw, Copy, Check } from 'lucide-react';

interface SessionControlBarProps {
  sessionId: string;
  onNewSession: () => void;
  onClearSession: () => void;
  onDeleteSession: () => void;
  isLoading: boolean;
  messageCount: number;
}

export function SessionControlBar({
  sessionId,
  onNewSession,
  onClearSession,
  onDeleteSession,
  isLoading,
  messageCount,
}: SessionControlBarProps) {
  const [copied, setCopied] = useState<boolean>(false);
  const [confirmClear, setConfirmClear] = useState<boolean>(false);
  const [confirmDelete, setConfirmDelete] = useState<boolean>(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(sessionId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  const handleClear = () => {
    if (confirmClear) {
      onClearSession();
      setConfirmClear(false);
    } else {
      setConfirmClear(true);
      setTimeout(() => setConfirmClear(false), 4000);
    }
  };

  const handleDelete = () => {
    if (confirmDelete) {
      onDeleteSession();
      setConfirmDelete(false);
    } else {
      setConfirmDelete(true);
      setTimeout(() => setConfirmDelete(false), 4000);
    }
  };

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-3 border-b border-slate-200 dark:border-slate-800/90 bg-slate-50/80 dark:bg-slate-900/60 backdrop-blur-md">
      {/* Session ID Chip with Copy */}
      <div className="flex items-center gap-2 min-w-0">
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800 text-xs shadow-sm">
          <KeyRound className="w-3.5 h-3.5 text-indigo-500 dark:text-indigo-400 flex-shrink-0" />
          <span className="text-slate-500 dark:text-slate-400 text-[11px] font-medium hidden sm:inline">Session:</span>
          <span className="font-mono text-indigo-600 dark:text-indigo-300 text-[11px] truncate max-w-[140px] sm:max-w-[200px]" title={sessionId}>
            {sessionId}
          </span>
          <button
            type="button"
            onClick={handleCopy}
            title={copied ? 'Copied to clipboard' : 'Copy Session ID'}
            aria-label="Copy Session ID"
            className="p-1 hover:text-slate-900 dark:hover:text-white text-slate-400 dark:text-slate-500 rounded transition-colors"
          >
            {copied ? (
              <Check className="w-3 h-3 text-emerald-500 dark:text-emerald-400" />
            ) : (
              <Copy className="w-3 h-3" />
            )}
          </button>
        </div>

        {messageCount > 0 && (
          <span className="hidden md:inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-400 border border-slate-300 dark:border-slate-700">
            {messageCount} {messageCount === 1 ? 'turn' : 'turns'}
          </span>
        )}
      </div>

      {/* Action Controls */}
      <div className="flex items-center gap-2">
        {/* New Session */}
        <button
          type="button"
          onClick={onNewSession}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium text-indigo-700 dark:text-slate-300 hover:text-indigo-900 dark:hover:text-white bg-indigo-50 dark:bg-indigo-950/60 hover:bg-indigo-100 dark:hover:bg-indigo-900/80 border border-indigo-200 dark:border-indigo-500/30 transition-all disabled:opacity-50 cursor-pointer"
          title="Start a fresh conversation session with new session ID"
        >
          <Plus className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
          <span>New Session</span>
        </button>

        {/* Clear Chat */}
        {messageCount > 0 && (
          <button
            type="button"
            onClick={handleClear}
            disabled={isLoading}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium transition-all disabled:opacity-50 cursor-pointer ${
              confirmClear
                ? 'bg-amber-100 dark:bg-amber-950/90 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-500/50'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
            }`}
            title="Clear all messages in this session history on backend & frontend"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>{confirmClear ? 'Confirm Clear?' : 'Clear History'}</span>
          </button>
        )}

        {/* Delete Session */}
        <button
          type="button"
          onClick={handleDelete}
          disabled={isLoading}
          className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium transition-all disabled:opacity-50 cursor-pointer ${
            confirmDelete
              ? 'bg-rose-100 dark:bg-rose-950/90 text-rose-800 dark:text-rose-300 border border-rose-300 dark:border-rose-500/50'
              : 'text-slate-500 hover:text-rose-600 dark:hover:text-rose-400 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-rose-200 dark:hover:border-rose-900/50'
          }`}
          title="Delete session thread and checkpoints from PostgreSQL / memory"
        >
          <Trash2 className="w-3.5 h-3.5" />
          <span>{confirmDelete ? 'Confirm Delete?' : 'Delete'}</span>
        </button>
      </div>
    </div>
  );
}

