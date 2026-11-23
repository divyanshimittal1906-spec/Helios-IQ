import { Plus, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { Panel } from '@/components/ui/stat-card';

export default function IntegrationsPage() {
  const integrations = [
    { name: 'FastAPI Backend Core', desc: 'Real-time orchestration & multi-agent routing', status: 'Connected' },
    { name: 'Knowledge RAG Store', desc: 'Vector chunking and semantic document retrieval', status: 'Connected' },
    { name: 'PostgreSQL Database', desc: 'Secure enterprise workspace isolation & audit logs', status: 'Active' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-200/80 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Integrations</h1>
          <p className="mt-1 text-sm text-slate-500">
            Connect third-party services, APIs, and document sources to expand your AI employees.
          </p>
        </div>

        <Button size="sm">
          <Plus size={14} /> Add Integration
        </Button>
      </div>

      <Panel title="Connected Systems" description="Active integrations and data pipelines">
        <div className="grid gap-3 sm:grid-cols-3">
          {integrations.map((item) => (
            <div
              key={item.name}
              className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs"
            >
              <div className="flex items-center justify-between">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 text-blue-600 border border-blue-100">
                  <Zap size={15} />
                </div>
                <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 border border-emerald-200">
                  {item.status}
                </span>
              </div>
              <h4 className="mt-3 text-xs font-semibold text-slate-900">{item.name}</h4>
              <p className="mt-1 text-[11px] text-slate-500">{item.desc}</p>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
