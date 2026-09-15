'use client';

import React from 'react';
import {
  Bot,
  UserCheck,
  Calendar,
  Plane,
  Users,
  GitMerge,
  Globe,
  ShieldAlert,
  ArrowRight,
  Sparkles,
} from 'lucide-react';

interface AgentEmptyStateProps {
  onSelectPrompt: (promptText: string) => void;
  disabled?: boolean;
}

interface ExampleCategory {
  title: string;
  badge: string;
  icon: React.ReactNode;
  prompt: string;
  description: string;
  accentColor: string;
}

const DEMO_PROMPTS: ExampleCategory[] = [
  {
    title: 'Employee Profile',
    badge: 'SQL Records',
    icon: <UserCheck className="w-4 h-4 text-blue-500 dark:text-blue-400" />,
    prompt: "Show employee E1001's information.",
    description: 'Retrieve full name, job title, department, email, and manager info',
    accentColor: 'border-blue-200 dark:border-blue-500/30 hover:border-blue-400 dark:hover:border-blue-500/60 bg-blue-50/50 dark:bg-blue-950/20',
  },
  {
    title: 'Leave Balances',
    badge: 'SQL Balances',
    icon: <Calendar className="w-4 h-4 text-indigo-500 dark:text-indigo-400" />,
    prompt: 'How many annual leave days does E1001 have left?',
    description: 'Check remaining PTO, total allocated days, and category breakdown',
    accentColor: 'border-indigo-200 dark:border-indigo-500/30 hover:border-indigo-400 dark:hover:border-indigo-500/60 bg-indigo-50/50 dark:bg-indigo-950/20',
  },
  {
    title: 'Travel & Expenses',
    badge: 'SQL Expenses',
    icon: <Plane className="w-4 h-4 text-cyan-500 dark:text-cyan-400" />,
    prompt: 'How much has E1001 spent on travel?',
    description: 'Analyze total claims, approved totals, and categorized expense rollups',
    accentColor: 'border-cyan-200 dark:border-cyan-500/30 hover:border-cyan-400 dark:hover:border-cyan-500/60 bg-cyan-50/50 dark:bg-cyan-950/20',
  },
  {
    title: 'Manager Hierarchy',
    badge: 'SQL Hierarchy',
    icon: <Users className="w-4 h-4 text-violet-500 dark:text-violet-400" />,
    prompt: "Who is E1001's manager?",
    description: 'Direct organizational manager lookup via employee records worker',
    accentColor: 'border-violet-200 dark:border-violet-500/30 hover:border-violet-400 dark:hover:border-violet-500/60 bg-violet-50/50 dark:bg-violet-950/20',
  },
  {
    title: 'Multi-Step Query',
    badge: 'Multi-Tool Flow',
    icon: <GitMerge className="w-4 h-4 text-emerald-500 dark:text-emerald-400" />,
    prompt: 'How much has E1001 spent on travel, and who is their manager?',
    description: 'Executes travel summary and manager lookup in sequential steps',
    accentColor: 'border-emerald-200 dark:border-emerald-500/30 hover:border-emerald-400 dark:hover:border-emerald-500/60 bg-emerald-50/50 dark:bg-emerald-950/20',
  },
  {
    title: 'Cross-Domain (SQL + RAG)',
    badge: 'Cross-Domain',
    icon: <Globe className="w-4 h-4 text-teal-500 dark:text-teal-400" />,
    prompt: 'How much has E1001 spent on travel and what is the domestic meal allowance?',
    description: 'Combines PostgreSQL expense data with ChromaDB policy knowledge',
    accentColor: 'border-teal-200 dark:border-teal-500/30 hover:border-teal-400 dark:hover:border-teal-500/60 bg-teal-50/50 dark:bg-teal-950/20',
  },
  {
    title: 'Human-in-the-Loop Gate',
    badge: 'HITL Approval',
    icon: <ShieldAlert className="w-4 h-4 text-amber-500 dark:text-amber-400" />,
    prompt: 'Show confidential compensation details for employee E1000.',
    description: 'Triggers deterministic LangGraph authorization checkpoint for review',
    accentColor: 'border-amber-200 dark:border-amber-500/30 hover:border-amber-400 dark:hover:border-amber-500/60 bg-amber-50/50 dark:bg-amber-950/20',
  },
];

export function AgentEmptyState({ onSelectPrompt, disabled = false }: AgentEmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-6 px-2 sm:px-4 text-center max-w-4xl mx-auto space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col items-center max-w-2xl space-y-3">
        <div className="p-3.5 rounded-2xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-600 dark:text-indigo-400 shadow-lg shadow-indigo-500/10">
          <Bot className="w-7 h-7" />
        </div>

        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-100 dark:bg-indigo-950/80 border border-indigo-200 dark:border-indigo-500/30 text-indigo-800 dark:text-indigo-300 mb-2">
            <Sparkles className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
            <span>Autonomous Tool-Calling &amp; Supervisor Architecture</span>
          </div>
          <h3 className="text-xl sm:text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Enterprise AI Agent Workspace
          </h3>
          <p className="mt-2 text-xs sm:text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
            Ask the agent to retrieve employee records, evaluate leave balances, analyze travel claims, or orchestrate multi-step cross-domain workflows with verifiable evidence and human governance.
          </p>
        </div>
      </div>

      {/* Categorized Demo Queries Grid */}
      <div className="w-full text-left space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Suggested Technical Demo Inquiries
          </span>
          <span className="text-[11px] text-slate-500 hidden sm:inline">
            Click any prompt to execute immediately
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {DEMO_PROMPTS.map((item) => (
            <button
              key={item.title}
              type="button"
              disabled={disabled}
              onClick={() => onSelectPrompt(item.prompt)}
              className={`text-left p-3.5 rounded-2xl border transition-all duration-200 group flex flex-col justify-between ${item.accentColor} disabled:opacity-50 cursor-pointer shadow-sm`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
                      {item.icon}
                    </div>
                    <span className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-200 transition-colors">
                      {item.title}
                    </span>
                  </div>
                  <span className="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-white dark:bg-slate-900/90 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-800">
                    {item.badge}
                  </span>
                </div>

                <div className="text-xs font-medium text-slate-800 dark:text-slate-200 mb-1.5 line-clamp-2">
                  &ldquo;{item.prompt}&rdquo;
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400 leading-normal">
                  {item.description}
                </div>
              </div>

              <div className="mt-3 pt-2 border-t border-slate-200 dark:border-slate-800/60 flex items-center justify-end text-[10px] font-semibold text-indigo-600 dark:text-indigo-400 group-hover:text-indigo-700 dark:group-hover:text-indigo-300 gap-1">
                <span>Run Query</span>
                <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

