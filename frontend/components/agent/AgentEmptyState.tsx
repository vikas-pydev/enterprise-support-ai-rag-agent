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
  pastelIcon: string;
}

const DEMO_PROMPTS: ExampleCategory[] = [
  {
    title: 'Employee Profile',
    badge: 'SQL Records',
    icon: <UserCheck className="w-4 h-4 text-[#2563EB] dark:text-[#60A5FA]" />,
    pastelIcon: 'bg-[#DCE7F7] dark:bg-[#2B3A4E] border-[#BFD5F2] dark:border-[#3D526D]',
    prompt: "Show employee E1001's information.",
    description: 'Retrieve full name, job title, department, email, and manager info',
  },
  {
    title: 'Leave Balances',
    badge: 'SQL Balances',
    icon: <Calendar className="w-4 h-4 text-[#7C3AED] dark:text-[#A78BFA]" />,
    pastelIcon: 'bg-[#DCCEEF] dark:bg-[#39344D] border-[#CBB8E3] dark:border-[#4A4463]',
    prompt: 'How many annual leave days does E1001 have left?',
    description: 'Check remaining PTO, total allocated days, and category breakdown',
  },
  {
    title: 'Travel & Expenses',
    badge: 'SQL Expenses',
    icon: <Plane className="w-4 h-4 text-[#368F88] dark:text-[#A9DED5]" />,
    pastelIcon: 'bg-[#E5F5F1] dark:bg-[#1A2D2A] border-[#C7E9E2] dark:border-[#244742]',
    prompt: 'How much has E1001 spent on travel?',
    description: 'Analyze total claims, approved totals, and categorized expense rollups',
  },
  {
    title: 'Manager Hierarchy',
    badge: 'SQL Hierarchy',
    icon: <Users className="w-4 h-4 text-[#7C3AED] dark:text-[#A78BFA]" />,
    pastelIcon: 'bg-[#DCCEEF] dark:bg-[#39344D] border-[#CBB8E3] dark:border-[#4A4463]',
    prompt: "Who is E1001's manager?",
    description: 'Direct organizational manager lookup via employee records worker',
  },
  {
    title: 'Multi-Step Query',
    badge: 'Multi-Tool Flow',
    icon: <GitMerge className="w-4 h-4 text-[#2F855A] dark:text-[#34D399]" />,
    pastelIcon: 'bg-[#CFE5D6] dark:bg-[#2C3B32] border-[#B7D9C2] dark:border-[#3A4D42]',
    prompt: 'How much has E1001 spent on travel, and who is their manager?',
    description: 'Executes travel summary and manager lookup in sequential steps',
  },
  {
    title: 'Cross-Domain (SQL + RAG)',
    badge: 'Cross-Domain',
    icon: <Globe className="w-4 h-4 text-[#368F88] dark:text-[#A9DED5]" />,
    pastelIcon: 'bg-[#E5F5F1] dark:bg-[#1A2D2A] border-[#C7E9E2] dark:border-[#244742]',
    prompt: 'How much has E1001 spent on travel and what is the domestic meal allowance?',
    description: 'Combines PostgreSQL expense data with ChromaDB policy knowledge',
  },
  {
    title: 'Human-in-the-Loop Gate',
    badge: 'HITL Approval',
    icon: <ShieldAlert className="w-4 h-4 text-[#B45309] dark:text-[#FBBF24]" />,
    pastelIcon: 'bg-[#FEF3C7] dark:bg-[#393425] border-[#FDE68A] dark:border-[#4A462B]',
    prompt: 'Show confidential compensation details for employee E1000.',
    description: 'Triggers deterministic LangGraph authorization checkpoint for review',
  },
];

export function AgentEmptyState({ onSelectPrompt, disabled = false }: AgentEmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-6 px-2 sm:px-4 text-center max-w-4xl mx-auto space-y-6 select-none">
      {/* Top Banner */}
      <div className="flex flex-col items-center max-w-2xl space-y-2.5">
        <div className="p-3 rounded-2xl bg-[#DCCEEF] dark:bg-[#39344D] border border-[#CBB8E3] dark:border-[#4A4463] text-[#5A4384] dark:text-[#DCCEEF] shadow-[0_1px_2px_rgba(38,49,66,0.03)]">
          <Bot className="w-6 h-6" />
        </div>

        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-[#E5F5F1] dark:bg-[#1A2D2A] border border-[#C7E9E2] dark:border-[#244742] text-[#263142] dark:text-[#A9DED5] mb-2">
            <Sparkles className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5]" />
            <span>Autonomous Tool-Calling &amp; Supervisor Architecture</span>
          </div>
          <h3 className="text-lg sm:text-xl font-semibold text-[#263142] dark:text-[#EBEFF5] tracking-tight">
            Enterprise AI Agent Workspace
          </h3>
          <p className="mt-1.5 text-xs sm:text-sm text-[#697582] dark:text-[#9CA6B5] leading-relaxed font-normal">
            Ask the agent to retrieve employee records, evaluate leave balances, analyze travel claims, or orchestrate multi-step cross-domain workflows with verifiable evidence and human governance.
          </p>
        </div>
      </div>

      {/* Categorized Demo Queries Grid */}
      <div className="w-full text-left space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-[#697582] dark:text-[#9CA6B5]">
            Suggested Technical Demo Inquiries
          </span>
          <span className="text-[11px] text-[#9299A3] dark:text-[#6E7887] hidden sm:inline font-normal">
            Click any prompt to execute immediately
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">
          {DEMO_PROMPTS.map((item) => (
            <button
              key={item.title}
              type="button"
              disabled={disabled}
              onClick={() => onSelectPrompt(item.prompt)}
              className="text-left p-3.5 rounded-xl border border-[#E9E5DF] dark:border-[#2F3540] bg-[#FFFEFC] dark:bg-[#21252D] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] hover:border-[#A9DED5] dark:hover:border-[#368F88] transition-colors group flex flex-col justify-between disabled:opacity-50 cursor-pointer shadow-[0_1px_2px_rgba(38,49,66,0.02)]"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className={`p-1 rounded-lg border ${item.pastelIcon}`}>
                      {item.icon}
                    </div>
                    <span className="text-xs font-semibold text-[#263142] dark:text-[#EBEFF5] group-hover:text-[#368F88] dark:group-hover:text-[#A9DED5] transition-colors">
                      {item.title}
                    </span>
                  </div>
                  <span className="px-1.5 py-0.2 rounded text-[9px] font-mono font-medium bg-[#F8F6F2] dark:bg-[#1B1E24] text-[#697582] dark:text-[#9CA6B5] border border-[#E9E5DF] dark:border-[#2F3540]">
                    {item.badge}
                  </span>
                </div>

                <div className="text-xs font-medium text-[#263142] dark:text-[#EBEFF5] mb-1.5 line-clamp-2">
                  &ldquo;{item.prompt}&rdquo;
                </div>
                <div className="text-[11px] text-[#697582] dark:text-[#9CA6B5] leading-normal font-normal">
                  {item.description}
                </div>
              </div>

              <div className="mt-3 pt-2 border-t border-[#E9E5DF]/60 dark:border-[#2F3540]/60 flex items-center justify-end text-[10px] font-medium text-[#368F88] dark:text-[#A9DED5] group-hover:text-[#2B7771] gap-1">
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
