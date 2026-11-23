'use client';

import { useEffect, useState } from 'react';
import {
  AlertTriangle,
  Bot,
  Check,
  ChevronRight,
  Copy,
  FileText,
  LineChart,
  RefreshCcw,
  Search,
  Sparkles,
  X,
} from 'lucide-react';
import { Badge, StatusBadge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { Panel } from '@/components/ui/stat-card';
import {
  generateContent,
  listAgents,
  runResearch,
  type AgentRead,
  type ContentGenerationResponse,
  type ResearchResponse,
  DEFAULT_WORKSPACE_ID,
} from '@/lib/api';

export default function AiEmployeesPage() {
  const [tab, setTab] = useState<'directory' | 'research' | 'content'>('directory');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [agents, setAgents] = useState<AgentRead[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<AgentRead | null>(null);

  // Research Agent state
  const [researchQuery, setResearchQuery] = useState(
    'Recent advances in artificial intelligence and autonomous agents'
  );
  const [maxSources, setMaxSources] = useState(5);
  const [researchLoading, setResearchLoading] = useState(false);
  const [researchError, setResearchError] = useState<string | null>(null);
  const [researchResult, setResearchResult] = useState<ResearchResponse | null>(null);

  // Content Agent state
  const [contentType, setContentType] = useState<
    'blog' | 'social_media_post' | 'email' | 'product_description' | 'report'
  >('blog');
  const [topic, setTopic] = useState('Helios IQ Enterprise AI Workforce Operating System');
  const [targetAudience, setTargetAudience] = useState('Enterprise CTOs and Engineering Leaders');
  const [tone, setTone] = useState('professional');
  const [keyPoints, setKeyPoints] = useState(
    'Unified workforce operating system\nSecure multi-tenant workspace isolation\nReal-time agent orchestration with research, content, and analytics'
  );
  const [instructions, setInstructions] = useState('');
  const [contentLoading, setContentLoading] = useState(false);
  const [contentError, setContentError] = useState<string | null>(null);
  const [contentResult, setContentResult] = useState<ContentGenerationResponse | null>(null);
  const [copied, setCopied] = useState(false);

  async function loadAgents() {
    try {
      setLoading(true);
      setError(null);
      setAgents(await listAgents());
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unable to load AI employees.';
      if (!msg.toLowerCase().includes('authentication')) {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadAgents();

    const handleAuthChange = () => {
      void loadAgents();
    };

    window.addEventListener('helios-auth-change', handleAuthChange);
    return () => {
      window.removeEventListener('helios-auth-change', handleAuthChange);
    };
  }, []);

  async function handleRunResearch(e: React.FormEvent) {
    e.preventDefault();
    if (!researchQuery.trim()) {
      setResearchError('Please enter a research query.');
      return;
    }
    setResearchLoading(true);
    setResearchError(null);
    setResearchResult(null);
    try {
      const res = await runResearch({
        query: researchQuery.trim(),
        workspace_id: DEFAULT_WORKSPACE_ID,
        max_sources: maxSources,
      });
      setResearchResult(res);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to execute research.';
      if (msg.toLowerCase().includes('authentication')) {
        setResearchError(
          'Authentication required. Please click "Quick Demo Login" in the top navigation bar.'
        );
      } else {
        setResearchError(msg);
      }
    } finally {
      setResearchLoading(false);
    }
  }

  async function handleGenerateContent(e: React.FormEvent) {
    e.preventDefault();
    const points = keyPoints
      .split('\n')
      .map((p) => p.trim())
      .filter((p) => p.length > 0);

    if (topic.trim().length < 3) {
      setContentError('Topic must be at least 3 characters.');
      return;
    }
    if (targetAudience.trim().length < 2) {
      setContentError('Target audience must be at least 2 characters.');
      return;
    }
    if (tone.trim().length < 2) {
      setContentError('Tone must be at least 2 characters.');
      return;
    }
    if (points.length === 0) {
      setContentError('At least one key point is required.');
      return;
    }

    setContentLoading(true);
    setContentError(null);
    setContentResult(null);
    try {
      const res = await generateContent({
        content_type: contentType,
        topic: topic.trim(),
        target_audience: targetAudience.trim(),
        tone: tone.trim(),
        key_points: points,
        instructions: instructions.trim() || undefined,
        workspace_id: DEFAULT_WORKSPACE_ID,
      });
      setContentResult(res);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to generate content.';
      if (msg.toLowerCase().includes('authentication')) {
        setContentError(
          'Authentication required. Please click "Quick Demo Login" in the top navigation bar.'
        );
      } else {
        setContentError(msg);
      }
    } finally {
      setContentLoading(false);
    }
  }

  const handleCopyContent = () => {
    if (contentResult?.content) {
      void navigator.clipboard.writeText(contentResult.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const getAgentIcon = (slugOrName: string) => {
    const s = slugOrName.toLowerCase();
    if (s.includes('research')) return Search;
    if (s.includes('content')) return FileText;
    if (s.includes('data') || s.includes('analyst')) return LineChart;
    return Bot;
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-200/80 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">AI Employees</h1>
          <p className="mt-1 text-sm text-slate-500">
            Choose specialized AI employees to assign business tasks and manage operational execution.
          </p>
        </div>

        {/* Tab Controls */}
        <div className="flex rounded-lg border border-slate-200 bg-white p-1 shadow-xs">
          <button
            id="tab-directory"
            onClick={() => setTab('directory')}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition ${
              tab === 'directory'
                ? 'bg-blue-600 text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
            }`}
          >
            <Bot size={14} /> Directory
          </button>
          <button
            id="tab-research"
            onClick={() => setTab('research')}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition ${
              tab === 'research'
                ? 'bg-blue-600 text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
            }`}
          >
            <Search size={14} /> Research Agent
          </button>
          <button
            id="tab-content"
            onClick={() => setTab('content')}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition ${
              tab === 'content'
                ? 'bg-blue-600 text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
            }`}
          >
            <FileText size={14} /> Content Agent
          </button>
        </div>
      </div>

      {error && !error.toLowerCase().includes('authentication') && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs font-medium text-rose-700">
          {error}
        </div>
      )}

      {/* 1. DIRECTORY TAB */}
      {tab === 'directory' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Workforce Directory ({agents.length || 3})
            </span>
            <button
              onClick={loadAgents}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50 shadow-xs"
            >
              <RefreshCcw size={12} /> Refresh
            </button>
          </div>

          {loading ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-44 animate-pulse rounded-xl bg-slate-100" />
              ))}
            </div>
          ) : agents.length > 0 ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {agents.map((agent) => {
                const Icon = getAgentIcon(agent.slug || agent.name);
                const isResearch = agent.slug?.includes('research') || agent.name.toLowerCase().includes('research');
                const isContent = agent.slug?.includes('content') || agent.name.toLowerCase().includes('content');

                return (
                  <div
                    key={agent.id}
                    className="flex flex-col justify-between rounded-xl border border-slate-200/90 bg-white p-5 shadow-xs transition hover:border-slate-300"
                  >
                    <div>
                      <div className="flex items-center justify-between">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-600 border border-blue-100">
                          <Icon size={18} />
                        </div>
                        <StatusBadge status={agent.status || 'available'} />
                      </div>

                      <h3 className="mt-4 text-sm font-semibold text-slate-900">{agent.name}</h3>
                      <p className="mt-1 text-xs text-slate-500 line-clamp-2 leading-relaxed">
                        {agent.description || 'Specialized AI employee for enterprise operations.'}
                      </p>
                    </div>

                    <div className="mt-5 pt-4 border-t border-slate-100 flex items-center justify-between gap-2">
                      <button
                        type="button"
                        onClick={() => setSelectedAgent(agent)}
                        className="text-xs font-medium text-slate-600 hover:text-slate-900"
                      >
                        Details
                      </button>

                      <Button
                        size="sm"
                        onClick={() => {
                          if (isResearch) setTab('research');
                          else if (isContent) setTab('content');
                          else setSelectedAgent(agent);
                        }}
                      >
                        Assign Task
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <EmptyState
              title="No AI agents registered"
              description="No agents found for this workspace. Sign in or load the demo workspace to access AI workers."
              action={
                <Button size="sm" onClick={loadAgents}>
                  Refresh Directory
                </Button>
              }
            />
          )}
        </div>
      )}

      {/* Agent Detail Modal / Drawer */}
      {selectedAgent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/30 p-4 backdrop-blur-xs">
          <div className="w-full max-w-lg rounded-xl border border-slate-200 bg-white p-6 shadow-xl">
            <div className="flex items-start justify-between border-b border-slate-100 pb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-600 border border-blue-100">
                  <Bot size={20} />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-slate-900">{selectedAgent.name}</h3>
                  <p className="text-xs text-slate-500">{selectedAgent.slug}</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedAgent(null)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
              >
                <X size={16} />
              </button>
            </div>

            <div className="py-4 space-y-4 text-xs text-slate-600">
              <div>
                <span className="font-semibold text-slate-800">Description:</span>
                <p className="mt-1 leading-relaxed text-slate-600">
                  {selectedAgent.description || 'Specialized AI employee deployed in this workspace.'}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-2">
                <div className="rounded-lg border border-slate-200/80 bg-slate-50 p-3">
                  <span className="text-[10px] uppercase font-semibold text-slate-400">Status</span>
                  <div className="mt-1">
                    <StatusBadge status={selectedAgent.status || 'available'} />
                  </div>
                </div>
                <div className="rounded-lg border border-slate-200/80 bg-slate-50 p-3">
                  <span className="text-[10px] uppercase font-semibold text-slate-400">Workspace</span>
                  <div className="mt-1 font-medium text-slate-800">#{selectedAgent.workspace_id}</div>
                </div>
                <div className="rounded-lg border border-slate-200/80 bg-slate-50 p-3">
                  <span className="text-[10px] uppercase font-semibold text-slate-400">Provider</span>
                  <div className="mt-1 font-medium text-slate-800">{selectedAgent.provider || 'Internal / Deterministic'}</div>
                </div>
                <div className="rounded-lg border border-slate-200/80 bg-slate-50 p-3">
                  <span className="text-[10px] uppercase font-semibold text-slate-400">Model</span>
                  <div className="mt-1 font-medium text-slate-800">{selectedAgent.model_name || 'Helios Standard'}</div>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 border-t border-slate-100 pt-4">
              <Button variant="secondary" size="sm" onClick={() => setSelectedAgent(null)}>
                Close
              </Button>
              <Button
                size="sm"
                onClick={() => {
                  const isResearch = selectedAgent.slug?.includes('research') || selectedAgent.name.toLowerCase().includes('research');
                  const isContent = selectedAgent.slug?.includes('content') || selectedAgent.name.toLowerCase().includes('content');
                  setSelectedAgent(null);
                  if (isResearch) setTab('research');
                  else if (isContent) setTab('content');
                }}
              >
                Open Workflow
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* 2. RESEARCH AGENT TAB */}
      {tab === 'research' && (
        <div className="grid gap-6 lg:grid-cols-12">
          {/* Form */}
          <div className="lg:col-span-5">
            <Panel title="Research Parameters" description="Query external or workspace sources for evidence">
              <form onSubmit={handleRunResearch} className="space-y-4">
                <div>
                  <label htmlFor="research-query-input" className="block text-xs font-medium text-slate-700 mb-1">
                    Research Topic / Question <span className="text-rose-500">*</span>
                  </label>
                  <textarea
                    id="research-query-input"
                    rows={4}
                    required
                    value={researchQuery}
                    onChange={(e) => setResearchQuery(e.target.value)}
                    placeholder="e.g. Research recent enterprise generative AI advancements"
                    className="w-full rounded-lg border border-slate-200 bg-white p-3 text-xs text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                  />
                </div>

                <div>
                  <label htmlFor="research-max-sources" className="block text-xs font-medium text-slate-700 mb-1">
                    Max Sources (1 - 10)
                  </label>
                  <input
                    id="research-max-sources"
                    type="number"
                    min={1}
                    max={10}
                    value={maxSources}
                    onChange={(e) => setMaxSources(Number(e.target.value))}
                    className="w-28 rounded-lg border border-slate-200 bg-white p-2 text-xs text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                  />
                </div>

                {researchError && (
                  <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700">
                    {researchError}
                  </div>
                )}

                <Button
                  id="run-research-btn"
                  type="submit"
                  disabled={researchLoading}
                  className="w-full"
                >
                  <Search size={14} />
                  {researchLoading ? 'Researching sources...' : 'Execute Research'}
                </Button>
              </form>
            </Panel>
          </div>

          {/* Output */}
          <div className="lg:col-span-7">
            <Panel title="Research Briefing Output">
              {researchLoading ? (
                <div className="space-y-4 p-4">
                  <div className="h-4 w-1/3 animate-pulse rounded bg-slate-100" />
                  <div className="h-20 animate-pulse rounded bg-slate-100" />
                  <div className="h-28 animate-pulse rounded bg-slate-100" />
                </div>
              ) : researchResult ? (
                <div className="space-y-4 text-xs">
                  {researchResult.insufficient_evidence && (
                    <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-xs text-amber-800">
                      <AlertTriangle size={14} className="shrink-0 text-amber-600" />
                      <span>Limited external evidence found; workspace context synthesized.</span>
                    </div>
                  )}

                  <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 block mb-1">
                      Executive Summary
                    </span>
                    <p className="text-slate-800 leading-relaxed text-xs">{researchResult.summary}</p>
                  </div>

                  <div className="rounded-lg border border-slate-200 bg-white p-4">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                      Key Findings
                    </span>
                    <ul className="space-y-1.5 list-disc list-inside text-slate-700 leading-relaxed">
                      {researchResult.key_findings.map((f, i) => (
                        <li key={i}>{f}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="rounded-lg border border-slate-200 bg-white p-4">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                      Sources & Citations ({researchResult.sources?.length || 0})
                    </span>
                    {researchResult.sources && researchResult.sources.length > 0 ? (
                      <div className="space-y-2">
                        {researchResult.sources.map((src, i) => (
                          <div key={i} className="rounded border border-slate-100 bg-slate-50 p-2">
                            <span className="font-semibold text-blue-700 block">
                              {String(src.title || src.source || `Source #${i + 1}`)}
                            </span>
                            {src.url ? <span className="text-slate-400 block truncate">{String(src.url)}</span> : null}
                            {src.snippet ? (
                              <p className="mt-1 text-slate-600 italic">&ldquo;{String(src.snippet)}&rdquo;</p>
                            ) : null}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-slate-400">No external source links needed.</p>
                    )}
                  </div>
                </div>
              ) : (
                <EmptyState
                  icon={<Search size={22} />}
                  title="No research executed yet"
                  description="Submit a question on the left to gather synthesized insights and citations."
                />
              )}
            </Panel>
          </div>
        </div>
      )}

      {/* 3. CONTENT AGENT TAB */}
      {tab === 'content' && (
        <div className="grid gap-6 lg:grid-cols-12">
          {/* Form */}
          <div className="lg:col-span-5">
            <Panel title="Content Generator" description="Draft structured marketing, sales, and operational copy">
              <form onSubmit={handleGenerateContent} className="space-y-3.5">
                <div>
                  <label htmlFor="content-type-select" className="block text-xs font-medium text-slate-700 mb-1">
                    Content Type
                  </label>
                  <select
                    id="content-type-select"
                    value={contentType}
                    onChange={(e) => setContentType(e.target.value as any)}
                    className="w-full rounded-lg border border-slate-200 bg-white p-2.5 text-xs text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                  >
                    <option value="blog">Blog Post</option>
                    <option value="social_media_post">Social Media Post</option>
                    <option value="email">Email Campaign / Newsletter</option>
                    <option value="product_description">Product Description</option>
                    <option value="report">Executive Report</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="content-topic-input" className="block text-xs font-medium text-slate-700 mb-1">
                    Topic / Title <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="content-topic-input"
                    type="text"
                    required
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="e.g. Next-Gen Enterprise AI Workforce"
                    className="w-full rounded-lg border border-slate-200 bg-white p-2.5 text-xs text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label htmlFor="content-audience-input" className="block text-xs font-medium text-slate-700 mb-1">
                      Audience <span className="text-rose-500">*</span>
                    </label>
                    <input
                      id="content-audience-input"
                      type="text"
                      required
                      value={targetAudience}
                      onChange={(e) => setTargetAudience(e.target.value)}
                      placeholder="e.g. CTOs, Managers"
                      className="w-full rounded-lg border border-slate-200 bg-white p-2.5 text-xs text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                    />
                  </div>
                  <div>
                    <label htmlFor="content-tone-input" className="block text-xs font-medium text-slate-700 mb-1">
                      Tone <span className="text-rose-500">*</span>
                    </label>
                    <input
                      id="content-tone-input"
                      type="text"
                      required
                      value={tone}
                      onChange={(e) => setTone(e.target.value)}
                      placeholder="e.g. professional, authoritative"
                      className="w-full rounded-lg border border-slate-200 bg-white p-2.5 text-xs text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="content-key-points-input" className="block text-xs font-medium text-slate-700 mb-1">
                    Key Points (one per line) <span className="text-rose-500">*</span>
                  </label>
                  <textarea
                    id="content-key-points-input"
                    rows={3}
                    required
                    value={keyPoints}
                    onChange={(e) => setKeyPoints(e.target.value)}
                    placeholder="Points to include..."
                    className="w-full rounded-lg border border-slate-200 bg-white p-2.5 text-xs text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                  />
                </div>

                <div>
                  <label htmlFor="content-instructions-input" className="block text-xs font-medium text-slate-700 mb-1">
                    Special Instructions (optional)
                  </label>
                  <input
                    id="content-instructions-input"
                    type="text"
                    value={instructions}
                    onChange={(e) => setInstructions(e.target.value)}
                    placeholder="e.g. Include a clear call to action"
                    className="w-full rounded-lg border border-slate-200 bg-white p-2.5 text-xs text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                  />
                </div>

                {contentError && (
                  <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700">
                    {contentError}
                  </div>
                )}

                <Button
                  id="generate-content-btn"
                  type="submit"
                  disabled={contentLoading}
                  className="w-full"
                >
                  <FileText size={14} />
                  {contentLoading ? 'Generating content...' : 'Generate Content'}
                </Button>
              </form>
            </Panel>
          </div>

          {/* Output */}
          <div className="lg:col-span-7">
            <Panel
              title="Generated Content"
              action={
                contentResult ? (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleCopyContent}
                    className="text-xs"
                  >
                    {copied ? <Check size={12} className="text-emerald-600" /> : <Copy size={12} />}
                    {copied ? 'Copied' : 'Copy'}
                  </Button>
                ) : null
              }
            >
              {contentLoading ? (
                <div className="space-y-4 p-4">
                  <div className="h-4 w-1/2 animate-pulse rounded bg-slate-100" />
                  <div className="h-32 animate-pulse rounded bg-slate-100" />
                </div>
              ) : contentResult ? (
                <div className="space-y-4 text-xs">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                    <div>
                      <span className="text-[10px] uppercase font-semibold text-blue-600">
                        {contentResult.content_type}
                      </span>
                      <h3 className="text-sm font-bold text-slate-900">{contentResult.title || topic}</h3>
                    </div>
                    <StatusBadge status={contentResult.status} />
                  </div>

                  <div className="rounded-lg border border-slate-200 bg-slate-50/50 p-4 text-slate-800 leading-relaxed whitespace-pre-wrap font-sans text-xs">
                    {contentResult.content}
                  </div>

                  {contentResult.metadata && Object.keys(contentResult.metadata).length > 0 && (
                    <div className="rounded border border-slate-100 bg-slate-50 p-2.5 text-[11px] text-slate-500">
                      <span className="font-semibold text-slate-700">Metadata: </span>
                      {JSON.stringify(contentResult.metadata)}
                    </div>
                  )}
                </div>
              ) : (
                <EmptyState
                  icon={<FileText size={22} />}
                  title="No content generated yet"
                  description="Configure parameters on the left and click 'Generate Content' to create copy."
                />
              )}
            </Panel>
          </div>
        </div>
      )}
    </div>
  );
}
