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
      className={`mt-4 rounded-2xl border transition-colors overflow-hidden shadow-[0_1px_3px_rgba(38,49,66,0.03)] ${
        isPending
          ? 'bg-[#FEF3C7]/60 dark:bg-[#393425]/40 border-[#FDE68A] dark:border-[#4A462B] ring-1 ring-[#FDE68A]/50'
          : isApproved
          ? 'bg-[#CFE5D6]/50 dark:bg-[#2C3B32]/40 border-[#B7D9C2] dark:border-[#3A4D42]'
          : 'bg-[#FDE8E8]/50 dark:bg-[#3D2525]/40 border-[#FBD5D5] dark:border-[#522828]'
      }`}
    >
      {/* Header Banner */}
      <div className="px-5 py-3.5 flex items-center justify-between gap-3 border-b border-[#E9E5DF] dark:border-[#2F3540] bg-[#FCFAF7] dark:bg-[#1B1E24]">
        <div className="flex items-center gap-3">
          <div
            className={`p-2 rounded-xl border ${
              isPending
                ? 'bg-[#FEF3C7] dark:bg-[#393425] border-[#FDE68A] dark:border-[#4A462B] text-[#B45309] dark:text-[#FBBF24]'
                : isApproved
                ? 'bg-[#CFE5D6] dark:bg-[#2C3B32] border-[#B7D9C2] dark:border-[#3A4D42] text-[#2F855A] dark:text-[#34D399]'
                : 'bg-[#FDE8E8] dark:bg-[#3D2525] border-[#FBD5D5] dark:border-[#522828] text-[#9B1C1C] dark:text-[#F87171]'
            }`}
          >
            {isPending ? (
              <Lock className="w-4 h-4" />
            ) : isApproved ? (
              <CheckCircle2 className="w-4 h-4" />
            ) : (
              <XCircle className="w-4 h-4" />
            )}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-xs sm:text-sm font-semibold text-[#263142] dark:text-[#EBEFF5]">
                {isPending
                  ? 'Human Approval Required'
                  : isApproved
                  ? 'Operation Authorized by Operator'
                  : 'Operation Rejected by Operator'}
              </h4>
              <span
                className={`px-2 py-0.2 rounded-full text-[10px] font-semibold border ${
                  isPending
                    ? 'bg-[#FEF3C7] dark:bg-[#393425] text-[#78350F] dark:text-[#FBBF24] border-[#FDE68A] dark:border-[#4A462B]'
                    : isApproved
                    ? 'bg-[#CFE5D6] dark:bg-[#2C3B32] text-[#2F855A] dark:text-[#34D399] border-[#B7D9C2] dark:border-[#3A4D42]'
                    : 'bg-[#FDE8E8] dark:bg-[#3D2525] text-[#9B1C1C] dark:text-[#F87171] border-[#FBD5D5] dark:border-[#522828]'
                }`}
              >
                {isPending ? 'HITL Gated' : isApproved ? 'Approved' : 'Rejected'}
              </span>
            </div>
            <p className="text-[11px] text-[#697582] dark:text-[#9CA6B5] mt-0.5 font-normal">
              Deterministic LangGraph checkpoint gate for sensitive enterprise queries
            </p>
          </div>
        </div>

        {/* Approval ID */}
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#FFFFFF] dark:bg-[#21252D] border border-[#E9E5DF] dark:border-[#2F3540] text-[11px] font-mono text-[#263142] dark:text-[#EBEFF5]">
          <KeyRound className="w-3 h-3 text-[#B45309] dark:text-[#FBBF24]" />
          <span className="truncate max-w-[180px]">{approvalId}</span>
        </div>
      </div>

      {/* Body Content */}
      <div className="p-4 sm:p-5 space-y-3.5">
        {/* Reason Box */}
        <div className="p-3.5 rounded-xl bg-[#FFFFFF] dark:bg-[#21252D] border border-[#E9E5DF] dark:border-[#2F3540] text-xs space-y-1.5">
          <div className="flex items-center justify-between gap-2">
            <span className="font-semibold text-[#263142] dark:text-[#EBEFF5] flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-[#B45309] dark:text-[#FBBF24]" />
              <span>Policy Evaluation</span>
            </span>
            {targetWorker && (
              <span className="text-[11px] text-[#697582] dark:text-[#9CA6B5]">
                Target Worker: <strong className="text-[#263142] dark:text-[#EBEFF5] font-semibold">{targetWorker}</strong>
              </span>
            )}
          </div>
          <p className="text-[#263142] dark:text-[#EBEFF5] leading-relaxed font-normal">{reason}</p>
        </div>

        {/* Local Error */}
        {localError && (
          <div className="p-3 rounded-xl bg-[#FDE8E8] dark:bg-[#3D2525] border border-[#FBD5D5] dark:border-[#522828] text-xs text-[#9B1C1C] dark:text-[#F87171] flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-[#C53030] dark:text-[#F87171] flex-shrink-0" />
            <span>{localError}</span>
          </div>
        )}

        {/* Interactive Decision Form if Pending */}
        {isPending ? (
          <div className="space-y-3 pt-1">
            {/* Operator Notes */}
            <div>
              <label
                htmlFor={`approval-notes-${approvalId}`}
                className="block text-[11px] font-semibold text-[#263142] dark:text-[#EBEFF5] mb-1"
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
                className="w-full px-3.5 py-2 rounded-xl bg-[#FFFFFF] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540] focus:border-[#368F88] focus:ring-1 focus:ring-[#368F88] text-xs text-[#263142] dark:text-[#EBEFF5] placeholder-[#9299A3] dark:placeholder-[#6E7887] outline-none transition-colors disabled:opacity-50"
              />
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-3 pt-1">
              <button
                type="button"
                onClick={() => handleAction('approve')}
                disabled={Boolean(submittingDecision) || isLoading}
                className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-[#368F88] hover:bg-[#2B7771] text-white text-xs font-semibold transition-colors disabled:opacity-50 cursor-pointer shadow-[0_1px_2px_rgba(38,49,66,0.05)]"
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
                className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-[#FDE8E8] hover:bg-[#FBD5D5] dark:bg-[#3D2525] dark:hover:bg-[#4A2626] border border-[#FBD5D5] dark:border-[#522828] text-[#9B1C1C] dark:text-[#F87171] text-xs font-semibold transition-colors disabled:opacity-50 cursor-pointer"
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
          <div className="p-3 rounded-xl bg-[#FFFFFF] dark:bg-[#21252D] border border-[#E9E5DF] dark:border-[#2F3540] text-xs text-[#697582] dark:text-[#9CA6B5] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="w-3.5 h-3.5 text-[#9299A3] dark:text-[#6E7887]" />
              <span>
                Status:{' '}
                <strong className={isApproved ? 'text-[#2F855A] dark:text-[#34D399]' : 'text-[#9B1C1C] dark:text-[#F87171]'}>
                  {isApproved ? 'Authorized' : 'Rejected'}
                </strong>
                {approvalNotes && ` • Notes: "${approvalNotes}"`}
              </span>
            </div>
            <span className="text-[10px] font-mono text-[#9299A3] dark:text-[#6E7887]">
              Checkpoint Thread Resolved
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
