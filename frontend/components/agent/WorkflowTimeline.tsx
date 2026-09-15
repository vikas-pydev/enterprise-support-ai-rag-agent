'use client';

import React from 'react';
import { AgentStepResponse } from '@/types/api';
import {
  Compass,
  Database,
  Plane,
  BookOpen,
  Sparkles,
  ArrowRight,
  ShieldAlert,
  GitBranch,
} from 'lucide-react';

interface WorkflowTimelineProps {
  steps: AgentStepResponse[];
  status?: string;
  isApprovalPending?: boolean;
}

interface WorkflowNode {
  id: string;
  type: 'supervisor' | 'worker_tool' | 'approval' | 'synthesis';
  label: string;
  subLabel?: string;
  toolName?: string;
  workerName?: string;
  status: 'success' | 'error' | 'pending' | 'duplicate';
  durationMs?: number;
}

export function WorkflowTimeline({
  steps,
  status = 'completed',
  isApprovalPending = false,
}: WorkflowTimelineProps) {
  if (!steps || steps.length === 0) {
    if (!isApprovalPending) return null;
  }

  const toolCallCount = steps.length;

  // Construct workflow nodes from execution steps
  const nodes: WorkflowNode[] = [];

  // 1. Initial Supervisor Router Node
  nodes.push({
    id: 'node-supervisor',
    type: 'supervisor',
    label: 'Supervisor Router',
    subLabel: 'Orchestrating domain workers',
    status: 'success',
  });

  // 2. Worker & Tool Execution Nodes
  steps.forEach((step, idx) => {
    const tool = step.tool_name.toLowerCase();
    let worker = 'Domain Worker';
    if (tool.includes('travel') || tool.includes('expense')) {
      worker = 'Travel & Expense';
    } else if (tool.includes('employee') || tool.includes('leave')) {
      worker = 'Employee Records';
    } else if (tool.includes('policy')) {
      worker = 'HR Policy';
    }

    let nodeStatus: 'success' | 'error' | 'duplicate' = 'success';
    if (step.status === 'error') {
      nodeStatus = 'error';
    } else if (step.status === 'rejected_duplicate') {
      nodeStatus = 'duplicate';
    }

    nodes.push({
      id: `node-step-${idx + 1}`,
      type: 'worker_tool',
      label: worker,
      subLabel: step.tool_name,
      toolName: step.tool_name,
      workerName: worker,
      status: nodeStatus,
      durationMs: step.duration_ms,
    });
  });

  // 3. Approval Node if pending
  if (isApprovalPending || status === 'pending_approval') {
    nodes.push({
      id: 'node-approval',
      type: 'approval',
      label: 'Human Authorization',
      subLabel: 'Awaiting operator approval',
      status: 'pending',
    });
  }

  // 4. Final Synthesis Node
  nodes.push({
    id: 'node-synthesis',
    type: 'synthesis',
    label: 'Final Synthesis',
    subLabel: status === 'rejected' ? 'Action rejected' : 'Synthesizing evidence',
    status: status === 'error' ? 'error' : 'success',
  });

  const getWorkerIcon = (workerName?: string, type?: string) => {
    if (type === 'supervisor') {
      return <Compass className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />;
    }
    if (type === 'approval') {
      return <ShieldAlert className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />;
    }
    if (type === 'synthesis') {
      return <Sparkles className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />;
    }

    if (workerName === 'Employee Records') {
      return <Database className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />;
    }
    if (workerName === 'Travel & Expense') {
      return <Plane className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />;
    }
    if (workerName === 'HR Policy') {
      return <BookOpen className="w-3.5 h-3.5 text-violet-600 dark:text-violet-400" />;
    }
    return <GitBranch className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />;
  };

  return (
    <div className="mt-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-950/70 p-4 shadow-sm">
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
          <h4 className="text-xs font-bold text-slate-900 dark:text-white tracking-wide">
            Multi-Agent Execution Workflow
          </h4>
        </div>
        <span className="text-[10px] font-medium text-slate-500 dark:text-slate-400">
          {toolCallCount} tool {toolCallCount === 1 ? 'call' : 'calls'} executed
        </span>
      </div>

      {/* Desktop Horizontal Flow / Mobile Vertical Timeline */}
      <div className="hidden md:flex items-center gap-2 overflow-x-auto pb-2 pt-1 scrollbar-thin">
        {nodes.map((node, index) => {
          const isLast = index === nodes.length - 1;

          return (
            <React.Fragment key={node.id}>
              {/* Node Box */}
              <div className="flex flex-col items-center flex-shrink-0">
                <div
                  className={`px-3 py-2 rounded-2xl border flex items-center gap-2 transition-all shadow-sm ${
                    node.type === 'supervisor'
                      ? 'bg-indigo-50 dark:bg-indigo-950/40 border-indigo-200 dark:border-indigo-500/40 text-indigo-900 dark:text-indigo-200'
                      : node.type === 'approval'
                      ? 'bg-amber-50 dark:bg-amber-950/50 border-amber-300 dark:border-amber-500/50 text-amber-900 dark:text-amber-200 shadow-[0_0_12px_rgba(245,158,11,0.2)]'
                      : node.type === 'synthesis'
                      ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-500/40 text-emerald-900 dark:text-emerald-200'
                      : node.status === 'error'
                      ? 'bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-500/40 text-rose-900 dark:text-rose-200'
                      : 'bg-white dark:bg-slate-900/90 border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200'
                  }`}
                >
                  <div className="p-1 rounded-xl bg-white dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800">
                    {getWorkerIcon(node.workerName, node.type)}
                  </div>
                  <div className="text-left">
                    <div className="text-[11px] font-bold tracking-tight text-slate-900 dark:text-white whitespace-nowrap">
                      {node.label}
                    </div>
                    {node.subLabel && (
                      <div className="text-[10px] text-slate-500 dark:text-slate-400 font-mono truncate max-w-[130px]">
                        {node.subLabel}
                      </div>
                    )}
                  </div>
                  {node.durationMs !== undefined && node.durationMs > 0 && (
                    <span className="text-[9px] font-mono text-slate-400 ml-1">
                      {Math.round(node.durationMs)}ms
                    </span>
                  )}
                </div>
              </div>

              {/* Connecting Arrow */}
              {!isLast && (
                <div className="flex items-center text-slate-400 dark:text-slate-600 flex-shrink-0 px-0.5">
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Mobile Vertical Timeline */}
      <div className="md:hidden space-y-2 pt-1">
        {nodes.map((node, index) => {
          const isLast = index === nodes.length - 1;

          return (
            <div key={node.id} className="relative pl-6">
              {/* Vertical connecting line */}
              {!isLast && (
                <div className="absolute left-2.5 top-6 bottom-0 w-0.5 bg-slate-200 dark:bg-slate-800" />
              )}

              {/* Step indicator dot */}
              <div className="absolute left-1 top-2.5 w-3.5 h-3.5 rounded-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 flex items-center justify-center">
                <div
                  className={`w-1.5 h-1.5 rounded-full ${
                    node.status === 'error'
                      ? 'bg-rose-500'
                      : node.status === 'pending'
                      ? 'bg-amber-500'
                      : 'bg-indigo-500'
                  }`}
                />
              </div>

              {/* Card */}
              <div
                className={`p-2.5 rounded-2xl border flex items-center justify-between gap-2 shadow-sm ${
                  node.type === 'supervisor'
                    ? 'bg-indigo-50 dark:bg-indigo-950/30 border-indigo-200 dark:border-indigo-500/30'
                    : node.type === 'approval'
                    ? 'bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-500/40'
                    : node.type === 'synthesis'
                    ? 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-500/30'
                    : node.status === 'error'
                    ? 'bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-500/30'
                    : 'bg-white dark:bg-slate-900/80 border-slate-200 dark:border-slate-800'
                }`}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <div className="p-1 rounded-xl bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 flex-shrink-0">
                    {getWorkerIcon(node.workerName, node.type)}
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs font-bold text-slate-900 dark:text-white truncate">
                      {node.label}
                    </div>
                    {node.subLabel && (
                      <div className="text-[10px] text-slate-500 dark:text-slate-400 font-mono truncate">
                        {node.subLabel}
                      </div>
                    )}
                  </div>
                </div>

                {node.durationMs !== undefined && node.durationMs > 0 && (
                  <span className="text-[10px] font-mono text-slate-400 flex-shrink-0">
                    {Math.round(node.durationMs)}ms
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

