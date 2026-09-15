'use client';

import React, { useState } from 'react';
import { AgentChatMessage } from '@/types/agent';
import { CitationCard } from '@/components/policy/CitationCard';
import { WorkflowTimeline } from './WorkflowTimeline';
import { ToolActivity } from './ToolActivity';
import { ExecutionSummary } from './ExecutionSummary';
import { ApprovalCard } from './ApprovalCard';
import {
  User,
  Bot,
  Copy,
  Check,
  AlertTriangle,
  BookOpen,
} from 'lucide-react';

interface AgentMessageProps {
  message: AgentChatMessage;
  onApprovalDecision: (approvalId: string, decision: 'approve' | 'reject', notes?: string) => Promise<void>;
  isDecisionLoading?: boolean;
}

export function AgentMessage({
  message,
  onApprovalDecision,
  isDecisionLoading = false,
}: AgentMessageProps) {
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

  // 1. User Message
  if (isUser) {
    return (
      <div className="flex items-start justify-end gap-3 max-w-4xl ml-auto">
        <div className="flex flex-col items-end max-w-2xl">
          <div className="flex items-center gap-1.5 text-[11px] text-slate-500 dark:text-slate-400 mb-1 font-medium">
            <span>You</span>
            <span>&bull;</span>
            <span>{formatTimestamp(message.timestamp)}</span>
          </div>

          <div className="p-4 rounded-3xl rounded-tr-sm bg-gradient-to-br from-indigo-600 to-violet-600 text-white shadow-lg shadow-indigo-600/15 text-sm leading-relaxed whitespace-pre-wrap break-words">
            {message.content}
          </div>
        </div>

        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white flex-shrink-0 shadow-md">
          <User className="w-4 h-4" />
        </div>
      </div>
    );
  }

  // 2. Assistant Message
  const hasSteps = Boolean(message.steps && message.steps.length > 0);
  const hasCitations = Boolean(message.citations && message.citations.length > 0);
  const isApprovalPending = message.status === 'pending_approval' || Boolean(message.approvalId && message.approvalStatus === 'pending');
  const isApprovalHandled = Boolean(message.approvalId);

  return (
    <div className="flex items-start gap-3.5 max-w-4xl mr-auto w-full">
      {/* Assistant Avatar */}
      <div className="w-8 h-8 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700/80 flex items-center justify-center text-indigo-600 dark:text-indigo-400 flex-shrink-0 shadow-md">
        <Bot className="w-4 h-4" />
      </div>

      <div className="flex-1 min-w-0">
        {/* Assistant Header */}
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-bold text-slate-900 dark:text-white">Enterprise AI Agent</span>
            <span className="px-2 py-0.2 rounded-full text-[10px] font-semibold bg-indigo-100 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/20">
              LangGraph Multi-Agent
            </span>
            {message.sessionId && (
              <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500 hidden sm:inline">
                [{message.sessionId.substring(0, 14)}...]
              </span>
            )}
            <span className="text-[11px] text-slate-500 dark:text-slate-400">&bull; {formatTimestamp(message.timestamp)}</span>
          </div>

          {/* Copy Button */}
          <button
            type="button"
            onClick={handleCopyAnswer}
            aria-label="Copy Agent Answer"
            title={isCopied ? 'Copied!' : 'Copy Agent Answer'}
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
        <div className="rounded-3xl rounded-tl-sm border border-slate-200 dark:border-slate-800/90 bg-white/90 dark:bg-slate-900/70 p-5 shadow-xl backdrop-blur-sm transition-colors">
          {/* Error Banner */}
          {message.error && (
            <div className="mb-4 p-3.5 rounded-2xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-500/30 text-rose-800 dark:text-rose-200 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-rose-600 dark:text-rose-400 flex-shrink-0 mt-0.5" />
              <div className="text-xs">
                <div className="font-bold text-rose-900 dark:text-rose-300 mb-0.5">Execution Notice</div>
                <div className="text-rose-800 dark:text-rose-200/90">{message.error}</div>
              </div>
            </div>
          )}

          {/* Synthesized Answer Content */}
          <div className="text-sm text-slate-800 dark:text-slate-200 leading-relaxed whitespace-pre-wrap break-words">
            {message.content}
          </div>

          {/* Human-in-the-Loop Approval Card */}
          {isApprovalHandled && message.approvalId && (
            <ApprovalCard
              approvalId={message.approvalId}
              reason={message.approvalReason}
              targetWorker={message.targetWorker}
              approvalStatus={message.approvalStatus || 'pending'}
              approvalDecision={message.approvalDecision}
              approvalNotes={message.approvalNotes}
              onDecision={onApprovalDecision}
              isLoading={isDecisionLoading}
            />
          )}

          {/* Multi-Agent Execution Workflow Timeline */}
          {hasSteps && (
            <WorkflowTimeline
              steps={message.steps || []}
              status={message.status}
              isApprovalPending={isApprovalPending}
            />
          )}

          {/* Collapsible Tool Activity */}
          {hasSteps && <ToolActivity steps={message.steps || []} />}

          {/* RAG Policy Evidence / Citations if retrieved */}
          {hasCitations && (
            <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-2 mb-3">
                <BookOpen className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
                <h4 className="text-xs font-bold text-slate-900 dark:text-white tracking-wide">
                  Retrieved Policy Knowledge &amp; Citations ({message.citations?.length})
                </h4>
              </div>
              <div className="space-y-2.5">
                {message.citations?.map((source) => (
                  <CitationCard key={`${source.chunk_uid}-${source.rank}`} source={source} />
                ))}
              </div>
            </div>
          )}

          {/* Execution Summary Metadata */}
          <ExecutionSummary
            status={message.status}
            durationMs={message.durationMs}
            totalSteps={message.totalSteps}
            steps={message.steps}
            usedRag={message.usedRag}
            citationCount={message.citations?.length || 0}
            trace={message.trace}
          />
        </div>
      </div>
    </div>
  );
}

