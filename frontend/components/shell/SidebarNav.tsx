'use client';

import React from 'react';
import {
  Compass,
  BookOpen,
  Bot,
  Files,
  Plus,
  ShieldCheck,
  Layers,
  ExternalLink,
} from 'lucide-react';

export type WorkspaceTab = 'home' | 'rag' | 'agent' | 'kb';

interface SidebarNavProps {
  activeTab: WorkspaceTab;
  onSelectTab: (tab: WorkspaceTab) => void;
  onNewConversation?: () => void;
  onOpenArchitecture: () => void;
  isMobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export function SidebarNav({
  activeTab,
  onSelectTab,
  onNewConversation,
  onOpenArchitecture,
  isMobileOpen = false,
  onCloseMobile,
}: SidebarNavProps) {
  const navItems = [
    {
      id: 'home' as WorkspaceTab,
      label: 'Workspace Home',
      shortLabel: 'Home',
      icon: <Compass className="w-4 h-4" />,
      badge: null,
      desc: 'Overview, prompt composer & workspace directory',
    },
    {
      id: 'rag' as WorkspaceTab,
      label: 'Policy Assistant',
      shortLabel: 'Policies',
      icon: <BookOpen className="w-4 h-4" />,
      badge: 'Hybrid RAG',
      desc: 'Document grounded policy research & citations',
    },
    {
      id: 'agent' as WorkspaceTab,
      label: 'Enterprise AI Agent',
      shortLabel: 'Agent',
      icon: <Bot className="w-4 h-4" />,
      badge: 'LangGraph',
      desc: 'Multi-agent orchestration, tools & human approval',
    },
    {
      id: 'kb' as WorkspaceTab,
      label: 'Knowledge Base',
      shortLabel: 'Docs',
      icon: <Files className="w-4 h-4" />,
      badge: '4 Docs',
      desc: 'Indexed policy document registry & chunk inspector',
    },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div
          role="button"
          tabIndex={0}
          aria-label="Close navigation drawer"
          onClick={onCloseMobile}
          onKeyDown={(e) => {
            if (e.key === 'Escape' || e.key === 'Enter') onCloseMobile?.();
          }}
          className="fixed inset-0 z-40 bg-[#263142]/30 backdrop-blur-xs md:hidden transition-opacity"
        />
      )}

      {/* Nav Rail / Drawer */}
      <aside
        aria-label="Application Navigation Rail"
        className={`fixed md:sticky top-0 left-0 z-50 h-screen w-64 md:w-16 lg:w-60 flex-shrink-0 flex flex-col justify-between border-r border-[#E9E5DF] dark:border-[#2F3540] bg-[#FCFAF7] dark:bg-[#1B1E24] transition-transform duration-200 ease-in-out select-none ${
          isMobileOpen ? 'translate-x-0 shadow-xl' : '-translate-x-full md:translate-x-0'
        }`}
      >
        {/* Top Branding & New Chat Section */}
        <div className="p-3 sm:p-3.5 space-y-3">
          {/* Brand Mark with Soft Mint Pastel Icon Container */}
          <div className="flex items-center gap-2.5 px-2 py-1.5">
            <div className="flex items-center justify-center w-8 h-8 rounded-xl bg-[#E5F5F1] dark:bg-[#1A2D2A] text-[#368F88] dark:text-[#A9DED5] border border-[#C7E9E2] dark:border-[#244742] shadow-[0_1px_2px_rgba(38,49,66,0.04)] flex-shrink-0">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div className="min-w-0 md:hidden lg:block">
              <div className="text-xs font-semibold text-[#263142] dark:text-[#EBEFF5] truncate tracking-tight">
                Enterprise AI
              </div>
              <div className="text-[10px] text-[#697582] dark:text-[#9CA6B5] font-mono">
                Support Platform
              </div>
            </div>
          </div>

