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

  // 2. Assistant Message
  const hasSteps = Boolean(message.steps && message.steps.length > 0);
  const hasCitations = Boolean(message.citations && message.citations.length > 0);
  const isApprovalPending = message.status === 'pending_approval' || Boolean(message.approvalId && message.approvalStatus === 'pending');
  const isApprovalHandled = Boolean(message.approvalId);

  return (
    <div className="flex items-start gap-3.5 max-w-4xl mr-auto w-full">
      {/* Assistant Avatar */}
      <div className="w-8 h-8 rounded-xl bg-[#DCCEEF] dark:bg-[#39344D] border border-[#CBB8E3] dark:border-[#4A4463] flex items-center justify-center text-[#5A4384] dark:text-[#DCCEEF] flex-shrink-0 shadow-[0_1px_2px_rgba(38,49,66,0.03)]">
        <Bot className="w-4 h-4" />
      </div>

      <div className="flex-1 min-w-0">
        {/* Assistant Header */}
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-semibold text-[#263142] dark:text-[#EBEFF5]">Enterprise AI Agent</span>
            <span className="px-2 py-0.2 rounded-full text-[10px] font-mono font-medium bg-[#F8F6F2] dark:bg-[#1B1E24] text-[#697582] dark:text-[#9CA6B5] border border-[#E9E5DF] dark:border-[#2F3540]">
              LangGraph Multi-Agent
            </span>
            {message.sessionId && (
              <span className="text-[10px] font-mono text-[#9299A3] dark:text-[#6E7887] hidden sm:inline">
                [{message.sessionId.substring(0, 14)}...]
              </span>
            )}
            <span className="text-[11px] text-[#9299A3] dark:text-[#6E7887]">&bull; {formatTimestamp(message.timestamp)}</span>
          </div>

          {/* Copy Button */}
          <button
            type="button"
            onClick={handleCopyAnswer}
            aria-label="Copy Agent Answer"
            title={isCopied ? 'Copied!' : 'Copy Agent Answer'}
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
          {/* Error Banner */}
          {message.error && (
            <div className="mb-4 p-3.5 rounded-xl bg-[#FDE8E8] dark:bg-[#3D2525] border border-[#FBD5D5] dark:border-[#522828] text-[#9B1C1C] dark:text-[#F87171] flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-[#C53030] dark:text-[#F87171] flex-shrink-0 mt-0.5" />
              <div className="text-xs">
                <div className="font-semibold text-[#9B1C1C] dark:text-[#F87171] mb-0.5">Execution Notice</div>
                <div className="text-[#9B1C1C]/90 dark:text-[#F87171]/90 font-normal">{message.error}</div>
              </div>
            </div>
          )}

          {/* Synthesized Answer Content */}
          <div className="text-xs sm:text-sm text-[#263142] dark:text-[#EBEFF5] leading-relaxed whitespace-pre-wrap break-words font-normal">
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
            <div className="mt-4 pt-4 border-t border-[#E9E5DF] dark:border-[#2F3540]">
              <div className="flex items-center gap-2 mb-3">
                <BookOpen className="w-4 h-4 text-[#368F88] dark:text-[#A9DED5]" />
                <h4 className="text-xs font-semibold text-[#263142] dark:text-[#EBEFF5] tracking-wide">
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
