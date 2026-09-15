'use client';

import React, { useState } from 'react';
import { AgentStepResponse } from '@/types/api';
import {
  Wrench,
  ChevronDown,
  ChevronRight,
  Clock,
  CheckCircle2,
  AlertCircle,
  Code2,
  Database,
  Plane,
  BookOpen,
  HelpCircle,
  Copy,
  Check,
} from 'lucide-react';

interface ToolActivityProps {
  steps: AgentStepResponse[];
}

export function ToolActivity({ steps }: ToolActivityProps) {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [expandedStepIndex, setExpandedStepIndex] = useState<number | null>(null);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  if (!steps || steps.length === 0) return null;

  const toggleStep = (idx: number) => {
    setExpandedStepIndex(expandedStepIndex === idx ? null : idx);
  };

  const copyOutput = async (idx: number, content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedIndex(idx);
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch {
      setCopiedIndex(null);
    }
  };

  const getWorkerBadge = (toolName: string) => {
    const t = toolName.toLowerCase();
    if (t.includes('travel') || t.includes('expense')) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-cyan-100 dark:bg-cyan-950/80 text-cyan-700 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-500/30">
          <Plane className="w-2.5 h-2.5" /> Travel &amp; Expense
        </span>
      );
    }
    if (t.includes('employee') || t.includes('leave')) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-100 dark:bg-blue-950/80 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-500/30">
          <Database className="w-2.5 h-2.5" /> Employee Records
        </span>
      );
    }
    if (t.includes('policy')) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-violet-100 dark:bg-violet-950/80 text-violet-700 dark:text-violet-300 border border-violet-200 dark:border-violet-500/30">
          <BookOpen className="w-2.5 h-2.5" /> HR Policy
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
        Worker
      </span>
    );
  };

  return (
    <div className="mt-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-950/70 overflow-hidden shadow-sm">
      {/* Collapsible Accordion Header */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        className="w-full px-4 py-3 flex items-center justify-between gap-3 bg-slate-100/60 dark:bg-slate-900/50 hover:bg-slate-200/60 dark:hover:bg-slate-900/80 transition-colors text-left cursor-pointer"
      >
        <div className="flex items-center gap-2">
          <Wrench className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
          <span className="text-xs font-bold text-slate-900 dark:text-white">
            Tool Activity ({steps.length} {steps.length === 1 ? 'call' : 'calls'})
          </span>
          <span className="text-[10px] text-slate-500 dark:text-slate-400">
            &bull; Structured parameters &amp; observations
          </span>
        </div>

        <div className="flex items-center gap-2">
          {isOpen ? (
            <ChevronDown className="w-4 h-4 text-slate-500 dark:text-slate-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-slate-500 dark:text-slate-400" />
          )}
        </div>
      </button>

      {/* Accordion Body */}
      {isOpen && (
        <div className="p-4 space-y-3 border-t border-slate-200 dark:border-slate-800/80 animate-in fade-in duration-150">
          {steps.map((step, idx) => {
            const isStepExpanded = expandedStepIndex === idx;
            const hasArgs = step.tool_args && Object.keys(step.tool_args).length > 0;
            const outputStr = JSON.stringify(step.tool_result, null, 2);

            return (
              <div
                key={`${step.tool_name}-${step.step_number || idx}`}
                className="rounded-2xl border border-slate-200 dark:border-slate-800/90 bg-white dark:bg-slate-900/60 overflow-hidden shadow-sm"
              >
                {/* Step Header */}
                <div
                  onClick={() => toggleStep(idx)}
                  className="px-3.5 py-2.5 flex items-center justify-between gap-3 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-900/90 transition-colors"
                >
                  <div className="flex items-center gap-2 min-w-0 flex-wrap">
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                      #{step.step_number || idx + 1}
                    </span>

                    <span className="font-mono text-xs font-bold text-slate-900 dark:text-white">
                      {step.tool_name}
                    </span>

                    {getWorkerBadge(step.tool_name)}

                    {step.status === 'success' ? (
                      <span className="inline-flex items-center gap-1 text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold">
                        <CheckCircle2 className="w-3 h-3" /> Success
                      </span>
                    ) : step.status === 'rejected_duplicate' ? (
                      <span className="inline-flex items-center gap-1 text-[10px] text-amber-600 dark:text-amber-400 font-semibold">
                        <HelpCircle className="w-3 h-3" /> Cached Duplicate
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[10px] text-rose-600 dark:text-rose-400 font-semibold">
                        <AlertCircle className="w-3 h-3" /> Error
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="inline-flex items-center gap-1 text-[10px] font-mono text-slate-500 dark:text-slate-400">
                      <Clock className="w-3 h-3 text-cyan-600 dark:text-cyan-400" />
                      {Math.round(step.duration_ms)}ms
                    </span>
                    {isStepExpanded ? (
                      <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                    ) : (
                      <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                    )}
                  </div>
                </div>

                {/* Step Details Collapsible */}
                {isStepExpanded && (
                  <div className="p-3.5 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/80 space-y-3 text-xs">
                    {/* Error Banner if any */}
                    {step.error && (
                      <div className="p-2.5 rounded-xl bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-500/30 text-rose-800 dark:text-rose-200 text-xs">
                        <span className="font-bold">Tool Error:</span> {step.error}
                      </div>
                    )}

                    {/* Arguments */}
                    {hasArgs && (
                      <div>
                        <div className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 mb-1 flex items-center gap-1">
                          <Code2 className="w-3 h-3 text-indigo-600 dark:text-indigo-400" />
                          <span>Input Arguments</span>
                        </div>
                        <pre className="p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 font-mono text-[11px] text-slate-800 dark:text-slate-300 overflow-x-auto">
                          {JSON.stringify(step.tool_args, null, 2)}
                        </pre>
                      </div>
                    )}

                    {/* Result Observation */}
                    <div>
                      <div className="flex items-center justify-between text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 mb-1">
                        <div className="flex items-center gap-1">
                          <Database className="w-3 h-3 text-cyan-600 dark:text-cyan-400" />
                          <span>Observation Result</span>
                        </div>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            copyOutput(idx, outputStr);
                          }}
                          className="flex items-center gap-1 text-[10px] text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white capitalize cursor-pointer font-medium"
                        >
                          {copiedIndex === idx ? (
                            <>
                              <Check className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                              <span className="text-emerald-600 dark:text-emerald-400 font-semibold">Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3 h-3" />
                              <span>Copy JSON</span>
                            </>
                          )}
                        </button>
                      </div>
                      <pre className="p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 font-mono text-[11px] text-slate-800 dark:text-slate-300 max-h-48 overflow-y-auto overflow-x-auto scrollbar-thin">
                        {outputStr}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

