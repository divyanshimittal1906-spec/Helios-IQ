'use client';

import { useEffect, useState } from 'react';
import {
  AlertTriangle,
  BookOpen,
  Database,
  FileText,
  FileUp,
  FolderOpen,
  Plus,
  RefreshCcw,
  Search,
  Sparkles,
  Trash2,
  X,
} from 'lucide-react';
import { StatusBadge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { Panel } from '@/components/ui/stat-card';
import {
  createKnowledgeBase,
  deleteDocument,
  deleteKnowledgeBase,
  formatDate,
  listDocuments,
  listKnowledgeBases,
  queryKnowledgeBase,
  reprocessDocument,
  type DocumentRead,
  type KnowledgeBaseRead,
  type RAGQueryResponse,
  uploadDocument,
  DEFAULT_WORKSPACE_ID,
} from '@/lib/api';

export default function KnowledgePage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<KnowledgeBaseRead[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [documents, setDocuments] = useState<DocumentRead[]>([]);
  const [uploading, setUploading] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [searchDocQuery, setSearchDocQuery] = useState('');

  // RAG query state
  const [ragQuery, setRagQuery] = useState('');
  const [ragLoading, setRagLoading] = useState(false);
  const [ragError, setRagError] = useState<string | null>(null);
  const [ragResult, setRagResult] = useState<RAGQueryResponse | null>(null);

  async function loadDocuments(knowledgeBaseId: number) {
    try {
      setDocuments(await listDocuments(knowledgeBaseId, DEFAULT_WORKSPACE_ID));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load knowledge base documents.');
    }
  }

  async function loadKnowledge() {
    try {
      setLoading(true);
      setError(null);
      const nextItems = await listKnowledgeBases(DEFAULT_WORKSPACE_ID);
      setItems(nextItems);
      if (nextItems.length > 0) {
        setSelectedId((prev) => (prev ? prev : nextItems[0].id));
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unable to load knowledge bases.';
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
    void loadKnowledge();

    const handleAuthChange = () => {
      void loadKnowledge();
    };

    window.addEventListener('helios-auth-change', handleAuthChange);
    return () => {
      window.removeEventListener('helios-auth-change', handleAuthChange);
    };
  }, []);

  useEffect(() => {
    if (selectedId) {
      void loadDocuments(selectedId);
    } else {
      setDocuments([]);
    }
    setRagResult(null);
  }, [selectedId]);

  async function handleCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedName = newName.trim();
    if (!trimmedName) {
      setError('Knowledge base name is required.');
      return;
    }

    try {
      setError(null);
      const created = await createKnowledgeBase({
        name: trimmedName,
        description: newDescription.trim() || null,
        workspace_id: DEFAULT_WORKSPACE_ID,
      });
      setNewName('');
      setNewDescription('');
      setCreateModalOpen(false);
      setSelectedId(created.id);
      await loadKnowledge();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to create knowledge base.');
    }
  }

  async function handleDelete(id: number) {
    if (!window.confirm('Delete this knowledge base?')) return;
    try {
      await deleteKnowledgeBase(id, DEFAULT_WORKSPACE_ID);
      setItems((current) => current.filter((item) => item.id !== id));
      if (selectedId === id) {
        setSelectedId(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to delete knowledge base.');
    }
  }

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || !selectedId) return;

    try {
      setUploading(true);
      setError(null);
      await uploadDocument(selectedId, DEFAULT_WORKSPACE_ID, file);
      await loadDocuments(selectedId);
      event.target.value = '';
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to upload document.');
    } finally {
      setUploading(false);
    }
  }

  async function handleUploadSampleDoc() {
    if (!selectedId) return;
    const sampleDocContent = `Helios IQ AI Workforce Platform Architecture
Helios IQ is an enterprise AI operating system designed to orchestrate specialized AI agents.
Core agents include:
1. Research Agent: Discovers authoritative evidence and produces executive synthesis with real citations.
2. Content Agent: Drafts strategic copy including blogs, emails, social posts, product briefs, and executive reports.
3. Data Analyst Agent: Parses CSV and XLSX datasets, performs descriptive statistics, and detects anomalies.
Security architecture enforces multi-tenant workspace isolation, Argon2 password hashing, and signed JWT authentication.`;
    const blob = new Blob([sampleDocContent], { type: 'text/plain' });
    const file = new File([blob], 'helios_architecture_guide.txt', { type: 'text/plain' });

    try {
      setUploading(true);
      setError(null);
      await uploadDocument(selectedId, DEFAULT_WORKSPACE_ID, file);
      await loadDocuments(selectedId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to upload sample document.');
    } finally {
      setUploading(false);
    }
  }

  async function handleReprocess(documentId: number) {
    if (!selectedId) return;
    try {
      await reprocessDocument(selectedId, documentId, DEFAULT_WORKSPACE_ID);
      await loadDocuments(selectedId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to reprocess document.');
    }
  }

  async function handleDeleteDocument(documentId: number) {
    if (!selectedId || !window.confirm('Delete this document from the knowledge base?')) return;
    try {
      await deleteDocument(selectedId, documentId, DEFAULT_WORKSPACE_ID);
      await loadDocuments(selectedId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to delete document.');
    }
  }

  async function handleRagQuery(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedId || !ragQuery.trim()) return;

    setRagLoading(true);
    setRagError(null);
    setRagResult(null);

    try {
      const res = await queryKnowledgeBase(selectedId, ragQuery.trim(), DEFAULT_WORKSPACE_ID);
      setRagResult(res);
    } catch (err) {
      setRagError(err instanceof Error ? err.message : 'RAG query failed.');
    } finally {
      setRagLoading(false);
    }
  }

  const selectedKb = items.find((i) => i.id === selectedId);

  const filteredDocs = documents.filter((d) => {
    if (!searchDocQuery.trim()) return true;
    const q = searchDocQuery.toLowerCase();
    return (
      (d.title && d.title.toLowerCase().includes(q)) ||
      (d.file_name && d.file_name.toLowerCase().includes(q)) ||
      (d.mime_type && d.mime_type.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-200/80 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Knowledge</h1>
          <p className="mt-1 text-sm text-slate-500">
            Give your AI employees access to the information and documents they need.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {selectedId && (
            <label className="cursor-pointer inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-blue-700 transition">
              <FileUp size={14} />
              <span>{uploading ? 'Uploading...' : 'Upload Document'}</span>
              <input
                id="kb-doc-upload"
                type="file"
                accept=".txt,.pdf,.docx"
                className="hidden"
                disabled={uploading}
                onChange={handleUpload}
              />
            </label>
          )}

          <Button
            variant="secondary"
            size="sm"
            onClick={() => setCreateModalOpen(true)}
          >
            <Plus size={14} />
            New Knowledge Base
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs font-medium text-rose-700">
          {error}
        </div>
      )}

      {/* Main Workspace Layout */}
      <div className="grid gap-6 lg:grid-cols-12">
        {/* Left Column (4 cols): Knowledge Bases List */}
        <div className="lg:col-span-4 space-y-4">
          <Panel
            title="Knowledge Bases"
            description="Repositories available to AI agents"
            action={
              <button
                onClick={loadKnowledge}
                className="text-slate-400 hover:text-slate-700 p-1"
                title="Refresh"
              >
                <RefreshCcw size={13} />
              </button>
            }
          >
            {loading ? (
              <div className="space-y-2 py-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-14 animate-pulse rounded-lg bg-slate-100" />
                ))}
              </div>
            ) : items.length > 0 ? (
              <div className="space-y-2">
                {items.map((kb) => (
                  <div
                    key={kb.id}
                    onClick={() => setSelectedId(kb.id)}
                    className={`flex items-start justify-between rounded-xl border p-3.5 transition cursor-pointer ${
                      selectedId === kb.id
                        ? 'border-blue-500 bg-blue-50/50 shadow-xs'
                        : 'border-slate-200/80 bg-white hover:border-slate-300'
                    }`}
                  >
                    <div className="flex items-start gap-3 min-w-0 pr-2">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600 border border-blue-100">
                        <Database size={15} />
                      </div>
                      <div className="min-w-0">
                        <h4 className="text-xs font-semibold text-slate-900 truncate">{kb.name}</h4>
                        <p className="mt-0.5 text-[11px] text-slate-500 line-clamp-1">
                          {kb.description || 'No description provided.'}
                        </p>
                        <span className="mt-1 block text-[10px] text-slate-400">
                          Updated {formatDate(kb.updated_at)}
                        </span>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        void handleDelete(kb.id);
                      }}
                      title="Delete knowledge base"
                      className="text-slate-400 hover:text-rose-600 p-1 rounded hover:bg-rose-50 transition"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                icon={<Database size={20} />}
                title="No knowledge bases"
                description="Create a knowledge base to begin uploading documentation for AI employees."
                action={
                  <Button size="sm" onClick={() => setCreateModalOpen(true)}>
                    Create Base
                  </Button>
                }
              />
            )}
          </Panel>
        </div>

        {/* Right Column (8 cols): Document Manager & RAG Query */}
        <div className="lg:col-span-8 space-y-6">
          {selectedKb ? (
            <>
              {/* Document Manager Panel */}
              <Panel
                title={selectedKb.name}
                description={selectedKb.description || `Knowledge base #${selectedKb.id}`}
                action={
                  <div className="flex items-center gap-2">
                    <Button
                      id="upload-sample-doc-btn"
                      variant="secondary"
                      size="sm"
                      disabled={uploading}
                      onClick={handleUploadSampleDoc}
                      className="text-xs"
                    >
                      <BookOpen size={12} />
                      Load Sample Guide
                    </Button>
                  </div>
                }
              >
                {/* Search & Filter Bar */}
                <div className="mb-4">
                  <label className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50/50 px-3 py-1.5 text-xs text-slate-700 focus-within:border-blue-500 focus-within:bg-white focus-within:ring-2 focus-within:ring-blue-100">
                    <Search size={13} className="text-slate-400" />
                    <input
                      type="text"
                      value={searchDocQuery}
                      onChange={(e) => setSearchDocQuery(e.target.value)}
                      placeholder="Search documents by name or file type..."
                      className="w-full bg-transparent focus:outline-none placeholder:text-slate-400"
                    />
                  </label>
                </div>

                {/* Document Table */}
                {filteredDocs.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-slate-100 text-slate-400 font-medium">
                          <th className="py-2.5 px-3">Document</th>
                          <th className="py-2.5 px-3">Type</th>
                          <th className="py-2.5 px-3">Status</th>
                          <th className="py-2.5 px-3">Updated</th>
                          <th className="py-2.5 px-3 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 text-slate-700">
                        {filteredDocs.map((doc) => (
                          <tr key={doc.id} className="hover:bg-slate-50/70 transition-colors">
                            <td className="py-3 px-3 font-medium text-slate-900">
                              <div className="flex items-center gap-2">
                                <FileText size={14} className="text-blue-600 shrink-0" />
                                <span className="truncate max-w-[200px]">
                                  {doc.title || doc.file_name}
                                </span>
                              </div>
                            </td>
                            <td className="py-3 px-3 text-slate-500">{doc.mime_type}</td>
                            <td className="py-3 px-3">
                              <StatusBadge status={doc.status} />
                            </td>
                            <td className="py-3 px-3 text-slate-400">
                              {formatDate(doc.updated_at)}
                            </td>
                            <td className="py-3 px-3 text-right">
                              <div className="flex items-center justify-end gap-1.5">
                                <button
                                  type="button"
                                  onClick={() => handleReprocess(doc.id)}
                                  className="rounded px-2 py-1 text-[11px] font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition"
                                >
                                  Reprocess
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleDeleteDocument(doc.id)}
                                  className="rounded p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition"
                                  title="Delete document"
                                >
                                  <Trash2 size={13} />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <EmptyState
                    icon={<FolderOpen size={20} />}
                    title="No documents uploaded"
                    description="Upload text documents, PDFs, or load the sample guide to train RAG retrieval."
                    action={
                      <label className="cursor-pointer inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-blue-700 transition">
                        <FileUp size={13} />
                        <span>Upload File</span>
                        <input
                          type="file"
                          accept=".txt,.pdf,.docx"
                          className="hidden"
                          onChange={handleUpload}
                        />
                      </label>
                    }
                  />
                )}
              </Panel>

              {/* RAG Semantic Query Panel */}
              <Panel
                title="RAG Semantic Query"
                description={`Retrieve synthesized context and citations from ${selectedKb.name}`}
              >
                <form onSubmit={handleRagQuery} className="space-y-4">
                  <div className="flex gap-2">
                    <input
                      id="rag-query-input"
                      type="text"
                      value={ragQuery}
                      onChange={(e) => setRagQuery(e.target.value)}
                      placeholder="Ask a question against this Knowledge Base..."
                      className="flex-1 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                    />
                    <Button
                      id="rag-query-btn"
                      type="submit"
                      disabled={ragLoading || !ragQuery.trim()}
                    >
                      <Search size={14} />
                      {ragLoading ? 'Searching...' : 'Ask RAG'}
                    </Button>
                  </div>

                  {ragError && (
                    <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700">
                      {ragError}
                    </div>
                  )}

                  {ragResult && (
                    <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 space-y-3 text-xs">
                      {ragResult.insufficient_evidence && (
                        <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-2 text-xs text-amber-800">
                          <AlertTriangle size={13} className="text-amber-600" />
                          <span>Insufficient evidence in uploaded documents to fully answer.</span>
                        </div>
                      )}

                      <div>
                        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 block mb-1">
                          Synthesized Answer
                        </span>
                        <p className="text-slate-800 leading-relaxed font-sans">{ragResult.answer}</p>
                      </div>

                      {ragResult.citations && ragResult.citations.length > 0 && (
                        <div className="pt-2 border-t border-slate-200/80">
                          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                            Citations ({ragResult.citations.length}) · Retrieved Chunks: {ragResult.retrieved_chunks}
                          </span>
                          <div className="space-y-1.5">
                            {ragResult.citations.map((cite, idx) => (
                              <div
                                key={idx}
                                className="rounded border border-slate-200/80 bg-white p-2 text-slate-600"
                              >
                                <span className="font-semibold text-blue-700">
                                  [{cite.document_title || cite.file_name}]
                                </span>
                                <span className="text-slate-400 ml-2">Chunk #{cite.chunk_index}</span>
                                {cite.similarity !== undefined && cite.similarity !== null && (
                                  <span className="text-slate-400 ml-2">
                                    Score: {cite.similarity.toFixed(2)}
                                  </span>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </form>
              </Panel>
            </>
          ) : (
            <EmptyState
              icon={<Database size={24} />}
              title="Select a knowledge base"
              description="Choose a knowledge repository from the left or create a new one to manage documents."
            />
          )}
        </div>
      </div>

      {/* New Knowledge Base Modal */}
      {createModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/30 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div className="flex items-center gap-2 text-slate-900">
                <Database size={18} className="text-blue-600" />
                <h3 className="font-semibold text-base">New Knowledge Base</h3>
              </div>
              <button
                onClick={() => setCreateModalOpen(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
              >
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleCreate} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Name <span className="text-rose-500">*</span>
                </label>
                <input
                  id="new-kb-name"
                  type="text"
                  required
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. Enterprise Architecture Docs"
                  className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Description
                </label>
                <textarea
                  id="new-kb-description"
                  rows={3}
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  placeholder="e.g. Product specifications, security guidelines, and business briefs."
                  className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => setCreateModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button id="create-kb-btn" type="submit" size="sm">
                  Create Knowledge Base
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
