'use client';

import React from 'react';
import { AgentStepResponse, AgentExecutionTraceResponse } from '@/types/api';
import {
  Activity,
  Clock,
  Layers,
  BookOpen,
  CheckCircle2,
  AlertCircle,
  ShieldAlert,
  HelpCircle,
} from 'lucide-react';

interface ExecutionSummaryProps {
  status?: string;
  durationMs?: number;
  totalSteps?: number;
  steps?: AgentStepResponse[];
  usedRag?: boolean;
  citationCount?: number;
  trace?: AgentExecutionTraceResponse | null;
}

export function ExecutionSummary({
  status = 'completed',
  durationMs = 0,
  totalSteps = 0,
  steps = [],
  usedRag = false,
  citationCount = 0,
  trace,
}: ExecutionSummaryProps) {
  // Infer workers from executed tools
  const workersInvolved = new Set<string>();
  const effectiveSteps = steps.length > 0 ? steps : [];
  const effectiveDuration = durationMs || trace?.total_duration_ms || 0;
  const effectiveStepCount = totalSteps || steps.length || trace?.total_steps || 0;

  effectiveSteps.forEach((s) => {
    const t = s.tool_name.toLowerCase();
    if (t.includes('travel') || t.includes('expense')) {
      workersInvolved.add('Travel & Expense');
    } else if (t.includes('employee') || t.includes('leave')) {
      workersInvolved.add('Employee Records');
    } else if (t.includes('policy')) {
      workersInvolved.add('HR Policy');
    } else {
      workersInvolved.add('Domain Worker');
    }
  });

  const getStatusBadge = () => {
    switch (status) {
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.2 rounded-full text-[10px] font-medium bg-[#CFE5D6] dark:bg-[#2C3B32] text-[#2F855A] dark:text-[#34D399] border border-[#B7D9C2] dark:border-[#3A4D42]">
            <CheckCircle2 className="w-3 h-3 text-[#2F855A] dark:text-[#34D399]" />
            <span>Completed</span>
          </span>
        );
      case 'pending_approval':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.2 rounded-full text-[10px] font-medium bg-[#FEF3C7] dark:bg-[#393425] text-[#78350F] dark:text-[#FBBF24] border border-[#FDE68A] dark:border-[#4A462B]">
            <ShieldAlert className="w-3 h-3 text-[#B45309] dark:text-[#FBBF24]" />
            <span>Pending Approval</span>
          </span>
        );
      case 'approved':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.2 rounded-full text-[10px] font-medium bg-[#E5F5F1] dark:bg-[#1A2D2A] text-[#263142] dark:text-[#A9DED5] border border-[#C7E9E2] dark:border-[#244742]">
            <CheckCircle2 className="w-3 h-3 text-[#368F88] dark:text-[#A9DED5]" />
            <span>Approved &amp; Resumed</span>
          </span>
        );
      case 'rejected':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.2 rounded-full text-[10px] font-medium bg-[#FDE8E8] dark:bg-[#3D2525] text-[#9B1C1C] dark:text-[#F87171] border border-[#FBD5D5] dark:border-[#522828]">
            <AlertCircle className="w-3 h-3 text-[#C53030] dark:text-[#F87171]" />
            <span>Action Rejected</span>
          </span>
        );
      case 'max_steps_reached':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.2 rounded-full text-[10px] font-medium bg-[#FEF3C7] dark:bg-[#393425] text-[#78350F] dark:text-[#FBBF24] border border-[#FDE68A] dark:border-[#4A462B]">
            <AlertCircle className="w-3 h-3 text-[#B45309] dark:text-[#FBBF24]" />
            <span>Max Steps Budget</span>
          </span>
        );
      case 'clarification_needed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.2 rounded-full text-[10px] font-medium bg-[#DCE7F7] dark:bg-[#2B3A4E] text-[#2563EB] dark:text-[#60A5FA] border border-[#BFD5F2] dark:border-[#3D526D]">
            <HelpCircle className="w-3 h-3 text-[#2563EB] dark:text-[#60A5FA]" />
            <span>Clarification Needed</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.2 rounded-full text-[10px] font-medium bg-[#F8F6F2] dark:bg-[#1B1E24] text-[#697582] dark:text-[#9CA6B5] border border-[#E9E5DF] dark:border-[#2F3540]">
            <span>{status}</span>
          </span>
        );
    }
  };

  return (
    <div className="mt-4 pt-3 border-t border-[#E9E5DF] dark:border-[#2F3540] select-none">
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
        {/* Left Side: Status & Metric Chips */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5 text-[#697582] dark:text-[#9CA6B5] font-normal mr-1">
            <Activity className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5]" />
            <span>Execution Summary:</span>
          </div>

          {getStatusBadge()}

          {/* Duration */}
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-[#FFFFFF] dark:bg-[#21252D] border border-[#E9E5DF] dark:border-[#2F3540] text-[11px] text-[#263142] dark:text-[#EBEFF5] font-mono shadow-[0_1px_2px_rgba(38,49,66,0.02)]">
            <Clock className="w-3 h-3 text-[#368F88] dark:text-[#A9DED5]" />
            {effectiveDuration > 1000
              ? `${(effectiveDuration / 1000).toFixed(2)}s`
              : `${Math.round(effectiveDuration)}ms`}
          </span>

          {/* Step Count */}
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-[#FFFFFF] dark:bg-[#21252D] border border-[#E9E5DF] dark:border-[#2F3540] text-[11px] text-[#263142] dark:text-[#EBEFF5] shadow-[0_1px_2px_rgba(38,49,66,0.02)]">
            <Layers className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5]" />
            <span>{effectiveStepCount} {effectiveStepCount === 1 ? 'tool step' : 'tool steps'}</span>
          </span>

          {/* RAG status */}
          {usedRag && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-[#E5F5F1] dark:bg-[#1A2D2A] border border-[#C7E9E2] dark:border-[#244742] text-[11px] text-[#263142] dark:text-[#A9DED5]">
              <BookOpen className="w-3 h-3 text-[#368F88] dark:text-[#A9DED5]" />
              <span>RAG Policy ({citationCount} {citationCount === 1 ? 'source' : 'sources'})</span>
            </span>
          )}
        </div>

        {/* Right Side: Workers Tag */}
        {workersInvolved.size > 0 && (
          <div className="flex items-center gap-1.5 text-[11px] text-[#697582] dark:text-[#9CA6B5]">
            <span>Workers:</span>
            {Array.from(workersInvolved).map((worker) => (
              <span
                key={worker}
                className="px-1.5 py-0.2 rounded bg-[#F8F6F2] dark:bg-[#1B1E24] text-[#697582] dark:text-[#9CA6B5] border border-[#E9E5DF] dark:border-[#2F3540] font-normal"
              >
                {worker}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
