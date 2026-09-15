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
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-500/30">
            <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
            <span>Completed</span>
          </span>
        );
      case 'pending_approval':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-500/30">
            <ShieldAlert className="w-3 h-3 text-amber-600 dark:text-amber-400" />
            <span>Pending Approval</span>
          </span>
        );
      case 'approved':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-cyan-100 dark:bg-cyan-950/80 text-cyan-800 dark:text-cyan-300 border border-cyan-300 dark:border-cyan-500/30">
            <CheckCircle2 className="w-3 h-3 text-cyan-600 dark:text-cyan-400" />
            <span>Approved &amp; Resumed</span>
          </span>
        );
      case 'rejected':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-100 dark:bg-rose-950/80 text-rose-800 dark:text-rose-300 border border-rose-300 dark:border-rose-500/30">
            <AlertCircle className="w-3 h-3 text-rose-600 dark:text-rose-400" />
            <span>Action Rejected</span>
          </span>
        );
      case 'max_steps_reached':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-500/30">
            <AlertCircle className="w-3 h-3 text-amber-600 dark:text-amber-400" />
            <span>Max Steps Budget</span>
          </span>
        );
      case 'clarification_needed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-100 dark:bg-blue-950/80 text-blue-800 dark:text-blue-300 border border-blue-300 dark:border-blue-500/30">
            <HelpCircle className="w-3 h-3 text-blue-600 dark:text-blue-400" />
            <span>Clarification Needed</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700">
            <span>{status}</span>
          </span>
        );
    }
  };

  return (
    <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-800/80">
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
        {/* Left Side: Status & Metric Chips */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400 font-medium mr-1">
            <Activity className="w-3.5 h-3.5 text-indigo-500 dark:text-indigo-400" />
            <span>Execution Summary:</span>
          </div>

          {getStatusBadge()}

          {/* Duration */}
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-[11px] text-slate-700 dark:text-slate-300 font-mono shadow-xs">
            <Clock className="w-3 h-3 text-cyan-600 dark:text-cyan-400" />
            {effectiveDuration > 1000
              ? `${(effectiveDuration / 1000).toFixed(2)}s`
              : `${Math.round(effectiveDuration)}ms`}
          </span>

          {/* Step Count */}
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-[11px] text-slate-700 dark:text-slate-300 shadow-xs">
            <Layers className="w-3 h-3 text-indigo-600 dark:text-indigo-400" />
            <span>{effectiveStepCount} {effectiveStepCount === 1 ? 'tool step' : 'tool steps'}</span>
          </span>

          {/* RAG status */}
          {usedRag && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-cyan-50 dark:bg-cyan-950/40 border border-cyan-200 dark:border-cyan-500/20 text-[11px] text-cyan-800 dark:text-cyan-300">
              <BookOpen className="w-3 h-3 text-cyan-600 dark:text-cyan-400" />
              <span>RAG Policy ({citationCount} {citationCount === 1 ? 'source' : 'sources'})</span>
            </span>
          )}
        </div>

        {/* Right Side: Workers Tag */}
        {workersInvolved.size > 0 && (
          <div className="flex items-center gap-1.5 text-[11px] text-slate-500 dark:text-slate-400">
            <span>Workers:</span>
            {Array.from(workersInvolved).map((worker) => (
              <span
                key={worker}
                className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800/80 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700/60 font-medium"
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

