'use client';

import React from 'react';
import { BackendStatusBadge } from '@/components/BackendStatusBadge';
import { ThemeToggle } from '@/components/ThemeToggle';
import {
  Menu,
  BookOpen,
  Layers,
  ChevronRight,
  Bot,
  Compass,
  Files,
} from 'lucide-react';
import { WorkspaceTab } from './SidebarNav';

interface TopBarProps {
  activeTab: WorkspaceTab;
  onSelectTab: (tab: WorkspaceTab) => void;
  onOpenArchitecture: () => void;
  onToggleMobileNav: () => void;
}

export function TopBar({
  activeTab,
  onSelectTab,
  onOpenArchitecture,
  onToggleMobileNav,
}: TopBarProps) {
  const getWorkspaceTitle = () => {
    switch (activeTab) {
      case 'rag':
        return {
          title: 'Policy Assistant',
          subtitle: 'Hybrid RAG grounded in company policy documents',
          icon: <BookOpen className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5]" />,
        };
      case 'agent':
        return {
          title: 'Enterprise AI Agent',
          subtitle: 'Autonomous task orchestration & human-in-the-loop approval',
          icon: <Bot className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5]" />,
        };
      case 'kb':
        return {
          title: 'Knowledge Base',
          subtitle: 'Indexed policy document registry & chunk passages',
          icon: <Files className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5]" />,
        };
      case 'home':
      default:
        return {
          title: 'Workspace Home',
          subtitle: 'Unified enterprise support & multi-agent system',
          icon: <Compass className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5]" />,
        };
    }
  };

  const { title, subtitle, icon } = getWorkspaceTitle();

  return (
    <header className="sticky top-0 z-30 h-16 border-b border-[#E9E5DF] dark:border-[#2F3540] bg-[#FCFAF7]/95 dark:bg-[#1B1E24]/95 backdrop-blur-md transition-colors select-none">
      <div className="h-full px-4 sm:px-6 flex items-center justify-between gap-4">
        {/* Left: Mobile Menu Toggle + Breadcrumbs */}
        <div className="flex items-center gap-3 min-w-0">
          <button
            type="button"
            onClick={onToggleMobileNav}
            aria-label="Toggle navigation drawer"
            className="md:hidden p-2 rounded-xl text-[#697582] dark:text-[#9CA6B5] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] border border-[#E9E5DF] dark:border-[#2F3540] transition-colors"
          >
            <Menu className="w-4 h-4" />
          </button>

          {/* Breadcrumbs & Title */}
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-xs text-[#697582] dark:text-[#9CA6B5]">
              <span className="font-semibold text-[#263142] dark:text-[#EBEFF5] truncate flex items-center gap-1.5">
                <span>Enterprise Support AI Agent</span>
                <span className="inline-flex items-center px-1.5 py-0.2 rounded-full text-[9px] font-medium bg-[#E5F5F1] dark:bg-[#1A2D2A] text-[#263142] dark:text-[#A9DED5] border border-[#C7E9E2] dark:border-[#244742]">
                  Production v1.0
                </span>
              </span>
              <ChevronRight className="w-3 h-3 text-[#9299A3] dark:text-[#6E7887] hidden sm:inline" />
              <span className="hidden sm:inline-flex items-center gap-1 font-medium text-[#263142] dark:text-[#EBEFF5]">
                {icon}
                <span>{title}</span>
              </span>
            </div>
            <p className="hidden md:block text-[11px] text-[#697582] dark:text-[#9CA6B5] truncate font-normal">
              {subtitle}
            </p>
          </div>
        </div>

        {/* Right: Technical diagnostics, backend badge, API docs, theme toggle */}
        <div className="flex items-center gap-2 sm:gap-2.5 flex-shrink-0">
          {/* Architecture Modal Trigger */}
          <button
            type="button"
            onClick={onOpenArchitecture}
            aria-label="View system architecture and tech stack"
            title="View Technical Architecture Details"
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium text-[#263142] dark:text-[#EBEFF5] hover:text-[#368F88] dark:hover:text-[#A9DED5] bg-[#FFFFFF] dark:bg-[#21252D] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] border border-[#E9E5DF] dark:border-[#2F3540] transition-colors cursor-pointer shadow-[0_1px_2px_rgba(38,49,66,0.03)]"
          >
            <Layers className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5]" />
            <span className="hidden sm:inline">Architecture</span>
          </button>

          {/* Backend Status Indicator */}
          <BackendStatusBadge />

          {/* FastAPI Swagger Documentation */}
          <a
            href="http://127.0.0.1:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Open FastAPI Swagger Documentation"
            title="Open Swagger API Reference"
            className="hidden lg:inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium text-[#697582] dark:text-[#9CA6B5] hover:text-[#368F88] dark:hover:text-[#A9DED5] bg-[#FFFFFF] dark:bg-[#21252D] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] border border-[#E9E5DF] dark:border-[#2F3540] transition-colors shadow-[0_1px_2px_rgba(38,49,66,0.03)]"
          >
            <BookOpen className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5]" />
            <span>API Docs</span>
          </a>

          {/* Theme Switcher Toggle */}
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
