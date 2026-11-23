export const DEFAULT_WORKSPACE_ID = 1;
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export type ApiError = Error & { status?: number };

export interface AgentRead {
  id: number;
  name: string;
  slug: string;
  description?: string | null;
  provider?: string | null;
  model_name?: string | null;
  status: string;
  workspace_id: number;
}

export interface AgentExecutionRead {
  id: number;
  workspace_id: number;
  user_id?: number | null;
  agent_id: number;
  conversation_id?: number | null;
  status: string;
  started_at?: string | null;
  completed_at?: string | null;
  duration_ms?: number | null;
  error_message?: string | null;
}

export interface ConversationRead {
  id: number;
  workspace_id: number;
  user_id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface MessageRead {
  id: number;
  workspace_id: number;
  conversation_id: number;
  user_id?: number | null;
  role: string;
  content: string;
  metadata?: Record<string, unknown> | null;
  created_at: string;
}

export interface KnowledgeBaseRead {
  id: number;
  workspace_id: number;
  name: string;
  description?: string | null;
  created_by?: number | null;
  created_at: string;
  updated_at: string;
}

export interface OrchestrationDecision {
  intent: string;
  agent_id?: string | null;
  supported: boolean;
  status: string;
  reason?: string | null;
}

export interface OrchestrationResponse {
  execution_id?: number | null;
  intent?: string | null;
  agent_id?: string | null;
  status: string;
  result?: Record<string, unknown> | null;
  error?: string | null;
  metadata?: Record<string, unknown>;
}

export interface ResearchResponse {
  question: string;
  summary: string;
  key_findings: string[];
  sources: Array<Record<string, unknown>>;
  citations: Array<Record<string, unknown>>;
  insufficient_evidence?: boolean;
}

export interface ContentGenerationResponse {
  content: string;
  content_type: string;
  title?: string | null;
  metadata?: Record<string, unknown>;
  execution_id?: number | null;
  status: string;
}

export interface DataAnalysisResponse {
  dataset: Record<string, unknown>;
  columns: Array<Record<string, unknown>>;
  statistics: Record<string, unknown>;
  data_quality: Record<string, unknown>;
  insights: string[];
  chart_ready?: Array<Record<string, unknown>>;
  execution_id?: number | null;
  status: string;
}

export interface Citation {
  chunk_id: number;
  document_id: number;
  document_title: string;
  file_name: string;
  knowledge_base_id: number;
  chunk_index: number;
  similarity?: number | null;
  source_metadata?: Record<string, unknown> | null;
}

export interface RAGQueryResponse {
  answer: string;
  citations: Citation[];
  context: string;
  insufficient_evidence: boolean;
  retrieved_chunks: number;
}

export interface DocumentRead {
  id: number;
  workspace_id: number;
  knowledge_base_id: number;
  title: string;
  file_name: string;
  mime_type: string;
  storage_path: string;
  checksum?: string | null;
  status: string;
  document_metadata?: Record<string, unknown> | null;
  extracted_text?: string | null;
  created_by?: number | null;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeBaseCreateInput {
  name: string;
  description?: string | null;
  workspace_id: number;
}

export interface KnowledgeBaseUpdateInput {
  name?: string;
  description?: string | null;
  workspace_id?: number;
}

function buildUrl(path: string, params: Record<string, string | number | undefined> = {}) {
  const baseUrl =
    typeof window !== 'undefined' && !process.env.NEXT_PUBLIC_API_URL
      ? ''
      : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');
  const query = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      query.append(key, String(value));
    }
  });

  const suffix = query.toString() ? `?${query.toString()}` : '';
  return `${baseUrl}${path}${suffix}`;
}

const AUTH_STORAGE_KEY = 'helios_auth_token';

let _authToken: string | null = null;
if (typeof window !== 'undefined') {
  try {
    _authToken = localStorage.getItem(AUTH_STORAGE_KEY);
  } catch {
    // ignore
  }
}

export function setAuthToken(token: string | null) {
  _authToken = token;
  if (typeof window !== 'undefined') {
    try {
      if (token) {
        localStorage.setItem(AUTH_STORAGE_KEY, token);
      } else {
        localStorage.removeItem(AUTH_STORAGE_KEY);
      }
    } catch {
      // ignore
    }
  }
}

export function getAuthToken(): string | null {
  return _authToken;
}

export interface UserRead {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserRead;
}

let _demoLoginPromise: Promise<TokenResponse | null> | null = null;

export async function ensureDemoSession(): Promise<UserRead | null> {
  if (typeof window === 'undefined') return null;

  if (_authToken) {
    try {
      return await getCurrentUser();
    } catch {
      setAuthToken(null);
    }
  }

  // Prevent multiple concurrent demo logins
  if (!_demoLoginPromise) {
    _demoLoginPromise = (async () => {
      try {
        const res = await loginUser({ email: 'user@example.com', password: 'devpassword123' });
        return res;
      } catch {
        return null;
      } finally {
        _demoLoginPromise = null;
      }
    })();
  }

  const res = await _demoLoginPromise;
  return res?.user ?? null;
}

