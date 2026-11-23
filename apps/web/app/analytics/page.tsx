'use client';

import { useState } from 'react';
import {
  AlertCircle,
  BarChart3,
  CheckCircle2,
  FileSpreadsheet,
  FileUp,
  Lightbulb,
  Table as TableIcon,
  TrendingUp,
} from 'lucide-react';
import { StatusBadge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { Panel, StatCard } from '@/components/ui/stat-card';
import { analyzeDataset, DEFAULT_WORKSPACE_ID, type DataAnalysisResponse } from '@/lib/api';

export default function AnalyticsPage() {
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DataAnalysisResponse | null>(null);
  const [activeFileName, setActiveFileName] = useState<string | null>(null);
  const [showRawStats, setShowRawStats] = useState(false);

  async function handleFileUpload(file: File) {
    if (!file) return;
    setAnalyzing(true);
    setError(null);
    setResult(null);
    setActiveFileName(file.name);

    try {
      const data = await analyzeDataset(DEFAULT_WORKSPACE_ID, file);
      setResult(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to analyze dataset.';
      if (msg.toLowerCase().includes('authentication')) {
        setError(
          'Authentication required. Please click "Quick Demo Login" in the top navigation bar.'
        );
      } else {
        setError(msg);
      }
    } finally {
      setAnalyzing(false);
    }
  }

  function handleFileInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) {
      handleFileUpload(file);
    }
  }

  function handleUploadSampleCsv() {
    const sampleCsvContent = `department,employees,budget,satisfaction_score,turnover_rate
Engineering,120,4500000,4.2,0.08
Product,35,1800000,4.0,0.12
Marketing,45,2200000,3.8,0.15
Sales,80,3100000,3.5,0.22
Customer Success,50,1500000,4.1,0.09
Operations,25,900000,4.4,0.04
`;
    const blob = new Blob([sampleCsvContent], { type: 'text/csv' });
    const file = new File([blob], 'dept_performance_q3.csv', { type: 'text/csv' });
    handleFileUpload(file);
  }

  function handleUploadInvalidFile() {
    const textBlob = new Blob(['invalid non-csv content'], { type: 'text/plain' });
    const file = new File([textBlob], 'invalid_notes.txt', { type: 'text/plain' });
    handleFileUpload(file);
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-slate-200/80 pb-5">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Analytics</h1>
        <p className="mt-1 text-sm text-slate-500">
          Upload business datasets to trigger automated statistical synthesis and quality diagnostics.
        </p>
      </div>

      {error && (
        <div
          id="analytics-error-banner"
          className="flex items-center gap-2.5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs font-medium text-rose-700"
        >
          <AlertCircle size={16} className="shrink-0 text-rose-600" />
          <span>{error}</span>
        </div>
      )}

      {/* Main Grid */}
      <div className="grid gap-6 lg:grid-cols-12">
        {/* Left Column (4 cols): Dataset Upload Controls */}
        <div className="lg:col-span-4 space-y-4">
          <Panel title="Upload Dataset" description="Select CSV or XLSX files to analyze">
            <div className="space-y-4">
              <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50/50 p-6 text-center hover:border-blue-400 transition">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-600 border border-blue-100 mb-2">
                  <FileSpreadsheet size={18} />
                </div>
                <div className="text-xs font-semibold text-slate-800">Drag or select dataset</div>
                <div className="mt-0.5 text-[11px] text-slate-400 mb-3">Accepts .csv, .xlsx</div>
                <label className="cursor-pointer inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-blue-700 transition">
                  <FileUp size={13} />
                  <span>Choose File</span>
                  <input
                    id="csv-file-input"
                    type="file"
                    accept=".csv,.xlsx"
                    onChange={handleFileInputChange}
                    className="hidden"
                  />
                </label>
              </div>

              <div className="space-y-2 pt-1">
                <Button
                  id="load-sample-csv-btn"
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={handleUploadSampleCsv}
                  disabled={analyzing}
                  className="w-full text-xs justify-start"
                >
                  <TableIcon size={14} className="text-blue-600" />
                  Load Sample Dataset (Dept Performance)
                </Button>

                <Button
                  id="upload-invalid-btn"
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleUploadInvalidFile}
                  disabled={analyzing}
                  className="w-full text-xs justify-start text-slate-500 hover:text-slate-800"
                >
                  <AlertCircle size={14} className="text-slate-400" />
                  Test Invalid File Rejection (.txt)
                </Button>
              </div>

              {activeFileName && (
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-xs text-slate-600">
                  <span className="text-slate-400">Selected file: </span>
                  <span className="font-semibold text-slate-800 truncate block mt-0.5">
                    {activeFileName}
                  </span>
                </div>
              )}
            </div>
          </Panel>
        </div>

        {/* Right Column (8 cols): Analysis & Insights Output */}
        <div className="lg:col-span-8">
          <Panel
            title="Dataset Intelligence"
            description="Statistical synthesis and data quality breakdown"
          >
            {analyzing ? (
              <div className="space-y-4 p-4">
                <div className="h-4 w-1/4 animate-pulse rounded bg-slate-100" />
                <div className="grid grid-cols-4 gap-3">
                  {[1, 2, 3, 4].map((i) => (
                    <div key={i} className="h-16 animate-pulse rounded-lg bg-slate-100" />
                  ))}
                </div>
                <div className="h-32 animate-pulse rounded-lg bg-slate-100" />
              </div>
            ) : result ? (
              <div className="space-y-5 text-xs">
                {/* Status Bar */}
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 size={15} className="text-emerald-600" />
                    <span className="font-semibold text-slate-900">Analysis Complete</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={result.status} />
                    {result.execution_id && (
                      <span className="text-slate-400">Run #{result.execution_id}</span>
                    )}
                  </div>
                </div>

                {/* 4 Concise Stat Cards */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <StatCard
                    title="Total Rows"
                    value={String(result.dataset?.row_count ?? '—')}
                  />
                  <StatCard
                    title="Columns"
                    value={String(
                      result.dataset?.column_count ?? result.columns?.length ?? '—'
                    )}
                  />
                  <StatCard
                    title="Quality Score"
                    value={
                      result.data_quality?.quality_score !== undefined
                        ? `${Math.round(Number(result.data_quality.quality_score) * 100)}%`
                        : '100%'
                    }
                  />
                  <StatCard
                    title="Duplicates"
                    value={String(result.data_quality?.duplicate_rows ?? 0)}
                  />
                </div>

                {/* Key Insights & Anomalies */}
                <div className="rounded-lg border border-slate-200/90 bg-white p-4">
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-700 mb-2">
                    <Lightbulb size={14} className="text-blue-600" /> Key Insights & Anomalies
                  </div>
                  {result.insights && result.insights.length > 0 ? (
                    <ul className="space-y-1.5 list-disc list-inside text-slate-700 leading-relaxed">
                      {result.insights.map((insight, idx) => (
                        <li key={idx}>{insight}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-slate-400">No anomalies detected in dataset.</p>
                  )}
                </div>

                {/* Column Profiles Table */}
                {result.columns && result.columns.length > 0 && (
                  <div className="rounded-lg border border-slate-200/90 bg-white p-4">
                    <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-700 mb-2.5">
                      <TableIcon size={14} className="text-blue-600" /> Column Schema & Profiles
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-slate-100 text-slate-400 font-medium">
                            <th className="py-2 px-2">Column</th>
                            <th className="py-2 px-2">Type</th>
                            <th className="py-2 px-2">Null Count</th>
                            <th className="py-2 px-2 text-right">Unique Values</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 text-slate-700">
                          {result.columns.map((col, idx) => (
                            <tr key={idx} className="hover:bg-slate-50/70">
                              <td className="py-2 px-2 font-medium text-slate-900">
                                {String(col.name ?? col.column_name ?? idx)}
                              </td>
                              <td className="py-2 px-2 text-slate-500 font-mono text-[11px]">
                                {String(col.type ?? col.dtype ?? 'unknown')}
                              </td>
                              <td className="py-2 px-2 text-slate-500">
                                {String(col.null_count ?? 0)}
                              </td>
                              <td className="py-2 px-2 text-right text-slate-500">
                                {String(col.unique_count ?? '—')}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Summary Statistics */}
                {result.statistics && Object.keys(result.statistics).length > 0 && (
                  <div className="rounded-lg border border-slate-200/90 bg-white p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-700">
                        <TrendingUp size={14} className="text-blue-600" /> Statistical Summary
                      </div>
                      <button
                        type="button"
                        onClick={() => setShowRawStats(!showRawStats)}
                        className="text-[11px] text-blue-600 hover:underline"
                      >
                        {showRawStats ? 'Hide raw data' : 'View raw data'}
                      </button>
                    </div>

                    {showRawStats ? (
                      <pre className="overflow-x-auto rounded border border-slate-100 bg-slate-50 p-2.5 text-[10px] text-slate-700 font-mono">
                        {JSON.stringify(result.statistics, null, 2)}
                      </pre>
                    ) : (
                      <div className="grid gap-2 sm:grid-cols-2 text-slate-600">
                        {Object.entries(result.statistics).slice(0, 6).map(([key, val]) => (
                          <div key={key} className="rounded border border-slate-100 bg-slate-50 p-2">
                            <span className="font-semibold text-slate-800 block truncate">{key}</span>
                            <span className="text-[11px] text-slate-500 truncate block">
                              {typeof val === 'object' && val !== null
                                ? Object.entries(val as Record<string, unknown>)
                                    .slice(0, 3)
                                    .map(([k, v]) => `${k}: ${v}`)
                                    .join(' · ')
                                : String(val)}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <EmptyState
                icon={<BarChart3 size={24} />}
                title="No dataset analyzed yet"
                description="Upload a CSV/Excel file or click 'Load Sample Dataset' to inspect automated statistical insights."
                action={
                  <Button size="sm" onClick={handleUploadSampleCsv}>
                    Load Sample CSV
                  </Button>
                }
              />
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}
