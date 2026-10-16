'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { AgentChatMessage } from '@/types/agent';
import { apiClient } from '@/lib/api/client';
import { ApiClientError } from '@/lib/api/errors';
import { SessionControlBar } from './SessionControlBar';
import { AgentEmptyState } from './AgentEmptyState';
import { AgentMessage } from './AgentMessage';
import { AgentComposer } from './AgentComposer';
import { Bot, Sparkles, AlertCircle, CheckCircle2, GitBranch } from 'lucide-react';

const generateNewSessionId = (): string => {
  const timestamp = Date.now().toString(36);
  const randomStr = Math.random().toString(36).substring(2, 8);
  return `session-agent-${timestamp}-${randomStr}`;
};

interface AgentChatWorkspaceProps {
  initialPrompt?: string;
}

export function AgentChatWorkspace({ initialPrompt }: AgentChatWorkspaceProps) {
  const [sessionId, setSessionId] = useState<string>(generateNewSessionId);
  const [messages, setMessages] = useState<AgentChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [loadingStage, setLoadingStage] = useState<string>('');
  const [globalBanner, setGlobalBanner] = useState<{ type: 'error' | 'success' | 'info'; text: string } | null>(null);
  const [isDecisionLoading, setIsDecisionLoading] = useState<boolean>(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const initialPromptHandled = useRef<boolean>(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // =====================================================================
  // SESSION CONTROLS
  // =====================================================================

  const handleNewSession = useCallback(() => {
    const newId = generateNewSessionId();
    setSessionId(newId);
    setMessages([]);
    setGlobalBanner({
      type: 'info',
      text: `Started new agent conversation session (${newId}).`,
    });
    setTimeout(() => setGlobalBanner(null), 4000);
  }, []);

  const handleClearSession = useCallback(async () => {
    try {
      setIsLoading(true);
      await apiClient.clearSession(sessionId);
      setMessages([]);
      setGlobalBanner({
        type: 'success',
        text: `Session history for '${sessionId}' cleared successfully on backend and frontend.`,
      });
    } catch (err: unknown) {
      const msg = err instanceof ApiClientError ? err.userMessage : 'Failed to clear session on backend.';
      setGlobalBanner({ type: 'error', text: msg });
    } finally {
      setIsLoading(false);
      setTimeout(() => setGlobalBanner(null), 4000);
    }
  }, [sessionId]);

  const handleDeleteSession = useCallback(async () => {
    try {
      setIsLoading(true);
      await apiClient.deleteSession(sessionId);
      const newId = generateNewSessionId();
      setSessionId(newId);
      setMessages([]);
      setGlobalBanner({
        type: 'success',
        text: `Session '${sessionId}' deleted from backend storage. Initialized fresh session (${newId}).`,
      });
    } catch (err: unknown) {
      const msg = err instanceof ApiClientError ? err.userMessage : 'Failed to delete session on backend.';
      setGlobalBanner({ type: 'error', text: msg });
    } finally {
      setIsLoading(false);
      setTimeout(() => setGlobalBanner(null), 4000);
    }
  }, [sessionId]);

  // =====================================================================
  // MESSAGE SENDING & MULTI-TURN AGENT INVOCATION
  // =====================================================================

  const handleSendMessage = async (queryText: string) => {
    const trimmed = queryText.trim();
    if (!trimmed || isLoading) return;

    setGlobalBanner(null);

    // 1. Append User Message
    const userMsg: AgentChatMessage = {
      id: `user-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      role: 'user',
      content: trimmed,
      timestamp: new Date(),
      sessionId,
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);
    setLoadingStage('Supervisor analyzing request & routing domain workers...');

    const start = performance.now();

    try {
      // 2. Call typed agent endpoint (POST /api/v1/agent/chat)
      const response = await apiClient.agentChat({
        session_id: sessionId,
        message: trimmed,
      });

      const elapsed = Math.round(performance.now() - start);

      // Check if response indicates Human Approval requirement
      let approvalId: string | null = null;
      let isApprovalPending = response.status === 'pending_approval';

      // Parse approval ID if present in final answer or trace
      const approvalMatch = response.answer.match(/Approval Request ID:\s*['"]?([a-zA-Z0-9_-]+)['"]?/i);
      if (approvalMatch) {
        approvalId = approvalMatch[1];
        isApprovalPending = true;
      } else if (isApprovalPending) {
        approvalId = `approval-${sessionId}`;
      }

      // Extract reason if present
      let approvalReason: string | null = null;
      const reasonMatch = response.answer.match(/Reason:\s*([^.\n]+)/i);
      if (reasonMatch) {
        approvalReason = reasonMatch[1].trim();
      }

      const assistantMsg: AgentChatMessage = {
        id: `assistant-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        role: 'assistant',
        content: response.answer,
        timestamp: new Date(),
        sessionId: response.session_id || sessionId,
        status: response.status,
        steps: response.steps || [],
        totalSteps: response.total_steps,
        durationMs: response.duration_ms || elapsed,
        usedRag: response.used_rag,
        citations: response.citations || [],
        trace: response.trace,
        approvalId,
        approvalRequired: isApprovalPending,
        approvalStatus: isApprovalPending ? 'pending' : undefined,
        approvalReason,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: unknown) {
      const elapsed = Math.round(performance.now() - start);
      let errorDetail = 'An unexpected error occurred while communicating with the agent backend.';

      if (err instanceof ApiClientError) {
        errorDetail = err.userMessage;
      } else if (err instanceof Error) {
        errorDetail = err.message;
      }

      const errorMsg: AgentChatMessage = {
        id: `assistant-err-${Date.now()}`,
        role: 'assistant',
        content: 'The enterprise agent encountered an error processing your inquiry.',
        timestamp: new Date(),
        sessionId,
        status: 'error',
        steps: [],
        totalSteps: 0,
        durationMs: elapsed,
        error: errorDetail,
      };

      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
      setLoadingStage('');
    }
  };

  // Handle initial prompt from WorkspaceHome
  useEffect(() => {
    if (initialPrompt && !initialPromptHandled.current) {
      initialPromptHandled.current = true;
      handleSendMessage(initialPrompt);
    }
  }, [initialPrompt]);

  // =====================================================================
  // HUMAN-IN-THE-LOOP APPROVAL SUBMISSION
  // =====================================================================

  const handleApprovalDecision = async (
    approvalId: string,
    decision: 'approve' | 'reject',
    notes?: string
  ) => {
    setIsDecisionLoading(true);
    setGlobalBanner(null);

    try {
      // Call POST /api/v1/agent/approvals/{approval_id}
      const response = await apiClient.submitApprovalDecision(approvalId, {
        decision,
        notes: notes || undefined,
      });

      // Update the existing message state with approval resolution
      setMessages((prev) =>
        prev.map((msg) => {
          if (msg.approvalId === approvalId) {
            return {
              ...msg,
              content: response.answer || msg.content,
              status: response.status,
              approvalStatus: decision === 'approve' ? 'approved' : 'rejected',
              approvalDecision: decision,
              approvalNotes: notes,
              durationMs: (msg.durationMs || 0) + (response.duration_ms || 0),
              trace: response.trace || msg.trace,
            };
          }
          return msg;
        })
      );

      setGlobalBanner({
        type: decision === 'approve' ? 'success' : 'info',
        text:
          decision === 'approve'
            ? `Operation authorized! Resumed workflow and received response.`
            : `Operation rejected. Sensitive execution terminated safely.`,
      });
    } catch (err: unknown) {
      let errMsg = 'Failed to submit approval decision.';
      if (err instanceof ApiClientError) {
        errMsg = err.userMessage;
      } else if (err instanceof Error) {
        errMsg = err.message;
      }
      setGlobalBanner({ type: 'error', text: errMsg });
      throw err;
    } finally {
      setIsDecisionLoading(false);
      setTimeout(() => setGlobalBanner(null), 5000);
    }
  };

  return (
    <div className="flex flex-col h-[760px] max-h-[85vh] rounded-2xl border border-[#E9E5DF] dark:border-[#2F3540] bg-[#FFFEFC] dark:bg-[#21252D] shadow-[0_2px_8px_rgba(38,49,66,0.03)] overflow-hidden transition-colors">
      {/* Top Header */}
      <div className="flex items-center justify-between px-4 sm:px-6 py-3.5 border-b border-[#E9E5DF] dark:border-[#2F3540] bg-[#FCFAF7] dark:bg-[#1B1E24]">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-[#DCCEEF] dark:bg-[#2E283E] border border-[#C5B4DF] dark:border-[#4B3E63] text-[#6E4E9E] dark:text-[#DCCEEF]">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xs sm:text-sm font-semibold text-[#263142] dark:text-[#EBEFF5]">
                Enterprise AI Agent Workspace
              </h2>
              <span className="px-2 py-0.2 rounded-full text-[10px] font-mono font-medium bg-[#DCCEEF]/40 dark:bg-[#2E283E] border border-[#C5B4DF] dark:border-[#4B3E63] text-[#263142] dark:text-[#DCCEEF]">
                LangGraph Multi-Agent
              </span>
            </div>
            <p className="text-[11px] text-[#697582] dark:text-[#9CA6B5] font-normal">
              Autonomous multi-step coordinator across PostgreSQL records, policies &amp; approvals
            </p>
          </div>
        </div>
      </div>

      {/* Session Control Toolbar */}
      <SessionControlBar
        sessionId={sessionId}
        onNewSession={handleNewSession}
        onClearSession={handleClearSession}
        onDeleteSession={handleDeleteSession}
        isLoading={isLoading}
        messageCount={messages.length}
      />

      {/* Global Toast / Feedback Banner */}
      {globalBanner && (
        <div
          className={`px-6 py-2.5 border-b text-xs flex items-center justify-between transition-all ${
            globalBanner.type === 'error'
              ? 'bg-[#FDE8E8] dark:bg-[#3D2525] border-[#FBD5D5] dark:border-[#522828] text-[#9B1C1C] dark:text-[#F87171]'
              : globalBanner.type === 'success'
              ? 'bg-[#E5F5F1] dark:bg-[#1A2D2A] border-[#C7E9E2] dark:border-[#244742] text-[#263142] dark:text-[#A9DED5]'
              : 'bg-[#F8F6F2] dark:bg-[#282D37] border-[#E9E5DF] dark:border-[#2F3540] text-[#263142] dark:text-[#EBEFF5]'
          }`}
        >
          <div className="flex items-center gap-2">
            {globalBanner.type === 'error' ? (
              <AlertCircle className="w-3.5 h-3.5 text-[#C53030] dark:text-[#F87171]" />
            ) : globalBanner.type === 'success' ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5]" />
            ) : (
              <Sparkles className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5]" />
            )}
            <span className="font-medium">{globalBanner.text}</span>
          </div>
          <button
            onClick={() => setGlobalBanner(null)}
            className="hover:opacity-75 font-mono text-xs cursor-pointer text-[#697582] dark:text-[#9CA6B5]"
          >
            &times;
          </button>
        </div>
      )}

      {/* Main Message Stream Container */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5 scrollbar-thin bg-[#F5F3EF]/40 dark:bg-[#16181D]/40">
        {messages.length === 0 ? (
          <AgentEmptyState onSelectPrompt={handleSendMessage} disabled={isLoading} />
        ) : (
          messages.map((msg) => (
            <AgentMessage
              key={msg.id}
              message={msg}
              onApprovalDecision={handleApprovalDecision}
              isDecisionLoading={isDecisionLoading}
            />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Sticky Bottom Composer */}
      <div className="p-3.5 sm:p-4 border-t border-[#E9E5DF] dark:border-[#2F3540] bg-[#FCFAF7] dark:bg-[#1B1E24]">
        <AgentComposer
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
          loadingStage={loadingStage}
        />
      </div>
    </div>
  );
}
