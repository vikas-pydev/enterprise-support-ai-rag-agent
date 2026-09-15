'use client';

import React, { useState, useRef, useEffect } from 'react';
import { PolicyChatMessage } from '@/types/chat';
import { apiClient } from '@/lib/api/client';
import { ApiClientError } from '@/lib/api/errors';
import { EmptyState } from './EmptyState';
import { ChatMessage } from './ChatMessage';
import { MessageComposer } from './MessageComposer';
import { BookOpen, Sparkles, RotateCcw, AlertCircle } from 'lucide-react';

export function PolicyChatWorkspace() {
  const [messages, setMessages] = useState<PolicyChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [loadingStage, setLoadingStage] = useState<string>('');
  const [globalError, setGlobalError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleClearChat = () => {
    setMessages([]);
    setGlobalError(null);
  };

  const handleSendMessage = async (questionText: string) => {
    const trimmed = questionText.trim();
    if (!trimmed || isLoading) return;

    setGlobalError(null);

    // 1. Append user message
    const userMsg: PolicyChatMessage = {
      id: `user-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      role: 'user',
      content: trimmed,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);
    setLoadingStage('Searching policy knowledge base & retrieving citations...');

    const start = performance.now();

    try {
      // 2. Call typed API client for POST /api/v1/ask
      const response = await apiClient.askPolicyQuestion({ question: trimmed });
      const elapsed = Math.round(performance.now() - start);

      const assistantMsg: PolicyChatMessage = {
        id: `assistant-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        role: 'assistant',
        content: response.answer,
        timestamp: new Date(),
        isRefusal: response.is_refusal,
        sources: response.sources || [],
        durationMs: elapsed,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: unknown) {
      const elapsed = Math.round(performance.now() - start);
      let errorDetail = 'An unexpected error occurred while communicating with the backend.';

      if (err instanceof ApiClientError) {
        errorDetail = err.userMessage;
      } else if (err instanceof Error) {
        errorDetail = err.message;
      }

      const errorMsg: PolicyChatMessage = {
        id: `assistant-err-${Date.now()}`,
        role: 'assistant',
        content: 'I was unable to retrieve policy information due to a service error.',
        timestamp: new Date(),
        isRefusal: false,
        sources: [],
        durationMs: elapsed,
        error: errorDetail,
      };

      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
      setLoadingStage('');
    }
  };

  return (
    <div className="flex flex-col h-[720px] max-h-[82vh] rounded-3xl border border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-950/70 shadow-2xl overflow-hidden backdrop-blur-xl transition-colors">
      {/* Workspace Header Toolbar */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800/80 bg-slate-50/80 dark:bg-slate-900/50">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-600 dark:text-cyan-400 shadow-sm">
            <BookOpen className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-slate-900 dark:text-white">
                Policy Assistant Workspace
              </h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-cyan-100 dark:bg-cyan-950/80 border border-cyan-200 dark:border-cyan-500/30 text-cyan-700 dark:text-cyan-300">
                Hybrid RAG
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Grounded company policy Q&amp;A strictly backed by indexed employee documentation
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <button
              type="button"
              onClick={handleClearChat}
              disabled={isLoading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all disabled:opacity-50 cursor-pointer shadow-sm"
              title="Clear conversation history"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Clear Chat</span>
            </button>
          )}
        </div>
      </div>

      {/* Global Error Banner if any */}
      {globalError && (
        <div className="px-6 py-3 bg-rose-50 dark:bg-rose-950/60 border-b border-rose-200 dark:border-rose-500/30 text-rose-800 dark:text-rose-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 dark:text-rose-400" />
            <span>{globalError}</span>
          </div>
          <button
            onClick={() => setGlobalError(null)}
            className="text-rose-600 dark:text-rose-400 hover:opacity-75 font-mono text-xs cursor-pointer"
          >
            &times;
          </button>
        </div>
      )}

      {/* Main Message Stream Container */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
        {messages.length === 0 ? (
          <EmptyState onSelectQuestion={handleSendMessage} disabled={isLoading} />
        ) : (
          messages.map((msg) => <ChatMessage key={msg.id} message={msg} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Sticky Bottom Composer */}
      <div className="p-4 sm:p-5 border-t border-slate-200 dark:border-slate-800/80 bg-slate-50/90 dark:bg-slate-950/90 backdrop-blur-md">
        <MessageComposer
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
          loadingStage={loadingStage}
        />
      </div>
    </div>
  );
}

