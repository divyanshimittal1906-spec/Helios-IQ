'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Activity,
  ArrowRight,
  Bot,
  CheckCircle2,
  ChevronRight,
  Database,
  FileText,
  LineChart,
  MessageSquare,
  Search,
  Send,
  Sparkles,
} from 'lucide-react';
import { StatusBadge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { Panel } from '@/components/ui/stat-card';
import { StepLoader } from '@/components/ui/step-loader';
import {
  addMessage,
  createConversation,
  ensureDemoSession,
  executeOrchestrationRequest,
  getCurrentUser,
  getWorkspaceSnapshot,
  listMessages,
  routeOrchestrationRequest,
  type AgentRead,
  type AgentExecutionRead,
  type ConversationRead,
  type KnowledgeBaseRead,
  type MessageRead,
  type OrchestrationDecision,
  type OrchestrationResponse,
  type UserRead,
  DEFAULT_WORKSPACE_ID,
  formatDate,
} from '@/lib/api';

const suggestedPrompts = [
  'Research competitors in the enterprise AI space',
  'Draft an executive summary for our Q3 product roadmap',
  'Analyze customer feedback trends and anomalies',
];

export function CommandCenterClient() {
  const [user, setUser] = useState<UserRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [agents, setAgents] = useState<AgentRead[]>([]);
  const [executions, setExecutions] = useState<AgentExecutionRead[]>([]);
  const [conversations, setConversations] = useState<ConversationRead[]>([]);
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBaseRead[]>([]);
  const [selectedConversationId, setSelectedConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<MessageRead[]>([]);
  const [messageDraft, setMessageDraft] = useState('');
  const [routeDecision, setRouteDecision] = useState<OrchestrationDecision | null>(null);
  const [executionResult, setExecutionResult] = useState<OrchestrationResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [executionStep, setExecutionStep] = useState(0);
  const [activeBottomTab, setActiveBottomTab] = useState<'thread' | 'knowledge'>('thread');
  const [showRawPayload, setShowRawPayload] = useState(false);

  useEffect(() => {
    let mounted = true;

    async function load() {
      try {
        setError(null);
        let currentUser = await getCurrentUser().catch(() => null);
        if (!currentUser) {
          currentUser = await ensureDemoSession();
        }

        const snapshot = await getWorkspaceSnapshot(DEFAULT_WORKSPACE_ID);

        if (!mounted) return;
        setUser(currentUser);
        setAgents(snapshot.agents);
        setExecutions(snapshot.executions);
        setConversations(snapshot.conversations);
        setKnowledgeBases(snapshot.knowledgeBases);

        if (snapshot.conversations.length > 0) {
          setSelectedConversationId(snapshot.conversations[0].id);
          const thread = await listMessages(snapshot.conversations[0].id, DEFAULT_WORKSPACE_ID);
          if (mounted) setMessages(thread);
        }
      } catch (err) {
        if (!mounted) return;
        const msg = err instanceof Error ? err.message : 'Unable to load workspace data.';
        if (!msg.toLowerCase().includes('authentication')) {
          setError(msg);
        }
      } finally {
        if (mounted) setLoading(false);
      }
    }

    load();

    const handleAuthChange = () => {
      if (mounted) void load();
    };

    window.addEventListener('helios-auth-change', handleAuthChange);

    return () => {
      mounted = false;
      window.removeEventListener('helios-auth-change', handleAuthChange);
    };
  }, []);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = messageDraft.trim();
    if (!trimmed) return;

    setSubmitting(true);
    setError(null);
    setExecutionStep(0);
    setRouteDecision(null);
    setExecutionResult(null);

    try {
      let conversationId = selectedConversationId;
      if (!conversationId) {
        const created = await createConversation({
          workspace_id: DEFAULT_WORKSPACE_ID,
          title: trimmed.slice(0, 60),
          initial_message: trimmed,
        });
        conversationId = created.id;
        setSelectedConversationId(conversationId);
        setConversations((current) => [created, ...current]);
      }

      const userMessage = await addMessage(
        conversationId,
        {
          role: 'user',
          content: trimmed,
        },
        DEFAULT_WORKSPACE_ID
      );

      setMessages((current) => [...current, userMessage]);
      setExecutionStep(1); // Routing

      const decision = await routeOrchestrationRequest({
        message: trimmed,
        workspace_id: DEFAULT_WORKSPACE_ID,
        conversation_id: conversationId,
      });
      setRouteDecision(decision);
      setExecutionStep(2); // Executing

      const execution = await executeOrchestrationRequest({
        message: trimmed,
        workspace_id: DEFAULT_WORKSPACE_ID,
        conversation_id: conversationId,
      });
      setExecutionResult(execution);
      setExecutionStep(3); // Completed

      const thread = await listMessages(conversationId, DEFAULT_WORKSPACE_ID);
      setMessages(thread);
      setMessageDraft('');

      const refreshed = await getWorkspaceSnapshot(DEFAULT_WORKSPACE_ID);
      setExecutions(refreshed.executions);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to run orchestration.');
      setExecutionStep(0);
    } finally {
      setSubmitting(false);
    }
  }

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  const displayName = user?.full_name ? user.full_name.split(' ')[0] : user?.email ? user.email.split('@')[0] : 'there';

  const defaultAgentCapabilities = [
    {
      name: 'Research Agent',
      slug: 'research-agent',
      desc: 'Researches markets, competitors, and topics with citations.',
      icon: Search,
      path: '/ai-employees?tab=research',
    },
    {
      name: 'Content Creator',
      slug: 'content-agent',
      desc: 'Drafts executive briefs, articles, and product copy.',
      icon: FileText,
      path: '/ai-employees?tab=content',
    },
    {
      name: 'Data Analyst',
      slug: 'data-agent',
      desc: 'Analyzes business datasets and detects anomalies.',
      icon: LineChart,
      path: '/analytics',
    },
  ];

  const executionSteps = [
    { id: 1, label: 'Routing Intent', detail: routeDecision ? `Intent: ${routeDecision.intent}` : 'Analyzing message context' },
    { id: 2, label: 'Executing Agent Workflow', detail: routeDecision?.agent_id ? `Assigned to Agent #${routeDecision.agent_id}` : 'Dispatching to worker' },
    { id: 3, label: 'Synthesizing Results', detail: executionResult ? `Status: ${executionResult.status}` : 'Formatting response' },
  ];

  // Helper to extract human-readable output from executionResult
  const getRenderableResult = () => {
    if (!executionResult?.result) return null;
    const r = executionResult.result as Record<string, unknown>;
    if (typeof r.content === 'string') return r.content;
    if (typeof r.summary === 'string') return r.summary;
    if (typeof r.answer === 'string') return r.answer;
    if (typeof r.message === 'string') return r.message;
    return null;
  };

  const renderableText = getRenderableResult();

  return (
    <div className="space-y-8">
      {/* 1. TOP GREETING */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
          {getGreeting()}, {displayName}
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Assign work to your AI workforce, track progress, and manage organization knowledge.
        </p>
      </div>

      {error && !error.toLowerCase().includes('authentication') && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs font-medium text-rose-700">
          {error}
        </div>
      )}

      {/* 2. THE ONE PROMINENT TASK INPUT / ACTION AREA */}
      <section className="rounded-xl border border-slate-200/90 bg-white p-5 sm:p-6 shadow-xs">
        <label htmlFor="orchestration-input" className="block text-sm font-semibold text-slate-900 mb-2">
          What would you like Helios IQ to work on?
        </label>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="relative">
            <textarea
              id="orchestration-input"
              rows={3}
              value={messageDraft}
              onChange={(e) => setMessageDraft(e.target.value)}
              placeholder="Describe a research topic, content brief, or data analysis task..."
              className="w-full resize-none rounded-lg border border-slate-200 bg-slate-50/50 p-3.5 text-sm text-slate-900 placeholder:text-slate-400 transition-colors focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
          </div>

          {/* Quick Prompt Chips */}
          <div className="flex flex-wrap items-center gap-1.5 pt-1">
            <span className="text-[11px] font-medium text-slate-400 mr-1">Examples:</span>
            {suggestedPrompts.map((prompt, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setMessageDraft(prompt)}
                className="rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-600 transition hover:bg-slate-50 hover:text-slate-900 hover:border-slate-300"
              >
                {prompt}
              </button>
            ))}
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-2 border-t border-slate-100">
            <span className="text-xs text-slate-400">
              Auto-routes to Research, Content, or Data Analyst agents.
            </span>
            <Button
              type="submit"
              disabled={submitting || !messageDraft.trim()}
              className="w-full sm:w-auto"
            >
              <Send size={13} />
              {submitting ? 'Starting...' : 'Start Task'}
            </Button>
          </div>
        </form>

        {/* Live Execution Progress Stepper */}
        {submitting && (
          <div className="mt-5 pt-5 border-t border-slate-100">
            <StepLoader
              agentName="Helios Orchestration Engine"
              currentStepIndex={executionStep}
              steps={executionSteps}
            />
          </div>
        )}

        {/* Execution Output (Progressive Disclosure) */}
        {!submitting && executionResult && (
          <div className="mt-5 rounded-lg border border-slate-200 bg-slate-50/70 p-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200/80">
              <div className="flex items-center gap-2">
                <CheckCircle2 size={15} className="text-emerald-600" />
                <span className="text-xs font-semibold text-slate-900">Task Completed</span>
                <span className="text-xs text-slate-400">·</span>
                <span className="text-xs text-slate-600">
                  {executionResult.agent_id ? `Agent #${executionResult.agent_id}` : 'Router'}
                </span>
              </div>
              <StatusBadge status={executionResult.status} />
            </div>

            <div className="mt-3 text-xs text-slate-700">
              {renderableText ? (
                <div className="whitespace-pre-wrap leading-relaxed text-slate-800 bg-white p-3 rounded-lg border border-slate-200/80">
                  {renderableText}
                </div>
              ) : (
                <p className="text-slate-600">Task output processed and recorded in workspace.</p>
              )}

              {executionResult.error && (
                <div className="mt-2 text-rose-600 font-medium">{executionResult.error}</div>
              )}

              <div className="mt-3 flex items-center justify-between text-[11px] text-slate-400">
                <span>Intent: {executionResult.intent || 'General Query'}</span>
                {executionResult.result && (
                  <button
                    type="button"
                    onClick={() => setShowRawPayload(!showRawPayload)}
                    className="text-blue-600 hover:underline"
                  >
                    {showRawPayload ? 'Hide details' : 'View payload'}
                  </button>
                )}
              </div>

              {showRawPayload && executionResult.result && (
                <pre className="mt-2 overflow-x-auto rounded border border-slate-200 bg-white p-2.5 text-[10px] text-slate-600 font-mono">
                  {JSON.stringify(executionResult.result, null, 2)}
                </pre>
              )}
            </div>
          </div>
        )}
      </section>

      {/* 3. CORE TWO-COLUMN SECTION: RECENT TASKS & AI WORKFORCE */}
      <div className="grid gap-6 lg:grid-cols-12">
        {/* Left Column (7 cols): Recent Tasks */}
        <div className="lg:col-span-7">
          <Panel
            title="Recent Tasks"
            description="Work currently in progress and recently completed"
            action={
              <Link
                href="/tasks"
                className="text-xs font-semibold text-blue-600 hover:text-blue-700 inline-flex items-center gap-0.5"
              >
                View all <ChevronRight size={13} />
              </Link>
            }
          >
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((n) => (
                  <div key={n} className="h-12 animate-pulse rounded-lg bg-slate-100" />
                ))}
              </div>
            ) : executions.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-100 text-slate-400 font-medium">
                      <th className="pb-2">Task</th>
                      <th className="pb-2">Employee</th>
                      <th className="pb-2">Status</th>
                      <th className="pb-2 text-right">Updated</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {executions.slice(0, 5).map((item) => (
                      <tr key={item.id} className="hover:bg-slate-50/70 transition-colors">
                        <td className="py-2.5 font-medium text-slate-900">
                          <Link href="/tasks" className="hover:text-blue-600">
                            Execution #{item.id}
                          </Link>
                        </td>
                        <td className="py-2.5 text-slate-500">Agent #{item.agent_id}</td>
                        <td className="py-2.5">
                          <StatusBadge status={item.status} />
                        </td>
                        <td className="py-2.5 text-right text-slate-400">
                          {formatDate(item.started_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState
                title="No tasks yet"
                description="Give your first task to an AI employee and Helios IQ will track the work for you."
                action={
                  <Button
                    size="sm"
                    onClick={() => {
                      document.getElementById('orchestration-input')?.focus();
                    }}
                  >
                    Start First Task
                  </Button>
                }
              />
            )}
          </Panel>
        </div>

        {/* Right Column (5 cols): Your AI Workforce */}
        <div className="lg:col-span-5">
          <Panel
            title="Your AI Workforce"
            description="Available employees ready for assignment"
            action={
              <Link
                href="/ai-employees"
                className="text-xs font-semibold text-blue-600 hover:text-blue-700 inline-flex items-center gap-0.5"
              >
                Directory <ChevronRight size={13} />
              </Link>
            }
          >
            <div className="space-y-2.5">
              {defaultAgentCapabilities.map((agent) => {
                const liveAgent = agents.find(
                  (a) =>
                    a.slug === agent.slug ||
                    a.name.toLowerCase().includes(agent.name.toLowerCase().split(' ')[0])
                );
                const status = liveAgent?.status || 'available';
                const Icon = agent.icon;

                return (
                  <div
                    key={agent.slug}
                    className="flex items-center justify-between rounded-lg border border-slate-200/80 bg-white p-3 transition-colors hover:border-slate-300"
                  >
                    <div className="flex items-center gap-2.5 min-w-0 pr-2">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600 border border-blue-100">
                        <Icon size={15} />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-semibold text-slate-900 truncate">
                            {agent.name}
                          </span>
                          <StatusBadge status={status} />
                        </div>
                        <p className="text-[11px] text-slate-500 truncate">
                          {agent.desc}
                        </p>
                      </div>
                    </div>
                    <Link
                      href={agent.path as any}
                      className="shrink-0 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 hover:text-slate-900 shadow-xs"
                    >
                      Assign
                    </Link>
                  </div>
                );
              })}
            </div>
          </Panel>
        </div>
      </div>

      {/* 4. PROGRESSIVE DISCLOSURE: THREAD & KNOWLEDGE */}
      <section className="space-y-3">
        <div className="flex items-center justify-between border-b border-slate-200 pb-2">
          <div className="flex gap-4">
            <button
              onClick={() => setActiveBottomTab('thread')}
              className={`pb-2 text-xs font-semibold transition-colors border-b-2 -mb-2.5 ${
                activeBottomTab === 'thread'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-slate-500 hover:text-slate-900'
              }`}
            >
              Conversation Thread ({messages.length})
            </button>
            <button
              onClick={() => setActiveBottomTab('knowledge')}
              className={`pb-2 text-xs font-semibold transition-colors border-b-2 -mb-2.5 ${
                activeBottomTab === 'knowledge'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-slate-500 hover:text-slate-900'
              }`}
            >
              Knowledge Sources ({knowledgeBases.length})
            </button>
          </div>
        </div>

        {activeBottomTab === 'thread' && (
          <Panel title="Workspace Conversation">
            <div className="space-y-2.5 max-h-64 overflow-y-auto pr-1">
              {messages.length > 0 ? (
                messages.map((item) => (
                  <div
                    key={item.id}
                    className={`rounded-lg p-3 text-xs ${
                      item.role === 'user'
                        ? 'bg-blue-50/60 border border-blue-100 text-slate-900'
                        : 'bg-slate-50 border border-slate-200/80 text-slate-800'
                    }`}
                  >
                    <div className="mb-1 flex items-center justify-between text-[10px] text-slate-400 font-medium uppercase tracking-wider">
                      <span>{item.role}</span>
                      <span>{formatDate(item.created_at)}</span>
                    </div>
                    <p className="whitespace-pre-wrap leading-relaxed">{item.content}</p>
                  </div>
                ))
              ) : (
                <EmptyState
                  title="No messages yet"
                  description="Start a task above to begin an interactive thread with Helios IQ."
                />
              )}
            </div>
          </Panel>
        )}

        {activeBottomTab === 'knowledge' && (
          <Panel
            title="Available Knowledge Bases"
            action={
              <Link
                href="/knowledge"
                className="text-xs font-semibold text-blue-600 hover:text-blue-700 inline-flex items-center gap-0.5"
              >
                Manage documents <ChevronRight size={13} />
              </Link>
            }
          >
            {knowledgeBases.length > 0 ? (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {knowledgeBases.map((kb) => (
                  <div
                    key={kb.id}
                    className="rounded-lg border border-slate-200/80 bg-white p-3.5 transition hover:border-slate-300"
                  >
                    <div className="flex items-center gap-2">
                      <Database size={14} className="text-blue-600" />
                      <span className="text-xs font-semibold text-slate-900">{kb.name}</span>
                    </div>
                    <p className="mt-1 text-[11px] text-slate-500 line-clamp-2">
                      {kb.description || 'No description provided.'}
                    </p>
                    <div className="mt-2 text-[10px] text-slate-400">
                      Updated {formatDate(kb.updated_at)}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No knowledge bases configured"
                description="Upload documents to give your AI workforce contextual information."
                action={
                  <Link href="/knowledge">
                    <Button size="sm">Go to Knowledge</Button>
                  </Link>
                }
              />
            )}
          </Panel>
        )}
      </section>
    </div>
  );
}
