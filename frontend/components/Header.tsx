'use client';

import React, { useState } from 'react';
import { BackendStatusBadge } from './BackendStatusBadge';
import { ThemeToggle } from './ThemeToggle';
import { ArchitectureModal } from './ArchitectureModal';
import { ShieldCheck, BookOpen, Layers } from 'lucide-react';

interface HeaderProps {
  activeMode?: 'rag' | 'agent';
  onModeSelect?: (mode: 'rag' | 'agent') => void;
}

export function Header({ activeMode = 'rag', onModeSelect }: HeaderProps) {
  const [isArchModalOpen, setIsArchModalOpen] = useState<boolean>(false);

  return (
    <>
      <header className="sticky top-0 z-40 bg-[#FCFAF7]/95 dark:bg-[#1B1E24]/95 backdrop-blur-md border-b border-[#E9E5DF] dark:border-[#2F3540] transition-colors select-none">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Brand & Subtitle */}
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-8 h-8 rounded-xl bg-[#E5F5F1] dark:bg-[#1A2D2A] text-[#368F88] dark:text-[#A9DED5] border border-[#C7E9E2] dark:border-[#244742] shadow-[0_1px_2px_rgba(38,49,66,0.04)] flex-shrink-0">
                <ShieldCheck className="w-4 h-4" />
              </div>

              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-sm sm:text-base font-semibold tracking-tight text-[#263142] dark:text-[#EBEFF5]">
                    Enterprise Support AI Agent
                  </h1>
                  <span className="hidden sm:inline-flex items-center px-2 py-0.2 rounded-full text-[10px] font-medium bg-[#E5F5F1] dark:bg-[#1A2D2A] text-[#263142] dark:text-[#A9DED5] border border-[#C7E9E2] dark:border-[#244742]">
                    Production v1.0
                  </span>
                </div>
                <p className="text-[11px] text-[#697582] dark:text-[#9CA6B5] font-normal line-clamp-1">
                  Grounded enterprise assistant powered by RAG, PostgreSQL, tool calling, and LangGraph
                </p>
              </div>
            </div>

            {/* Right Action Bar */}
            <div className="flex items-center gap-2 sm:gap-2.5">
              {/* Architecture & Tech Stack Showcase Modal Trigger */}
              <button
                type="button"
                onClick={() => setIsArchModalOpen(true)}
                aria-label="View System Architecture and Tech Stack"
                title="View Technical Architecture Details"
                className="hidden lg:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium text-[#263142] dark:text-[#EBEFF5] hover:text-[#368F88] dark:hover:text-[#A9DED5] bg-[#FFFFFF] dark:bg-[#21252D] border border-[#E9E5DF] dark:border-[#2F3540] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] transition-colors cursor-pointer shadow-[0_1px_2px_rgba(38,49,66,0.03)]"
              >
                <Layers className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5]" />
                <span>Architecture</span>
              </button>

              {/* Live Backend Status Badge */}
              <BackendStatusBadge />

              {/* Quick Link to FastAPI Docs */}
              <a
                href="http://127.0.0.1:8000/docs"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Open FastAPI Swagger Documentation"
                className="hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium text-[#697582] dark:text-[#9CA6B5] bg-[#FFFFFF] dark:bg-[#21252D] border border-[#E9E5DF] dark:border-[#2F3540] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] transition-colors shadow-[0_1px_2px_rgba(38,49,66,0.03)]"
              >
                <BookOpen className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5]" />
                <span>API Docs</span>
              </a>

              {/* Theme Switcher Toggle */}
              <ThemeToggle />
            </div>
          </div>
        </div>
      </header>

      {/* Architecture Showcase Modal */}
      <ArchitectureModal
        isOpen={isArchModalOpen}
        onClose={() => setIsArchModalOpen(false)}
      />
    </>
  );
}
