'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { apiClient } from '@/lib/api/client';
import { HealthResponse } from '@/types/api';
import { Activity, CheckCircle2, XCircle, AlertTriangle, RefreshCw, Terminal, X } from 'lucide-react';

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
      if (data && data.status === 'healthy') {
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
        className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-medium cursor-pointer transition-all ${
          status === 'online'
            ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-300 dark:border-emerald-500/30 text-emerald-800 dark:text-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.15)]'
            : status === 'connecting'
            ? 'bg-amber-50 dark:bg-amber-950/30 border-amber-300 dark:border-amber-500/30 text-amber-800 dark:text-amber-300'
            : status === 'error'
            ? 'bg-orange-50 dark:bg-orange-950/40 border-orange-300 dark:border-orange-500/30 text-orange-800 dark:text-orange-300'
            : 'bg-rose-50 dark:bg-rose-950/40 border-rose-300 dark:border-rose-500/30 text-rose-800 dark:text-rose-300 shadow-[0_0_12px_rgba(244,63,94,0.15)]'
        } ${className}`}
      >
        {/* Pulsing Dot */}
        <span className="relative flex h-2 w-2">
          {status === 'online' && (
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
          )}
          {status === 'connecting' && (
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
          )}
          <span
            className={`relative inline-flex rounded-full h-2 w-2 ${
              status === 'online'
                ? 'bg-emerald-500'
                : status === 'connecting'
                ? 'bg-amber-500'
                : status === 'error'
                ? 'bg-orange-500'
                : 'bg-rose-500'
            }`}
          />
        </span>

        {/* Label */}
        <span className="tracking-wide flex items-center gap-1">
          <span className="font-bold">Backend:</span>
          {status === 'connecting' && <span>Connecting...</span>}
          {status === 'online' && (
            <span>
              Online <span className="font-mono text-[11px] opacity-80">v{healthData?.version}</span>
              {latencyMs !== null && (
                <span className="font-mono text-[10px] ml-1 opacity-70">({latencyMs}ms)</span>
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
          className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors disabled:opacity-50 ml-0.5 cursor-pointer"
          title="Check Backend Health"
        >
          <RefreshCw className={`w-3 h-3 ${isRefreshing ? 'animate-spin text-cyan-500' : ''}`} />
        </button>
      </div>

      {/* Diagnostics Popover */}
      {showDiagnostics && (
        <div className="absolute right-0 top-full mt-2 w-80 sm:w-96 p-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-2xl z-50 text-xs text-slate-800 dark:text-slate-200 animate-in fade-in duration-150">
          <div className="flex items-center justify-between pb-2 mb-3 border-b border-slate-200 dark:border-slate-800">
            <span className="font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-cyan-500" />
              <span>Backend Diagnostics</span>
            </span>
            <button
              type="button"
              onClick={() => setShowDiagnostics(false)}
              className="text-slate-400 hover:text-slate-700 dark:hover:text-white p-1"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-2 text-[11px]">
            <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800/60">
              <span className="text-slate-500">Service Status:</span>
              <span className="font-bold capitalize">{status}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800/60">
              <span className="text-slate-500">API Base URL:</span>
              <span className="font-mono">{apiClient.getBaseUrl()}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800/60">
              <span className="text-slate-500">Health Probe:</span>
              <span className="font-mono">GET /health</span>
            </div>
            {latencyMs !== null && (
              <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800/60">
                <span className="text-slate-500">Latency:</span>
                <span className="font-mono">{latencyMs} ms</span>
              </div>
            )}
          </div>

          {status === 'offline' && (
            <div className="mt-3 p-2.5 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-500/30 text-amber-800 dark:text-amber-300 space-y-1.5">
              <div className="font-bold flex items-center gap-1">
                <Terminal className="w-3 h-3" />
                <span>How to start the backend:</span>
              </div>
              <pre className="p-1.5 rounded bg-slate-950 text-slate-200 font-mono text-[10px] overflow-x-auto select-all">
                uvicorn app.api.main:app --reload --port 8000
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

