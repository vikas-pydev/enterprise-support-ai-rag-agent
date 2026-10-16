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
        <span className="inline-flex items-center gap-1 px-2 py-0.2 rounded-full text-[10px] font-medium bg-[#E5F5F1] dark:bg-[#1A2D2A] text-[#263142] dark:text-[#A9DED5] border border-[#C7E9E2] dark:border-[#244742]">
          <Plane className="w-2.5 h-2.5" /> Travel &amp; Expense
        </span>
      );
    }
    if (t.includes('employee') || t.includes('leave')) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.2 rounded-full text-[10px] font-medium bg-[#DCE7F7] dark:bg-[#2B3A4E] text-[#2563EB] dark:text-[#60A5FA] border border-[#BFD5F2] dark:border-[#3D526D]">
          <Database className="w-2.5 h-2.5" /> Employee Records
        </span>
      );
    }
    if (t.includes('policy')) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.2 rounded-full text-[10px] font-medium bg-[#DCCEEF] dark:bg-[#39344D] text-[#5A4384] dark:text-[#DCCEEF] border border-[#CBB8E3] dark:border-[#4A4463]">
          <BookOpen className="w-2.5 h-2.5" /> HR Policy
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.2 rounded-full text-[10px] font-medium bg-[#F8F6F2] dark:bg-[#1B1E24] text-[#697582] dark:text-[#9CA6B5] border border-[#E9E5DF] dark:border-[#2F3540]">
        Worker
      </span>
    );
  };

  return (
    <div className="mt-4 rounded-xl border border-[#E9E5DF] dark:border-[#2F3540] bg-[#F8F6F2] dark:bg-[#1B1E24] overflow-hidden shadow-[0_1px_2px_rgba(38,49,66,0.02)]">
      {/* Collapsible Accordion Header */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        className="w-full px-4 py-3 flex items-center justify-between gap-3 bg-[#FCFAF7] dark:bg-[#1B1E24] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] transition-colors text-left cursor-pointer"
      >
        <div className="flex items-center gap-2">
          <Wrench className="w-4 h-4 text-[#368F88] dark:text-[#A9DED5]" />
          <span className="text-xs font-semibold text-[#263142] dark:text-[#EBEFF5]">
            Tool Activity ({steps.length} {steps.length === 1 ? 'call' : 'calls'})
          </span>
          <span className="text-[10px] text-[#697582] dark:text-[#9CA6B5]">
            &bull; Structured parameters &amp; observations
          </span>
        </div>

        <div className="flex items-center gap-2">
          {isOpen ? (
            <ChevronDown className="w-4 h-4 text-[#9299A3] dark:text-[#6E7887]" />
          ) : (
            <ChevronRight className="w-4 h-4 text-[#9299A3] dark:text-[#6E7887]" />
          )}
        </div>
      </button>

      {/* Accordion Body */}
      {isOpen && (
        <div className="p-3.5 space-y-2.5 border-t border-[#E9E5DF] dark:border-[#2F3540] animate-in fade-in duration-150">
          {steps.map((step, idx) => {
            const isStepExpanded = expandedStepIndex === idx;
            const hasArgs = step.tool_args && Object.keys(step.tool_args).length > 0;
            const outputStr = JSON.stringify(step.tool_result, null, 2);

            return (
              <div
                key={`${step.tool_name}-${step.step_number || idx}`}
                className="rounded-xl border border-[#E9E5DF] dark:border-[#2F3540] bg-[#FFFEFC] dark:bg-[#21252D] overflow-hidden shadow-[0_1px_2px_rgba(38,49,66,0.02)]"
              >
                {/* Step Header */}
                <div
                  onClick={() => toggleStep(idx)}
                  className="px-3.5 py-2.5 flex items-center justify-between gap-3 cursor-pointer hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] transition-colors"
                >
                  <div className="flex items-center gap-2 min-w-0 flex-wrap">
                    <span className="px-1.5 py-0.2 rounded text-[10px] font-mono font-medium bg-[#F8F6F2] dark:bg-[#1B1E24] text-[#697582] dark:text-[#9CA6B5] border border-[#E9E5DF] dark:border-[#2F3540]">
                      #{step.step_number || idx + 1}
                    </span>

                    <span className="font-mono text-xs font-semibold text-[#263142] dark:text-[#EBEFF5]">
                      {step.tool_name}
                    </span>

                    {getWorkerBadge(step.tool_name)}

                    {step.status === 'success' ? (
                      <span className="inline-flex items-center gap-1 text-[10px] text-[#2F855A] dark:text-[#34D399] font-medium">
                        <CheckCircle2 className="w-3 h-3" /> Success
                      </span>
                    ) : step.status === 'rejected_duplicate' ? (
                      <span className="inline-flex items-center gap-1 text-[10px] text-[#B45309] dark:text-[#FBBF24] font-medium">
                        <HelpCircle className="w-3 h-3" /> Cached Duplicate
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[10px] text-[#C53030] dark:text-[#F87171] font-medium">
                        <AlertCircle className="w-3 h-3" /> Error
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="inline-flex items-center gap-1 text-[10px] font-mono text-[#697582] dark:text-[#9CA6B5]">
                      <Clock className="w-3 h-3 text-[#368F88] dark:text-[#A9DED5]" />
                      {Math.round(step.duration_ms)}ms
                    </span>
                    {isStepExpanded ? (
                      <ChevronDown className="w-3.5 h-3.5 text-[#9299A3] dark:text-[#6E7887]" />
                    ) : (
                      <ChevronRight className="w-3.5 h-3.5 text-[#9299A3] dark:text-[#6E7887]" />
                    )}
                  </div>
                </div>

                {/* Step Details Collapsible */}
                {isStepExpanded && (
                  <div className="p-3.5 border-t border-[#E9E5DF] dark:border-[#2F3540] bg-[#FCFAF7] dark:bg-[#1B1E24] space-y-3 text-xs">
                    {/* Error Banner if any */}
                    {step.error && (
                      <div className="p-2.5 rounded-lg bg-[#FDE8E8] dark:bg-[#3D2525] border border-[#FBD5D5] dark:border-[#522828] text-[#9B1C1C] dark:text-[#F87171] text-xs">
                        <span className="font-semibold">Tool Error:</span> {step.error}
                      </div>
                    )}

                    {/* Arguments */}
                    {hasArgs && (
                      <div>
                        <div className="text-[10px] uppercase font-semibold text-[#697582] dark:text-[#9CA6B5] mb-1 flex items-center gap-1">
                          <Code2 className="w-3 h-3 text-[#368F88] dark:text-[#A9DED5]" />
                          <span>Input Arguments</span>
                        </div>
                        <pre className="p-2.5 rounded-lg bg-[#FFFFFF] dark:bg-[#21252D] border border-[#E9E5DF] dark:border-[#2F3540] font-mono text-[11px] text-[#263142] dark:text-[#EBEFF5] overflow-x-auto">
                          {JSON.stringify(step.tool_args, null, 2)}
                        </pre>
                      </div>
                    )}

                    {/* Result Observation */}
                    <div>
                      <div className="flex items-center justify-between text-[10px] uppercase font-semibold text-[#697582] dark:text-[#9CA6B5] mb-1">
                        <div className="flex items-center gap-1">
                          <Database className="w-3 h-3 text-[#368F88] dark:text-[#A9DED5]" />
                          <span>Observation Result</span>
                        </div>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            copyOutput(idx, outputStr);
                          }}
                          className="flex items-center gap-1 text-[10px] text-[#697582] hover:text-[#263142] dark:text-[#9CA6B5] dark:hover:text-[#EBEFF5] cursor-pointer font-medium"
                        >
                          {copiedIndex === idx ? (
                            <>
                              <Check className="w-3 h-3 text-[#2F855A] dark:text-[#34D399]" />
                              <span className="text-[#2F855A] dark:text-[#34D399] font-medium">Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3 h-3" />
                              <span>Copy JSON</span>
                            </>
                          )}
                        </button>
                      </div>
                      <pre className="p-2.5 rounded-lg bg-[#FFFFFF] dark:bg-[#21252D] border border-[#E9E5DF] dark:border-[#2F3540] font-mono text-[11px] text-[#263142] dark:text-[#EBEFF5] max-h-48 overflow-y-auto overflow-x-auto scrollbar-thin">
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
