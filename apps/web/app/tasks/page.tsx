'use client';

import { useEffect, useState } from 'react';
import {
  AlertCircle,
  Bot,
  CheckCircle2,
  Clock,
  ExternalLink,
  Filter,
  RefreshCcw,
  Terminal,
  X,
} from 'lucide-react';
import { StatusBadge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { Panel } from '@/components/ui/stat-card';
import {
  formatDate,
  getExecution,
  listExecutions,
  type AgentExecutionRead,
  DEFAULT_WORKSPACE_ID,
} from '@/lib/api';

export default function TasksPage() {
  const [executions, setExecutions] = useState<AgentExecutionRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedExecution, setSelectedExecution] = useState<AgentExecutionRead | null>(null);
  const [filter, setFilter] = useState<'all' | 'completed' | 'failed' | 'running'>('all');

  async function loadExecutions() {
    try {
      setLoading(true);
      setError(null);
      const data = await listExecutions(DEFAULT_WORKSPACE_ID);
      setExecutions(data);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unable to load execution history.';
      if (msg.toLowerCase().includes('authentication')) {
        setError(
          'Authentication required. Please click "Quick Demo Login" in the top navigation bar.'
        );
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadExecutions();

    const handleAuthChange = () => {
      void loadExecutions();
    };

    window.addEventListener('helios-auth-change', handleAuthChange);
    return () => {
      window.removeEventListener('helios-auth-change', handleAuthChange);
    };
  }, []);

  async function handleSelectExecution(id: number) {
    try {
      const details = await getExecution(id, DEFAULT_WORKSPACE_ID);
      setSelectedExecution(details);
    } catch {
      const item = executions.find((e) => e.id === id);
      if (item) setSelectedExecution(item);
    }
  }

  const filtered = executions.filter((item) => {
    if (filter === 'all') return true;
    const s = item.status.toLowerCase();
    if (filter === 'completed') return s.includes('completed') || s === 'success';
    if (filter === 'failed') return s.includes('failed') || s === 'error';
    if (filter === 'running') return s.includes('running') || s.includes('pending') || s.includes('queued');
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-200/80 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Tasks</h1>
          <p className="mt-1 text-sm text-slate-500">
            Track and audit business tasks executed across your AI workforce.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            id="refresh-executions-btn"
            variant="secondary"
            size="sm"
            onClick={loadExecutions}
          >
            <RefreshCcw size={13} />
            Refresh
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs font-medium text-rose-700">
          {error}
        </div>
      )}

      {/* Main Table Panel */}
      <Panel
        title="Execution Log"
        description="Comprehensive audit trail of AI agent actions and telemetry"
        action={
          <div className="flex items-center gap-1 rounded-lg border border-slate-200 bg-white p-1 text-xs shadow-xs">
            {(['all', 'running', 'completed', 'failed'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`rounded px-2.5 py-1 capitalize font-medium transition-colors ${
                  filter === f
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        }
      >
        {loading ? (
          <div className="space-y-3 py-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-12 animate-pulse rounded-lg bg-slate-100" />
            ))}
          </div>
        ) : filtered.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-100 text-slate-400 font-medium">
                  <th className="py-2.5 px-3">Task / Run</th>
                  <th className="py-2.5 px-3">AI Employee</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Duration</th>
                  <th className="py-2.5 px-3">Started</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {filtered.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => handleSelectExecution(item.id)}
                    className="hover:bg-slate-50/70 transition-colors cursor-pointer group"
                  >
                    <td className="py-3 px-3 font-medium text-slate-900">
                      <div className="flex items-center gap-2">
                        <Terminal size={14} className="text-slate-400 group-hover:text-blue-600 transition-colors" />
                        <span>Execution #{item.id}</span>
                      </div>
                    </td>
                    <td className="py-3 px-3 text-slate-600">
                      <span className="inline-flex items-center gap-1.5">
                        <Bot size={13} className="text-slate-400" />
                        Agent #{item.agent_id}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <StatusBadge status={item.status} />
                    </td>
                    <td className="py-3 px-3 text-slate-500">
                      {item.duration_ms !== null && item.duration_ms !== undefined
                        ? `${item.duration_ms} ms`
                        : '—'}
                    </td>
                    <td className="py-3 px-3 text-slate-500">
                      <span className="inline-flex items-center gap-1">
                        <Clock size={12} className="text-slate-400" />
                        {formatDate(item.started_at)}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-right">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSelectExecution(item.id);
                        }}
                        className="text-xs h-7 px-2.5"
                      >
                        View
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title={`No ${filter !== 'all' ? filter : ''} tasks found`}
            description="Tasks and autonomous agent runs will appear here as work is dispatched."
          />
        )}
      </Panel>

      {/* Task Details Slide-Over Drawer / Modal */}
      {selectedExecution && (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-slate-900/30 backdrop-blur-xs">
          <div className="h-full w-full max-w-md bg-white shadow-2xl border-l border-slate-200 flex flex-col justify-between">
            <div>
              {/* Drawer Header */}
              <div className="flex items-center justify-between border-b border-slate-100 p-5">
                <div className="flex items-center gap-2">
                  <Terminal size={18} className="text-blue-600" />
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900">
                      Execution #{selectedExecution.id}
                    </h3>
                    <p className="text-[11px] text-slate-400">Run Telemetry & Audit Detail</p>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedExecution(null)}
                  className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                >
                  <X size={16} />
                </button>
              </div>

              {/* Drawer Content */}
              <div className="p-5 space-y-4 text-xs text-slate-600">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                  <span className="font-medium text-slate-700">Status</span>
                  <StatusBadge status={selectedExecution.status} />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-lg border border-slate-200/80 bg-slate-50 p-3">
                    <span className="text-[10px] uppercase font-semibold text-slate-400">Agent</span>
                    <div className="mt-1 font-semibold text-slate-900">
                      Agent #{selectedExecution.agent_id}
                    </div>
                  </div>
                  <div className="rounded-lg border border-slate-200/80 bg-slate-50 p-3">
                    <span className="text-[10px] uppercase font-semibold text-slate-400">Workspace</span>
                    <div className="mt-1 font-semibold text-slate-900">
                      #{selectedExecution.workspace_id}
                    </div>
                  </div>
                  <div className="rounded-lg border border-slate-200/80 bg-slate-50 p-3">
                    <span className="text-[10px] uppercase font-semibold text-slate-400">Duration</span>
                    <div className="mt-1 font-semibold text-slate-900">
                      {selectedExecution.duration_ms !== null && selectedExecution.duration_ms !== undefined
                        ? `${selectedExecution.duration_ms} ms`
                        : '—'}
                    </div>
                  </div>
                  <div className="rounded-lg border border-slate-200/80 bg-slate-50 p-3">
                    <span className="text-[10px] uppercase font-semibold text-slate-400">User ID</span>
                    <div className="mt-1 font-semibold text-slate-900">
                      {selectedExecution.user_id ? `#${selectedExecution.user_id}` : 'System'}
                    </div>
                  </div>
                </div>

                <div className="space-y-1.5 pt-2">
                  <div className="flex justify-between text-slate-500">
                    <span>Started:</span>
                    <span className="font-medium text-slate-800">{formatDate(selectedExecution.started_at)}</span>
                  </div>
                  {selectedExecution.completed_at && (
                    <div className="flex justify-between text-slate-500">
                      <span>Completed:</span>
                      <span className="font-medium text-slate-800">{formatDate(selectedExecution.completed_at)}</span>
                    </div>
                  )}
                </div>

                {selectedExecution.error_message ? (
                  <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-3.5 text-xs text-rose-800">
                    <div className="font-semibold mb-1 flex items-center gap-1.5 text-rose-700">
                      <AlertCircle size={14} /> Error Diagnostics
                    </div>
                    <p className="font-mono text-[11px] whitespace-pre-wrap leading-relaxed">
                      {selectedExecution.error_message}
                    </p>
                  </div>
                ) : (
                  <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50/70 p-3.5 text-xs text-emerald-800 flex items-center gap-2">
                    <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />
                    <span>Workflow completed without unhandled exceptions.</span>
                  </div>
                )}
              </div>
            </div>

            {/* Drawer Footer */}
            <div className="p-5 border-t border-slate-100 flex justify-end">
              <Button variant="secondary" size="sm" onClick={() => setSelectedExecution(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
