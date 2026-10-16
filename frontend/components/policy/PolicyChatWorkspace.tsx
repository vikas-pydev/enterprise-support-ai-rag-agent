'use client';

import React, { useState, useRef, useEffect } from 'react';
import { PolicyChatMessage } from '@/types/chat';
import { CitationSource } from '@/types/api';
import { apiClient } from '@/lib/api/client';
import { ApiClientError } from '@/lib/api/errors';
import { EmptyState } from './EmptyState';
import { ChatMessage } from './ChatMessage';
import { MessageComposer } from './MessageComposer';
import { KnowledgeBasePanel } from './KnowledgeBasePanel';
import { SourceInspectorPanel } from './SourceInspectorPanel';
import { PolicyDocument } from '@/lib/knowledge/documents';
import {
  BookOpen,
  RotateCcw,
  AlertCircle,
  Files,
  Info,
} from 'lucide-react';

interface PolicyChatWorkspaceProps {
  initialQuery?: string;
}

export function PolicyChatWorkspace({ initialQuery }: PolicyChatWorkspaceProps) {
  const [messages, setMessages] = useState<PolicyChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [loadingStage, setLoadingStage] = useState<string>('');
  const [globalError, setGlobalError] = useState<string | null>(null);

  // 3-Panel Layout States
  const [isKbCollapsed, setIsKbCollapsed] = useState<boolean>(false);
  const [isInspectorOpen, setIsInspectorOpen] = useState<boolean>(false);
  const [selectedCitation, setSelectedCitation] = useState<CitationSource | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<PolicyDocument | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const initialQueryHandled = useRef<boolean>(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleClearChat = () => {
    setMessages([]);
    setGlobalError(null);
    setSelectedCitation(null);
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

      // If citations were returned, auto-select the highest ranked citation to inspect
      if (response.sources && response.sources.length > 0) {
        setSelectedCitation(response.sources[0]);
        setSelectedDocument(null);
        // On wider screens, open inspector automatically
        if (typeof window !== 'undefined' && window.innerWidth >= 1280) {
          setIsInspectorOpen(true);
        }
      }
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

  // Handle initial prompt if passed from WorkspaceHome
  useEffect(() => {
    if (initialQuery && !initialQueryHandled.current) {
      initialQueryHandled.current = true;
      handleSendMessage(initialQuery);
    }
  }, [initialQuery]);

  const handleSelectCitation = (citation: CitationSource) => {
    setSelectedCitation(citation);
    setSelectedDocument(null);
    setIsInspectorOpen(true);
  };

  const handleSelectDocument = (doc: PolicyDocument) => {
    setSelectedDocument(doc);
    setSelectedCitation(null);
    setIsInspectorOpen(true);
  };

  return (
    <div className="flex h-[760px] max-h-[85vh] rounded-2xl border border-[#E9E5DF] dark:border-[#2F3540] bg-[#FFFEFC] dark:bg-[#21252D] shadow-[0_2px_8px_rgba(38,49,66,0.03)] overflow-hidden transition-colors">
      {/* 1. Left Panel: Knowledge Base Document Browser */}
      <div className="hidden md:flex">
        <KnowledgeBasePanel
          selectedDocumentId={selectedDocument?.id}
          onSelectDocument={handleSelectDocument}
          isCollapsed={isKbCollapsed}
          onToggleCollapse={() => setIsKbCollapsed(!isKbCollapsed)}
        />
      </div>

      {/* 2. Center Panel: Conversational Research Workspace */}
      <div className="flex-1 min-w-0 flex flex-col justify-between overflow-hidden bg-[#F5F3EF]/40 dark:bg-[#16181D]/40">
        {/* Workspace Header Toolbar */}
        <div className="flex items-center justify-between px-4 sm:px-6 py-3.5 border-b border-[#E9E5DF] dark:border-[#2F3540] bg-[#FCFAF7] dark:bg-[#1B1E24]">
          <div className="flex items-center gap-3 min-w-0">
            <div className="p-2 rounded-xl bg-[#E5F5F1] dark:bg-[#1A2D2A] border border-[#C7E9E2] dark:border-[#244742] text-[#368F88] dark:text-[#A9DED5]">
              <BookOpen className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h2 className="text-xs sm:text-sm font-semibold text-[#263142] dark:text-[#EBEFF5] truncate">
                  Policy Assistant Workspace
                </h2>
                <span className="px-2 py-0.2 rounded-full text-[10px] font-mono font-medium bg-[#E5F5F1] dark:bg-[#1A2D2A] border border-[#C7E9E2] dark:border-[#244742] text-[#263142] dark:text-[#A9DED5]">
                  Hybrid RAG
                </span>
              </div>
              <p className="text-[11px] text-[#697582] dark:text-[#9CA6B5] truncate font-normal">
                Grounded company policy Q&amp;A strictly backed by indexed employee documentation
              </p>
            </div>
          </div>

          {/* Action Controls */}
          <div className="flex items-center gap-2 flex-shrink-0">
            {/* Toggle Knowledge Base on tablet */}
            <button
              type="button"
              onClick={() => setIsKbCollapsed(!isKbCollapsed)}
              title={isKbCollapsed ? 'Show Knowledge Base' : 'Hide Knowledge Base'}
              className="hidden sm:inline-flex md:hidden p-1.5 rounded-lg text-[#697582] hover:text-[#263142] dark:text-[#9CA6B5] dark:hover:text-[#EBEFF5] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] border border-[#E9E5DF] dark:border-[#2F3540] transition-colors text-xs"
            >
              <Files className="w-3.5 h-3.5" />
            </button>

            {/* Toggle Source Inspector Panel */}
            <button
              type="button"
              onClick={() => setIsInspectorOpen(!isInspectorOpen)}
              title={isInspectorOpen ? 'Close Source Inspector' : 'Open Source Inspector'}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium border transition-colors cursor-pointer ${
                isInspectorOpen
                  ? 'bg-[#E5F5F1] dark:bg-[#1A2D2A] text-[#263142] dark:text-[#A9DED5] border-[#A9DED5] dark:border-[#368F88]'
                  : 'bg-[#FFFFFF] dark:bg-[#21252D] text-[#697582] dark:text-[#9CA6B5] border-[#E9E5DF] dark:border-[#2F3540] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37]'
              }`}
            >
              <Info className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5]" />
              <span className="hidden lg:inline">{isInspectorOpen ? 'Hide Sources' : 'Inspect Sources'}</span>
            </button>

            {/* Clear Chat */}
            {messages.length > 0 && (
              <button
                type="button"
                onClick={handleClearChat}
                disabled={isLoading}
                className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium text-[#697582] dark:text-[#9CA6B5] hover:text-[#263142] dark:hover:text-[#EBEFF5] bg-[#FFFFFF] dark:bg-[#21252D] border border-[#E9E5DF] dark:border-[#2F3540] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] transition-colors disabled:opacity-50 cursor-pointer shadow-[0_1px_2px_rgba(38,49,66,0.03)]"
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
          <div className="px-6 py-2.5 bg-[#FDE8E8] dark:bg-[#3D2525] border-b border-[#FBD5D5] dark:border-[#522828] text-[#9B1C1C] dark:text-[#F87171] text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-[#C53030] dark:text-[#F87171]" />
              <span>{globalError}</span>
            </div>
            <button
              onClick={() => setGlobalError(null)}
              className="text-[#9B1C1C] dark:text-[#F87171] hover:opacity-75 font-mono text-xs cursor-pointer"
            >
              &times;
            </button>
          </div>
        )}

        {/* Main Message Stream Container */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5 scrollbar-thin">
          {messages.length === 0 ? (
            <EmptyState onSelectQuestion={handleSendMessage} disabled={isLoading} />
          ) : (
            messages.map((msg) => (
              <ChatMessage
                key={msg.id}
                message={msg}
                onSelectCitation={handleSelectCitation}
                selectedCitationUid={selectedCitation?.chunk_uid}
              />
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Sticky Bottom Composer */}
        <div className="p-3.5 sm:p-4 border-t border-[#E9E5DF] dark:border-[#2F3540] bg-[#FCFAF7] dark:bg-[#1B1E24]">
          <MessageComposer
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
            loadingStage={loadingStage}
          />
        </div>
      </div>

      {/* 3. Right Panel: Source Inspector & Document Preview */}
      <SourceInspectorPanel
        isOpen={isInspectorOpen}
        onClose={() => setIsInspectorOpen(false)}
        selectedCitation={selectedCitation}
        selectedDocument={selectedDocument}
      />
    </div>
  );
}
