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
    <div className="flex flex-wrap items-center justify-between gap-3 px-4 sm:px-6 py-2.5 border-b border-[#E9E5DF] dark:border-[#2F3540] bg-[#FCFAF7] dark:bg-[#1B1E24] backdrop-blur-md select-none">
      {/* Session ID Chip with Copy */}
      <div className="flex items-center gap-2 min-w-0">
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#FFFFFF] dark:bg-[#21252D] border border-[#E9E5DF] dark:border-[#2F3540] text-xs shadow-[0_1px_2px_rgba(38,49,66,0.02)]">
          <KeyRound className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5] flex-shrink-0" />
          <span className="text-[#697582] dark:text-[#9CA6B5] text-[11px] font-normal hidden sm:inline">Session:</span>
          <span className="font-mono text-[#263142] dark:text-[#EBEFF5] text-[11px] truncate max-w-[140px] sm:max-w-[200px]" title={sessionId}>
            {sessionId}
          </span>
          <button
            type="button"
            onClick={handleCopy}
            title={copied ? 'Copied to clipboard' : 'Copy Session ID'}
            aria-label="Copy Session ID"
            className="p-1 hover:text-[#263142] dark:hover:text-[#EBEFF5] text-[#9299A3] dark:text-[#6E7887] rounded transition-colors cursor-pointer"
          >
            {copied ? (
              <Check className="w-3 h-3 text-[#2F855A] dark:text-[#34D399]" />
            ) : (
              <Copy className="w-3 h-3" />
            )}
          </button>
        </div>

        {messageCount > 0 && (
          <span className="hidden md:inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-mono font-normal bg-[#F8F6F2] dark:bg-[#1B1E24] text-[#697582] dark:text-[#9CA6B5] border border-[#E9E5DF] dark:border-[#2F3540]">
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
          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium text-[#263142] dark:text-[#EBEFF5] hover:text-[#368F88] dark:hover:text-[#A9DED5] bg-[#FFFFFF] dark:bg-[#21252D] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] border border-[#E9E5DF] dark:border-[#2F3540] transition-colors disabled:opacity-50 cursor-pointer shadow-[0_1px_2px_rgba(38,49,66,0.02)]"
          title="Start a fresh conversation session with new session ID"
        >
          <Plus className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5]" />
          <span>New Session</span>
        </button>

        {/* Clear Chat */}
        {messageCount > 0 && (
          <button
            type="button"
            onClick={handleClear}
            disabled={isLoading}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium transition-colors disabled:opacity-50 cursor-pointer ${
              confirmClear
                ? 'bg-[#FEF3C7] dark:bg-[#393425] text-[#78350F] dark:text-[#FBBF24] border border-[#FDE68A] dark:border-[#4A462B]'
                : 'text-[#697582] dark:text-[#9CA6B5] hover:text-[#263142] dark:hover:text-[#EBEFF5] bg-[#FFFFFF] dark:bg-[#21252D] border border-[#E9E5DF] dark:border-[#2F3540] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37]'
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
          className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium transition-colors disabled:opacity-50 cursor-pointer ${
            confirmDelete
              ? 'bg-[#FDE8E8] dark:bg-[#3D2525] text-[#9B1C1C] dark:text-[#F87171] border border-[#FBD5D5] dark:border-[#522828]'
              : 'text-[#697582] dark:text-[#9CA6B5] hover:text-[#9B1C1C] dark:hover:text-[#F87171] bg-[#FFFFFF] dark:bg-[#21252D] border border-[#E9E5DF] dark:border-[#2F3540] hover:border-[#FBD5D5]'
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
