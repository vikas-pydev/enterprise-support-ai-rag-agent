'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { apiClient } from '@/lib/api/client';
import { HealthResponse } from '@/types/api';
import { Activity, RefreshCw, Terminal, X } from 'lucide-react';

export type StatusState = 'connecting' | 'online' | 'offline' | 'error';

interface BackendStatusBadgeProps {
  onStatusChange?: (status: StatusState, data?: HealthResponse | null) => void;
  className?: string;
}

export function BackendStatusBadge({ onStatusChange, className = '' }: BackendStatusBadgeProps) {
  const [status, setStatus] = useState<StatusState>('connecting');
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [showDiagnostics, setShowDiagnostics] = useState<boolean>(false);

  const checkHealth = useCallback(async () => {
    setIsRefreshing(true);
    const start = performance.now();
    try {
      const data = await apiClient.healthCheck();
      const elapsed = Math.round(performance.now() - start);
      setLatencyMs(elapsed);
      if (data && (data.status === 'healthy' || data.status === 'ok')) {
        setStatus('online');
        setHealthData(data);
        setErrorMessage(null);
        onStatusChange?.('online', data);
      } else {
        setStatus('error');
        setHealthData(data);
        setErrorMessage(data?.status || 'Unrecognized health payload');
        onStatusChange?.('error', data);
      }
    } catch (err: unknown) {
      const elapsed = Math.round(performance.now() - start);
      setLatencyMs(elapsed);
      setStatus('offline');
      setHealthData(null);
      const msg = err instanceof Error ? err.message : 'Backend unreachable';
      setErrorMessage(msg);
      onStatusChange?.('offline', null);
    } finally {
      setIsRefreshing(false);
    }
  }, [onStatusChange]);

  useEffect(() => {
    checkHealth();
    const timer = setInterval(checkHealth, 30000);
    return () => clearInterval(timer);
  }, [checkHealth]);

  return (
    <div className="relative inline-block">
      <div
        onClick={() => setShowDiagnostics(!showDiagnostics)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setShowDiagnostics(!showDiagnostics);
          }
        }}
        aria-label={`Backend status: ${status}. Click for diagnostics.`}
        className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-full border text-xs font-medium cursor-pointer transition-colors shadow-[0_1px_2px_rgba(38,49,66,0.03)] ${
          status === 'online'
            ? 'bg-[#E5F5F1] dark:bg-[#1A2D2A] border-[#C7E9E2] dark:border-[#244742] text-[#263142] dark:text-[#EBEFF5]'
            : status === 'connecting'
            ? 'bg-[#FEF3C7] dark:bg-[#393425] border-[#FDE68A] dark:border-[#4A462B] text-[#78350F] dark:text-[#FBBF24]'
            : status === 'error'
            ? 'bg-[#FDE8E8] dark:bg-[#3D2525] border-[#FBD5D5] dark:border-[#522828] text-[#9B1C1C] dark:text-[#F87171]'
            : 'bg-[#F8F6F2] dark:bg-[#282D37] border-[#E9E5DF] dark:border-[#2F3540] text-[#697582] dark:text-[#9CA6B5]'
        } ${className}`}
      >
        {/* Understated Status Dot */}
        <span className="relative flex h-2 w-2">
          {status === 'online' && (
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#368F88] opacity-60" />
          )}
          {status === 'connecting' && (
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#D97706] opacity-60" />
          )}
          <span
            className={`relative inline-flex rounded-full h-2 w-2 ${
              status === 'online'
                ? 'bg-[#368F88] dark:bg-[#45B3A9]'
                : status === 'connecting'
                ? 'bg-[#D97706]'
                : status === 'error'
                ? 'bg-[#DC2626]'
                : 'bg-[#9299A3]'
            }`}
          />
        </span>

        {/* Label */}
        <span className="flex items-center gap-1 text-[11px]">
          <span className="font-semibold text-[#263142] dark:text-[#EBEFF5]">Backend:</span>
          {status === 'connecting' && <span>Connecting...</span>}
          {status === 'online' && (
            <span className="flex items-center gap-1">
              <span>Online</span>
              {healthData?.version ? (
                <span className="font-mono text-[10px] text-[#697582] dark:text-[#9CA6B5]">
                  v{healthData.version}
                </span>
              ) : null}
              {latencyMs !== null && (
                <span className="font-mono text-[10px] text-[#9299A3] dark:text-[#6E7887]">
                  ({latencyMs}ms)
                </span>
              )}
            </span>
          )}
          {status === 'offline' && <span>Offline</span>}
          {status === 'error' && <span>Degraded</span>}
        </span>

        {/* Refresh trigger */}
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            checkHealth();
          }}
          disabled={isRefreshing}
          aria-label="Refresh Backend Status"
          className="text-[#9299A3] hover:text-[#263142] dark:hover:text-[#EBEFF5] transition-colors disabled:opacity-50 ml-0.5 cursor-pointer"
          title="Check Backend Health"
        >
          <RefreshCw className={`w-3 h-3 ${isRefreshing ? 'animate-spin text-[#368F88]' : ''}`} />
        </button>
      </div>

      {/* Diagnostics Popover */}
      {showDiagnostics && (
        <div className="absolute right-0 top-full mt-2 w-80 sm:w-96 p-4 rounded-2xl border border-[#E9E5DF] dark:border-[#2F3540] bg-[#FFFEFC] dark:bg-[#21252D] shadow-lg z-50 text-xs text-[#263142] dark:text-[#EBEFF5] animate-in fade-in duration-150">
          <div className="flex items-center justify-between pb-2 mb-3 border-b border-[#E9E5DF] dark:border-[#2F3540]">
            <span className="font-bold flex items-center gap-1.5 text-[#263142] dark:text-[#EBEFF5]">
              <Activity className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5]" />
              <span>Backend Diagnostics</span>
            </span>
            <button
              type="button"
              onClick={() => setShowDiagnostics(false)}
              className="text-[#9299A3] hover:text-[#263142] dark:hover:text-[#EBEFF5] p-1 rounded-md"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-2 text-[11px]">
            <div className="flex justify-between py-1 border-b border-[#E9E5DF]/60 dark:border-[#2F3540]/60">
              <span className="text-[#697582] dark:text-[#9CA6B5]">Service Status:</span>
              <span className="font-semibold capitalize text-[#263142] dark:text-[#EBEFF5]">{status}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#E9E5DF]/60 dark:border-[#2F3540]/60">
              <span className="text-[#697582] dark:text-[#9CA6B5]">API Base URL:</span>
              <span className="font-mono text-[#263142] dark:text-[#EBEFF5]">{apiClient.getBaseUrl()}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#E9E5DF]/60 dark:border-[#2F3540]/60">
              <span className="text-[#697582] dark:text-[#9CA6B5]">Health Probe:</span>
              <span className="font-mono text-[#263142] dark:text-[#EBEFF5]">GET /health</span>
            </div>
            {latencyMs !== null && (
              <div className="flex justify-between py-1 border-b border-[#E9E5DF]/60 dark:border-[#2F3540]/60">
                <span className="text-[#697582] dark:text-[#9CA6B5]">Latency:</span>
                <span className="font-mono text-[#263142] dark:text-[#EBEFF5]">{latencyMs} ms</span>
              </div>
            )}
          </div>

          {status === 'offline' && (
            <div className="mt-3 p-2.5 rounded-xl bg-[#F8F6F2] dark:bg-[#1B1E24] border border-[#E9E5DF] dark:border-[#2F3540] text-[#697582] dark:text-[#9CA6B5] space-y-1.5">
              <div className="font-bold flex items-center gap-1 text-[#263142] dark:text-[#EBEFF5]">
                <Terminal className="w-3 h-3 text-[#368F88]" />
                <span>How to start the backend:</span>
              </div>
              <pre className="p-1.5 rounded bg-[#263142] text-[#EBEFF5] font-mono text-[10px] overflow-x-auto select-all">
                uvicorn app.api.main:app --reload --port 8000
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
