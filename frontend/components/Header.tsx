'use client';

import React, { useState } from 'react';
import { BackendStatusBadge } from './BackendStatusBadge';
import { ThemeToggle } from './ThemeToggle';
import { ArchitectureModal } from './ArchitectureModal';
import { ShieldCheck, BookOpen, Layers, Sparkles } from 'lucide-react';

interface HeaderProps {
  activeMode?: 'rag' | 'agent';
  onModeSelect?: (mode: 'rag' | 'agent') => void;
}

export function Header({ activeMode = 'rag', onModeSelect }: HeaderProps) {
  const [isArchModalOpen, setIsArchModalOpen] = useState<boolean>(false);

  return (
    <>
      <header className="sticky top-0 z-40 backdrop-blur-md bg-white/80 dark:bg-slate-950/80 border-b border-slate-200 dark:border-slate-800/80 transition-all">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-20">
            {/* Brand & Subtitle */}
            <div className="flex items-center gap-3.5">
              <div className="flex items-center justify-center w-11 h-11 rounded-2xl bg-gradient-to-br from-indigo-500 via-cyan-500 to-teal-400 p-[1.5px] shadow-lg shadow-indigo-500/20 flex-shrink-0">
                <div className="w-full h-full bg-white dark:bg-slate-950 rounded-[14px] flex items-center justify-center">
                  <ShieldCheck className="w-6 h-6 text-cyan-600 dark:text-cyan-400" />
                </div>
              </div>

              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-base sm:text-lg font-extrabold tracking-tight text-slate-900 dark:text-white">
                    Enterprise Support AI Agent
                  </h1>
                  <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-100 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/30">
                    Production v1.0
                  </span>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 font-normal line-clamp-1">
                  Grounded enterprise assistant powered by RAG, PostgreSQL, tool calling, and LangGraph
                </p>
              </div>
            </div>

            {/* Right Action Bar */}
            <div className="flex items-center gap-2 sm:gap-3">
              {/* Architecture & Tech Stack Showcase Modal Trigger */}
              <button
                type="button"
                onClick={() => setIsArchModalOpen(true)}
                aria-label="View System Architecture and Tech Stack"
                title="View Technical Architecture Details"
                className="hidden lg:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-indigo-700 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-500/30 hover:bg-indigo-100 dark:hover:bg-indigo-900/80 transition-all cursor-pointer shadow-sm"
              >
                <Layers className="w-3.5 h-3.5 text-indigo-500 dark:text-indigo-400" />
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
                className="hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-700/60 hover:bg-slate-200 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white transition-all shadow-sm"
              >
                <BookOpen className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
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

