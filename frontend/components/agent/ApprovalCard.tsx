'use client';

import React, { useState } from 'react';
import {
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Loader2,
  Lock,
  KeyRound,
  FileText,
  AlertTriangle,
} from 'lucide-react';

interface ApprovalCardProps {
  approvalId: string;
  reason?: string | null;
  targetWorker?: string | null;
  approvalStatus?: 'pending' | 'approved' | 'rejected' | 'completed' | 'error' | string;
  approvalDecision?: string;
  approvalNotes?: string | null;
  onDecision: (approvalId: string, decision: 'approve' | 'reject', notes?: string) => Promise<void>;
  isLoading?: boolean;
}

export function ApprovalCard({
  approvalId,
  reason = 'This operation accesses sensitive enterprise records requiring operator authorization.',
  targetWorker = 'Employee Records',
  approvalStatus = 'pending',
  approvalDecision,
  approvalNotes,
  onDecision,
  isLoading = false,
}: ApprovalCardProps) {
  const [notes, setNotes] = useState<string>('');
  const [submittingDecision, setSubmittingDecision] = useState<'approve' | 'reject' | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  const isPending = approvalStatus === 'pending';
  const isApproved = approvalStatus === 'approved' || approvalDecision === 'approve';
  const isRejected = approvalStatus === 'rejected' || approvalDecision === 'reject';

  const handleAction = async (decision: 'approve' | 'reject') => {
    if (isLoading || submittingDecision) return;
    setLocalError(null);
    setSubmittingDecision(decision);

    try {
      await onDecision(approvalId, decision, notes.trim() || undefined);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setLocalError(msg);
    } finally {
      setSubmittingDecision(null);
    }
  };

  return (
    <div
      className={`mt-4 rounded-3xl border transition-all overflow-hidden shadow-lg ${
        isPending
          ? 'bg-amber-50/90 dark:bg-gradient-to-br dark:from-amber-950/40 dark:via-slate-900 dark:to-amber-950/30 border-amber-300 dark:border-amber-500/50 shadow-amber-950/10'
          : isApproved
          ? 'bg-emerald-50/90 dark:bg-gradient-to-br dark:from-emerald-950/40 dark:via-slate-900 dark:to-emerald-950/30 border-emerald-300 dark:border-emerald-500/40'
          : 'bg-rose-50/90 dark:bg-gradient-to-br dark:from-rose-950/40 dark:via-slate-900 dark:to-rose-950/30 border-rose-300 dark:border-rose-500/40'
      }`}
    >
      {/* Header Banner */}
      <div className="px-5 py-4 flex items-center justify-between gap-3 border-b border-slate-200 dark:border-slate-800/80">
        <div className="flex items-center gap-3">
          <div
            className={`p-2 rounded-2xl border ${
              isPending
                ? 'bg-amber-100 dark:bg-amber-500/10 border-amber-300 dark:border-amber-500/30 text-amber-700 dark:text-amber-400'
                : isApproved
                ? 'bg-emerald-100 dark:bg-emerald-500/10 border-emerald-300 dark:border-emerald-500/30 text-emerald-700 dark:text-emerald-400'
                : 'bg-rose-100 dark:bg-rose-500/10 border-rose-300 dark:border-rose-500/30 text-rose-700 dark:text-rose-400'
            }`}
          >
            {isPending ? (
              <Lock className="w-5 h-5" />
            ) : isApproved ? (
              <CheckCircle2 className="w-5 h-5" />
            ) : (
              <XCircle className="w-5 h-5" />
            )}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                {isPending
                  ? 'Human Approval Required'
                  : isApproved
                  ? 'Operation Authorized by Operator'
                  : 'Operation Rejected by Operator'}
              </h4>
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                  isPending
                    ? 'bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-500/30'
                    : isApproved
                    ? 'bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-500/30'
                    : 'bg-rose-100 dark:bg-rose-950/80 text-rose-800 dark:text-rose-300 border-rose-300 dark:border-rose-500/30'
                }`}
              >
                {isPending ? 'HITL Gated' : isApproved ? 'Approved' : 'Rejected'}
              </span>
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
              Deterministic LangGraph checkpoint gate for sensitive enterprise queries
            </p>
          </div>
        </div>

        {/* Approval ID */}
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-white dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800 text-[11px] font-mono text-slate-700 dark:text-slate-300">
          <KeyRound className="w-3 h-3 text-amber-600 dark:text-amber-400" />
          <span className="truncate max-w-[180px]">{approvalId}</span>
        </div>
      </div>

      {/* Body Content */}
      <div className="p-5 space-y-4">
        {/* Reason Box */}
        <div className="p-3.5 rounded-2xl bg-white/80 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800/90 text-xs space-y-2">
          <div className="flex items-center justify-between gap-2">
            <span className="font-bold text-slate-900 dark:text-slate-300 flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
              <span>Policy Evaluation</span>
            </span>
            {targetWorker && (
              <span className="text-[11px] text-slate-500 dark:text-slate-400">
                Target Worker: <strong className="text-slate-800 dark:text-slate-200">{targetWorker}</strong>
              </span>
            )}
          </div>
          <p className="text-slate-700 dark:text-slate-300 leading-relaxed font-sans">{reason}</p>
        </div>

        {/* Local Error */}
        {localError && (
          <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-500/30 text-xs text-rose-800 dark:text-rose-300 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 dark:text-rose-400 flex-shrink-0" />
            <span>{localError}</span>
          </div>
        )}

        {/* Interactive Decision Form if Pending */}
        {isPending ? (
          <div className="space-y-3 pt-2">
            {/* Operator Notes */}
            <div>
              <label
                htmlFor={`approval-notes-${approvalId}`}
                className="block text-[11px] font-bold text-slate-700 dark:text-slate-400 mb-1"
              >
                Operator Notes (Optional):
              </label>
              <input
                id={`approval-notes-${approvalId}`}
                type="text"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="e.g. Authorized by HR Operations Director"
                disabled={Boolean(submittingDecision) || isLoading}
                className="w-full px-3.5 py-2 rounded-2xl bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 focus:border-amber-500 focus:ring-1 focus:ring-amber-500 text-xs text-slate-900 dark:text-white placeholder-slate-400 outline-none transition-all disabled:opacity-50"
              />
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-3 pt-1">
              <button
                type="button"
                onClick={() => handleAction('approve')}
                disabled={Boolean(submittingDecision) || isLoading}
                className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-2xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-lg shadow-emerald-600/20 transition-all disabled:opacity-50 cursor-pointer"
              >
                {submittingDecision === 'approve' ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Authorizing &amp; Resuming...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Approve &amp; Continue</span>
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={() => handleAction('reject')}
                disabled={Boolean(submittingDecision) || isLoading}
                className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-2xl bg-rose-100 hover:bg-rose-200 dark:bg-rose-900/60 dark:hover:bg-rose-800/80 border border-rose-300 dark:border-rose-500/30 text-rose-800 dark:text-rose-200 text-xs font-bold transition-all disabled:opacity-50 cursor-pointer"
              >
                {submittingDecision === 'reject' ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Rejecting...</span>
                  </>
                ) : (
                  <>
                    <XCircle className="w-4 h-4" />
                    <span>Reject</span>
                  </>
                )}
              </button>
            </div>
          </div>
        ) : (
          /* Static Resolved View */
          <div className="p-3 rounded-2xl bg-white/80 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-400 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="w-3.5 h-3.5 text-slate-400" />
              <span>
                Status:{' '}
                <strong className={isApproved ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}>
                  {isApproved ? 'Authorized' : 'Rejected'}
                </strong>
                {approvalNotes && ` • Notes: "${approvalNotes}"`}
              </span>
            </div>
            <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500">
              Checkpoint Thread Resolved
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