export async function loginUser(payload: { email: string; password: string }) {
  const data = await request<TokenResponse>('/api/auth/login', {}, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  if (data?.access_token) {
    setAuthToken(data.access_token);
  }
  if (typeof window !== 'undefined' && data?.user) {
    window.dispatchEvent(new CustomEvent('helios-auth-change', { detail: data.user }));
  }
  return data;
}

export async function registerUser(payload: { email: string; password: string; full_name?: string }) {
  return request<UserRead>('/api/auth/register', {}, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getCurrentUser() {
  return request<UserRead>('/api/auth/me');
}

export async function logoutUser() {
  try {
    await request<{ message: string }>('/api/auth/logout', {}, { method: 'POST' });
  } finally {
    setAuthToken(null);
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('helios-auth-change', { detail: null }));
    }
  }
}

async function request<T>(path: string, params: Record<string, string | number | undefined> = {}, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers ?? {});

  if (!_authToken && typeof window !== 'undefined') {
    try {
      _authToken = localStorage.getItem(AUTH_STORAGE_KEY);
    } catch {
      // ignore
    }
  }

  if (_authToken) {
    headers.set('Authorization', `Bearer ${_authToken}`);
  }

  if (!(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(buildUrl(path, params), {
    credentials: 'include',
    ...init,
    headers,
  });

  if (!response.ok) {
    // If unauthorized on a data route, attempt demo login recovery once
    if (
      response.status === 401 &&
      typeof window !== 'undefined' &&
      !path.includes('/api/auth/login') &&
      !path.includes('/api/auth/register') &&
      !path.includes('/api/auth/logout')
    ) {
      try {
        const demo = await ensureDemoSession();
        if (demo && _authToken) {
          headers.set('Authorization', `Bearer ${_authToken}`);
          const retryRes = await fetch(buildUrl(path, params), {
            credentials: 'include',
            ...init,
            headers,
          });
          if (retryRes.ok) {
            if (retryRes.status === 204) return undefined as T;
            const retryText = await retryRes.text();
            if (!retryText) return undefined as T;
            try {
              return JSON.parse(retryText) as T;
            } catch {
              return retryText as unknown as T;
            }
          }
        }
      } catch {
        // fall through to error handling
      }
    }

    const text = await response.text();
    let message = text || 'Request failed.';
    try {
      const parsed = JSON.parse(text);
      if (parsed.detail) {
        message = typeof parsed.detail === 'string' ? parsed.detail : JSON.stringify(parsed.detail);
      }
    } catch {
      // use raw text
    }
    const error = new Error(message) as ApiError;
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  if (!text) {
    return undefined as T;
  }

  try {
    return JSON.parse(text) as T;
  } catch {
    return text as unknown as T;
  }
}

export async function listAgents(workspaceId = DEFAULT_WORKSPACE_ID) {
  return request<AgentRead[]>('/api/agents', { workspace_id: workspaceId });
}

export async function getAgent(agentId: number, workspaceId = DEFAULT_WORKSPACE_ID) {
  return request<AgentRead>(`/api/agents/${agentId}`, { workspace_id: workspaceId });
}

export async function listExecutions(workspaceId = DEFAULT_WORKSPACE_ID) {
  return request<AgentExecutionRead[]>('/api/agents/executions', { workspace_id: workspaceId });
}

export async function getExecution(executionId: number, workspaceId = DEFAULT_WORKSPACE_ID) {
  return request<AgentExecutionRead>(`/api/agents/executions/${executionId}`, { workspace_id: workspaceId });
}

export async function listConversations(workspaceId = DEFAULT_WORKSPACE_ID) {
  return request<ConversationRead[]>('/api/conversations', { workspace_id: workspaceId });
}

export async function createConversation(payload: { workspace_id: number; title?: string | null; initial_message?: string | null }) {
  return request<ConversationRead>('/api/conversations', {}, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getConversation(conversationId: number, workspaceId = DEFAULT_WORKSPACE_ID) {
  return request<ConversationRead>(`/api/conversations/${conversationId}`, { workspace_id: workspaceId });
}

export async function listMessages(conversationId: number, workspaceId = DEFAULT_WORKSPACE_ID) {
  return request<MessageRead[]>(`/api/conversations/${conversationId}/messages`, { workspace_id: workspaceId });
}

export async function addMessage(conversationId: number, payload: { role: string; content: string; metadata?: Record<string, unknown> | null }, workspaceId = DEFAULT_WORKSPACE_ID) {
  return request<MessageRead>(`/api/conversations/${conversationId}/messages`, { workspace_id: workspaceId }, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function routeOrchestrationRequest(payload: { message: string; workspace_id: number; conversation_id?: number | null; context?: Record<string, unknown> | null }) {
  return request<OrchestrationDecision>('/api/orchestration/route', {}, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function executeOrchestrationRequest(payload: { message: string; workspace_id: number; conversation_id?: number | null; context?: Record<string, unknown> | null }) {
  return request<OrchestrationResponse>('/api/orchestration/execute', {}, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function runResearch(payload: { query: string; workspace_id: number; knowledge_base_id?: number | null; max_sources?: number }) {
  return request<ResearchResponse>('/api/research', {}, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function generateContent(payload: {
  content_type: string;
  topic: string;
  target_audience: string;
  tone: string;
  desired_length?: string;
  key_points: string[];
  brand_voice?: string | null;
  language?: string;
  instructions?: string | null;
  workspace_id: number;
}) {
  return request<ContentGenerationResponse>('/api/content/generate', {}, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function analyzeDataset(workspaceId: number, file: File) {
  const form = new FormData();
  form.append('file', file);
  form.append('workspace_id', String(workspaceId));

  return request<DataAnalysisResponse>(`/api/data/analyze?workspace_id=${workspaceId}`, {}, {
    method: 'POST',
    body: form,
  });
}

export async function listKnowledgeBases(workspaceId = DEFAULT_WORKSPACE_ID) {
  return request<KnowledgeBaseRead[]>('/api/knowledge', { workspace_id: workspaceId });
}

export async function createKnowledgeBase(payload: KnowledgeBaseCreateInput) {
  return request<KnowledgeBaseRead>('/api/knowledge', {}, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getKnowledgeBase(knowledgeBaseId: number, workspaceId = DEFAULT_WORKSPACE_ID) {
  return request<KnowledgeBaseRead>(`/api/knowledge/${knowledgeBaseId}`, { workspace_id: workspaceId });
}

export async function updateKnowledgeBase(knowledgeBaseId: number, payload: KnowledgeBaseUpdateInput, workspaceId = DEFAULT_WORKSPACE_ID) {
  return request<KnowledgeBaseRead>(`/api/knowledge/${knowledgeBaseId}`, { workspace_id: workspaceId }, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function deleteKnowledgeBase(knowledgeBaseId: number, workspaceId = DEFAULT_WORKSPACE_ID) {
  return request<{ message: string }>(`/api/knowledge/${knowledgeBaseId}`, { workspace_id: workspaceId }, {
    method: 'DELETE',
  });
}

export async function listDocuments(knowledgeBaseId: number, workspaceId = DEFAULT_WORKSPACE_ID) {
  return request<DocumentRead[]>(`/api/knowledge/${knowledgeBaseId}/documents`, { workspace_id: workspaceId });
}

export async function uploadDocument(knowledgeBaseId: number, workspaceId: number, file: File) {
  const form = new FormData();
  form.append('file', file);

  return request<DocumentRead>(`/api/knowledge/${knowledgeBaseId}/documents`, { workspace_id: workspaceId }, {
    method: 'POST',
    body: form,
  });
}

export async function reprocessDocument(knowledgeBaseId: number, documentId: number, workspaceId = DEFAULT_WORKSPACE_ID) {
  return request<DocumentRead>(`/api/knowledge/${knowledgeBaseId}/documents/${documentId}/reprocess`, { workspace_id: workspaceId }, {
    method: 'POST',
  });
}

export async function deleteDocument(knowledgeBaseId: number, documentId: number, workspaceId = DEFAULT_WORKSPACE_ID) {
  return request<{ message: string }>(`/api/knowledge/${knowledgeBaseId}/documents/${documentId}`, { workspace_id: workspaceId }, {
    method: 'DELETE',
  });
}

export async function queryKnowledgeBase(
  knowledgeBaseId: number,
  query: string,
  workspaceId = DEFAULT_WORKSPACE_ID,
  topK = 5
) {
  return request<RAGQueryResponse>(`/api/knowledge/${knowledgeBaseId}/rag/query?workspace_id=${workspaceId}`, {}, {
    method: 'POST',
    body: JSON.stringify({ query, top_k: topK }),
  });
}

export async function getWorkspaceSnapshot(workspaceId = DEFAULT_WORKSPACE_ID) {
  const [agents, executions, conversations, knowledgeBases] = await Promise.all([
    listAgents(workspaceId),
    listExecutions(workspaceId),
    listConversations(workspaceId),
    listKnowledgeBases(workspaceId),
  ]);

  return { agents, executions, conversations, knowledgeBases };
}

export function formatDate(value?: string | null) {
  if (!value) return '—';
  return new Date(value).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

export function statusClasses(status: string) {
  const normalized = status.toLowerCase();

  if (normalized.includes('completed') || normalized === 'success') return 'bg-emerald-500/10 text-emerald-300 ring-1 ring-emerald-500/30';
  if (normalized.includes('running') || normalized.includes('pending') || normalized.includes('queued')) return 'bg-amber-500/10 text-amber-300 ring-1 ring-amber-500/30';
  if (normalized.includes('failed') || normalized.includes('error')) return 'bg-rose-500/10 text-rose-300 ring-1 ring-rose-500/30';
  return 'bg-slate-500/10 text-slate-300 ring-1 ring-slate-500/30';
}