          {/* New Conversation Button */}
          {onNewConversation && (
            <button
              type="button"
              onClick={() => {
                onNewConversation();
                onCloseMobile?.();
              }}
              title="Start New Conversation"
              aria-label="Start New Conversation"
              className="w-full flex items-center justify-center lg:justify-start gap-2 px-2.5 py-2 rounded-xl text-xs font-medium text-[#263142] dark:text-[#EBEFF5] bg-[#FFFFFF] dark:bg-[#21252D] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] border border-[#E9E5DF] dark:border-[#2F3540] transition-colors cursor-pointer shadow-[0_1px_2px_rgba(38,49,66,0.03)]"
            >
              <Plus className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5] flex-shrink-0" />
              <span className="hidden lg:inline truncate">New Conversation</span>
            </button>
          )}

          {/* Nav Links */}
          <nav aria-label="Workspaces" className="space-y-1 pt-1">
            <div className="hidden lg:block px-2 pb-1 text-[10px] font-semibold uppercase tracking-wider text-[#9299A3] dark:text-[#6E7887]">
              Workspaces
            </div>

            {navItems.map((item) => {
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => {
                    onSelectTab(item.id);
                    onCloseMobile?.();
                  }}
                  title={item.label}
                  aria-label={item.label}
                  aria-current={isActive ? 'page' : undefined}
                  className={`w-full flex items-center justify-center lg:justify-between px-2.5 py-2 rounded-xl text-xs transition-colors cursor-pointer group ${
                    isActive
                      ? 'bg-[#E5F5F1] dark:bg-[#1A2D2A] text-[#263142] dark:text-[#EBEFF5] border border-[#C7E9E2] dark:border-[#244742] font-semibold shadow-[0_1px_2px_rgba(38,49,66,0.03)]'
                      : 'text-[#697582] dark:text-[#9CA6B5] hover:text-[#263142] dark:hover:text-[#EBEFF5] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] border border-transparent font-normal'
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span
                      className={`flex-shrink-0 ${
                        isActive
                          ? 'text-[#368F88] dark:text-[#A9DED5]'
                          : 'text-[#9299A3] group-hover:text-[#263142] dark:group-hover:text-[#EBEFF5]'
                      }`}
                    >
                      {item.icon}
                    </span>
                    <span className="hidden lg:inline truncate text-[12px]">{item.label}</span>
                  </div>

                  {item.badge && (
                    <span
                      className={`hidden lg:inline-flex px-1.5 py-0.2 rounded-md text-[9px] font-mono font-medium ${
                        isActive
                          ? 'bg-[#C7E9E2]/60 dark:bg-[#244742] text-[#263142] dark:text-[#A9DED5]'
                          : 'bg-[#F8F6F2] dark:bg-[#21252D] text-[#697582] dark:text-[#9CA6B5] border border-[#E9E5DF] dark:border-[#2F3540]'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Bottom Technical & External Access */}
        <div className="p-3 border-t border-[#E9E5DF] dark:border-[#2F3540] space-y-1">
          {/* Architecture Modal Trigger */}
          <button
            type="button"
            onClick={() => {
              onOpenArchitecture();
              onCloseMobile?.();
            }}
            title="System Architecture & Diagnostics"
            aria-label="View system architecture and tech stack"
            className="w-full flex items-center justify-center lg:justify-between px-2.5 py-2 rounded-xl text-xs text-[#697582] dark:text-[#9CA6B5] hover:text-[#263142] dark:hover:text-[#EBEFF5] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] transition-colors cursor-pointer"
          >
            <div className="flex items-center gap-2.5">
              <Layers className="w-4 h-4 text-[#368F88] dark:text-[#A9DED5] flex-shrink-0" />
              <span className="hidden lg:inline text-[11px] font-medium">Architecture</span>
            </div>
            <span className="hidden lg:inline-flex text-[9px] font-mono text-[#9299A3] dark:text-[#6E7887]">Modal</span>
          </button>

          {/* FastAPI Swagger Docs Link */}
          <a
            href="http://127.0.0.1:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            title="Open FastAPI Swagger Documentation"
            aria-label="Open FastAPI Swagger Documentation"
            className="w-full flex items-center justify-center lg:justify-between px-2.5 py-2 rounded-xl text-xs text-[#697582] dark:text-[#9CA6B5] hover:text-[#368F88] dark:hover:text-[#A9DED5] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] transition-colors"
          >
            <div className="flex items-center gap-2.5">
              <ExternalLink className="w-4 h-4 text-[#9299A3] dark:text-[#6E7887] flex-shrink-0" />
              <span className="hidden lg:inline text-[11px] font-medium">API Docs</span>
            </div>
            <span className="hidden lg:inline-flex text-[9px] font-mono text-[#9299A3] dark:text-[#6E7887]">:8000</span>
          </a>
        </div>
      </aside>
    </>
  );
}
