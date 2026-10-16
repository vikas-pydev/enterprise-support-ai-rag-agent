'use client';

import React, { useState } from 'react';
import { SidebarNav, WorkspaceTab } from '@/components/shell/SidebarNav';
import { TopBar } from '@/components/shell/TopBar';
import { WorkspaceHome } from '@/components/home/WorkspaceHome';
import { PolicyChatWorkspace } from '@/components/policy/PolicyChatWorkspace';
import { AgentChatWorkspace } from '@/components/agent/AgentChatWorkspace';
import { ArchitectureModal } from '@/components/ArchitectureModal';
import { ShieldCheck, ExternalLink, BookOpen, Bot, Database } from 'lucide-react';
import { INDEXED_POLICY_DOCUMENTS } from '@/lib/knowledge/documents';

export default function Home() {
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('home');
  const [activeMode, setActiveMode] = useState<'rag' | 'agent'>('rag');
  const [isMobileNavOpen, setIsMobileNavOpen] = useState<boolean>(false);
  const [isArchModalOpen, setIsArchModalOpen] = useState<boolean>(false);
  const [pendingPrompt, setPendingPrompt] = useState<string | undefined>(undefined);

  const handleSelectTab = (tab: WorkspaceTab) => {
    setActiveTab(tab);
    if (tab === 'rag') setActiveMode('rag');
    if (tab === 'agent') setActiveMode('agent');
  };

  const handleWorkspaceSelectFromHome = (mode: 'rag' | 'agent', initialPrompt?: string) => {
    setActiveMode(mode);
    setActiveTab(mode);
    setPendingPrompt(initialPrompt);
  };

  const handleNewConversation = () => {
    setPendingPrompt(undefined);
    setActiveTab('home');
  };

  return (
    <div className="flex min-h-screen bg-[#F5F3EF] dark:bg-[#16181D] text-[#263142] dark:text-[#EBEFF5] transition-colors">
      {/* 1. Slim Persistent Left Navigation Rail */}
      <SidebarNav
        activeTab={activeTab}
        onSelectTab={handleSelectTab}
        onNewConversation={handleNewConversation}
        onOpenArchitecture={() => setIsArchModalOpen(true)}
        isMobileOpen={isMobileNavOpen}
        onCloseMobile={() => setIsMobileNavOpen(false)}
      />

      {/* 2. Main Content Frame with Contextual Top Bar */}
      <div className="flex-1 flex flex-col min-w-0 bg-[radial-gradient(ellipse_60%_40%_at_85%_0%,rgba(169,222,213,0.14),transparent_70%)] dark:bg-[radial-gradient(ellipse_60%_40%_at_85%_0%,rgba(54,143,136,0.08),transparent_70%)]">
        {/* Top Header Bar */}
        <TopBar
          activeTab={activeTab}
          onSelectTab={handleSelectTab}
          onOpenArchitecture={() => setIsArchModalOpen(true)}
          onToggleMobileNav={() => setIsMobileNavOpen(!isMobileNavOpen)}
        />

        {/* Workspace Work Surfaces */}
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-5 sm:py-7 space-y-6">
          {/* VIEW 1: WORKSPACE HOME */}
          {activeTab === 'home' && (
            <WorkspaceHome
              onSelectWorkspace={handleWorkspaceSelectFromHome}
              onOpenKnowledgeBase={() => setActiveTab('kb')}
            />
          )}

          {/* VIEW 2: POLICY ASSISTANT */}
          {activeTab === 'rag' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between px-1">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#697582] dark:text-[#9CA6B5]">
                  <BookOpen className="w-4 h-4 text-[#368F88] dark:text-[#A9DED5]" />
                  <span>Active Application Workspace: Policy Assistant</span>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveTab('home')}
                  className="text-xs font-medium text-[#368F88] dark:text-[#A9DED5] hover:text-[#2B7771] cursor-pointer"
                >
                  &larr; Back to Workspace Home
                </button>
              </div>

              <section
                id="panel-policy"
                role="tabpanel"
                aria-labelledby="tab-policy"
              >
                <PolicyChatWorkspace initialQuery={pendingPrompt} />
              </section>
            </div>
          )}

          {/* VIEW 3: ENTERPRISE AI AGENT */}
          {activeTab === 'agent' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between px-1">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#697582] dark:text-[#9CA6B5]">
                  <Bot className="w-4 h-4 text-[#368F88] dark:text-[#A9DED5]" />
                  <span>Active Application Workspace: Enterprise AI Agent</span>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveTab('home')}
                  className="text-xs font-medium text-[#368F88] dark:text-[#A9DED5] hover:text-[#2B7771] cursor-pointer"
                >
                  &larr; Back to Workspace Home
                </button>
              </div>

              <section
                id="panel-agent"
                role="tabpanel"
                aria-labelledby="tab-agent"
              >
                <AgentChatWorkspace initialPrompt={pendingPrompt} />
              </section>
            </div>
          )}

          {/* VIEW 4: KNOWLEDGE BASE REGISTRY EXPLORER */}
          {activeTab === 'kb' && (
            <div className="space-y-6 max-w-6xl mx-auto animate-in fade-in duration-150">
              <div className="flex items-center justify-between px-1">
                <div className="flex items-center gap-2">
                  <Database className="w-4 h-4 text-[#368F88] dark:text-[#A9DED5]" />
                  <h2 className="text-sm font-semibold text-[#263142] dark:text-[#EBEFF5] uppercase tracking-wider">
                    Enterprise Policy Document Registry
                  </h2>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveTab('rag')}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-[#368F88] hover:bg-[#2B7771] text-white cursor-pointer shadow-[0_1px_2px_rgba(38,49,66,0.05)]"
                >
                  <span>Open in Policy Assistant</span>
                  <BookOpen className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {INDEXED_POLICY_DOCUMENTS.map((doc, idx) => {
                  const pastelColors = [
                    'bg-[#E5F5F1] text-[#368F88] border-[#C7E9E2]',
                    'bg-[#DCCEEF] text-[#5A4384] border-[#CBB8E3]',
                    'bg-[#F7C9B8] text-[#9A4927] border-[#F1B5A0]',
                    'bg-[#CFE5D6] text-[#2F855A] border-[#B7D9C2]',
                  ];
                  const pastel = pastelColors[idx % pastelColors.length];

                  return (
                    <div
                      key={doc.id}
                      className="p-5 rounded-2xl border border-[#E9E5DF] dark:border-[#2F3540] bg-[#FFFEFC] dark:bg-[#21252D] flex flex-col justify-between space-y-3 shadow-[0_1px_3px_rgba(38,49,66,0.03)]"
                    >
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${pastel}`}>
                            {doc.category}
                          </span>
                          <span className="font-mono text-[10px] text-[#9299A3] dark:text-[#6E7887]">
                            v{doc.version}
                          </span>
                        </div>
                        <h3 className="text-sm font-semibold text-[#263142] dark:text-[#EBEFF5]">
                          {doc.title}
                        </h3>
                        <div className="text-[11px] font-mono text-[#697582] dark:text-[#9CA6B5] mt-0.5">
                          data/documents/{doc.filename} &bull; {doc.chunkCount} indexed passages
                        </div>
                        <p className="text-xs text-[#697582] dark:text-[#9CA6B5] mt-2 leading-relaxed font-normal">
                          {doc.summary}
                        </p>
                      </div>

                      <div className="pt-3 border-t border-[#E9E5DF]/60 dark:border-[#2F3540]/60 flex items-center justify-between">
                        <span className="text-[10px] text-[#9299A3] dark:text-[#6E7887] font-mono">
                          Dense Embeddings + BM25 Ingested
                        </span>
                        <button
                          type="button"
                          onClick={() => {
                            setActiveTab('rag');
                          }}
                          className="text-xs font-medium text-[#368F88] dark:text-[#A9DED5] hover:text-[#2B7771] cursor-pointer"
                        >
                          Query Document &rarr;
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </main>

        {/* Global Application Footer */}
        <footer className="border-t border-[#E9E5DF] dark:border-[#2F3540] bg-[#FCFAF7] dark:bg-[#1B1E24] py-4 mt-10 transition-colors select-none">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[#697582] dark:text-[#9CA6B5]">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-[#368F88] dark:text-[#A9DED5]" />
              <span>Enterprise Support AI Agent &bull; Next.js 16 + TypeScript + Tailwind CSS</span>
            </div>
            <div className="flex items-center gap-4">
              <button
                type="button"
                onClick={() => setIsArchModalOpen(true)}
                className="text-[#697582] dark:text-[#9CA6B5] hover:text-[#368F88] dark:hover:text-[#A9DED5] transition-colors font-medium cursor-pointer"
              >
                Architecture &amp; Diagnostics
              </button>
              <a
                href="http://127.0.0.1:8000/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-[#368F88] dark:hover:text-[#A9DED5] transition-colors flex items-center gap-1 text-[#368F88] dark:text-[#A9DED5] font-medium"
              >
                <span>Swagger API Docs</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>
        </footer>
      </div>

      {/* Global Architecture Modal */}
      <ArchitectureModal
        isOpen={isArchModalOpen}
        onClose={() => setIsArchModalOpen(false)}
      />
    </div>
  );
}
