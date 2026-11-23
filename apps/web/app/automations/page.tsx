import { Plus, Workflow } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { Panel } from '@/components/ui/stat-card';

export default function AutomationsPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-200/80 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Automations</h1>
          <p className="mt-1 text-sm text-slate-500">
            Define recurring schedules and event-driven recipes for autonomous agent execution.
          </p>
        </div>

        <Button size="sm">
          <Plus size={14} /> New Automation
        </Button>
      </div>

      <Panel title="Configured Automations" description="Event triggers and agent pipelines">
        <EmptyState
          icon={<Workflow size={24} />}
          title="No automations created"
          description="Automate repetitive research briefings, weekly executive content drafts, and dataset monitoring."
          action={<Button size="sm">Create Automation</Button>}
        />
      </Panel>
    </div>
  );
}
