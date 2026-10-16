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

  const getWorkerPastelBadge = (workerName?: string, type?: string) => {
    if (type === 'supervisor') {
      return {
        icon: <Compass className="w-3.5 h-3.5" />,
        container: 'bg-[#DCCEEF] text-[#5A4384] border-[#CBB8E3] dark:bg-[#39344D] dark:text-[#DCCEEF] dark:border-[#4A4463]',
      };
    }
    if (type === 'approval') {
      return {
        icon: <ShieldAlert className="w-3.5 h-3.5" />,
        container: 'bg-[#FEF3C7] text-[#B45309] border-[#FDE68A] dark:bg-[#393425] dark:text-[#FBBF24] dark:border-[#4A462B]',
      };
    }
    if (type === 'synthesis') {
      return {
        icon: <Sparkles className="w-3.5 h-3.5" />,
        container: 'bg-[#CFE5D6] text-[#2F855A] border-[#B7D9C2] dark:bg-[#2C3B32] dark:text-[#34D399] dark:border-[#3A4D42]',
      };
    }

    if (workerName === 'Employee Records') {
      return {
        icon: <Database className="w-3.5 h-3.5" />,
        container: 'bg-[#DCE7F7] text-[#2563EB] border-[#BFD5F2] dark:bg-[#2B3A4E] dark:text-[#60A5FA] dark:border-[#3D526D]',
      };
    }
    if (workerName === 'Travel & Expense') {
      return {
        icon: <Plane className="w-3.5 h-3.5" />,
        container: 'bg-[#C7E9E2] text-[#368F88] border-[#A9DED5] dark:bg-[#1A2D2A] dark:text-[#A9DED5] dark:border-[#244742]',
      };
    }
    if (workerName === 'HR Policy') {
      return {
        icon: <BookOpen className="w-3.5 h-3.5" />,
        container: 'bg-[#DCCEEF] text-[#5A4384] border-[#CBB8E3] dark:bg-[#39344D] dark:text-[#DCCEEF] dark:border-[#4A4463]',
      };
    }
    return {
      icon: <GitBranch className="w-3.5 h-3.5" />,
      container: 'bg-[#F8F6F2] text-[#697582] border-[#E9E5DF] dark:bg-[#1B1E24] dark:text-[#9CA6B5] dark:border-[#2F3540]',
    };
  };

  return (
    <div className="mt-4 rounded-xl border border-[#E9E5DF] dark:border-[#2F3540] bg-[#F8F6F2] dark:bg-[#1B1E24] p-4 shadow-[0_1px_2px_rgba(38,49,66,0.02)] select-none">
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-[#368F88] dark:text-[#A9DED5]" />
          <h4 className="text-xs font-semibold text-[#263142] dark:text-[#EBEFF5] tracking-wide">
            Multi-Agent Execution Workflow
          </h4>
        </div>
        <span className="text-[10px] font-normal text-[#697582] dark:text-[#9CA6B5] font-mono">
          {toolCallCount} tool {toolCallCount === 1 ? 'call' : 'calls'} executed
        </span>
      </div>

      {/* Desktop Horizontal Flow */}
      <div className="hidden md:flex items-center gap-1.5 overflow-x-auto pb-2 pt-1 scrollbar-thin">
        {nodes.map((node, index) => {
          const isLast = index === nodes.length - 1;
          const { icon, container } = getWorkerPastelBadge(node.workerName, node.type);

          return (
            <React.Fragment key={node.id}>
              {/* Node Box */}
              <div className="flex flex-col items-center flex-shrink-0">
                <div
                  className={`px-3 py-2 rounded-xl border flex items-center gap-2 transition-colors bg-[#FFFEFC] dark:bg-[#21252D] border-[#E9E5DF] dark:border-[#2F3540] text-[#263142] dark:text-[#EBEFF5] shadow-[0_1px_2px_rgba(38,49,66,0.02)] ${
                    node.type === 'approval'
                      ? 'ring-1 ring-[#FDE68A] dark:ring-[#4A462B]'
                      : ''
                  }`}
                >
                  <div className={`p-1 rounded-lg border ${container}`}>
                    {icon}
                  </div>
                  <div className="text-left">
                    <div className="text-[11px] font-semibold tracking-tight text-[#263142] dark:text-[#EBEFF5] whitespace-nowrap">
                      {node.label}
                    </div>
                    {node.subLabel && (
                      <div className="text-[10px] text-[#697582] dark:text-[#9CA6B5] font-mono truncate max-w-[130px]">
                        {node.subLabel}
                      </div>
                    )}
                  </div>
                  {node.durationMs !== undefined && node.durationMs > 0 && (
                    <span className="text-[9px] font-mono text-[#9299A3] dark:text-[#6E7887] ml-1">
                      {Math.round(node.durationMs)}ms
                    </span>
                  )}
                </div>
              </div>

              {/* Connecting Arrow */}
              {!isLast && (
                <div className="flex items-center text-[#9299A3] dark:text-[#6E7887] flex-shrink-0 px-0.5">
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
          const { icon, container } = getWorkerPastelBadge(node.workerName, node.type);

          return (
            <div key={node.id} className="relative pl-6">
              {/* Vertical connecting line */}
              {!isLast && (
                <div className="absolute left-2.5 top-6 bottom-0 w-0.5 bg-[#E9E5DF] dark:bg-[#2F3540]" />
              )}

              {/* Step indicator dot */}
              <div className="absolute left-1 top-2.5 w-3.5 h-3.5 rounded-full bg-[#FFFEFC] dark:bg-[#21252D] border border-[#E9E5DF] dark:border-[#2F3540] flex items-center justify-center">
                <div
                  className={`w-1.5 h-1.5 rounded-full ${
                    node.status === 'error'
                      ? 'bg-rose-500'
                      : node.status === 'pending'
                      ? 'bg-amber-500'
                      : 'bg-[#368F88]'
                  }`}
                />
              </div>

              {/* Card */}
              <div className="p-2.5 rounded-xl border border-[#E9E5DF] dark:border-[#2F3540] bg-[#FFFEFC] dark:bg-[#21252D] flex items-center justify-between gap-2 shadow-[0_1px_2px_rgba(38,49,66,0.02)]">
                <div className="flex items-center gap-2 min-w-0">
                  <div className={`p-1 rounded-lg border flex-shrink-0 ${container}`}>
                    {icon}
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs font-semibold text-[#263142] dark:text-[#EBEFF5] truncate">
                      {node.label}
                    </div>
                    {node.subLabel && (
                      <div className="text-[10px] text-[#697582] dark:text-[#9CA6B5] font-mono truncate">
                        {node.subLabel}
                      </div>
                    )}
                  </div>
                </div>

                {node.durationMs !== undefined && node.durationMs > 0 && (
                  <span className="text-[10px] font-mono text-[#9299A3] dark:text-[#6E7887] flex-shrink-0">
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
