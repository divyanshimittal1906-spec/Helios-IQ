import { FolderKanban, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { Panel } from '@/components/ui/stat-card';

export default function ProjectsPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-200/80 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Projects</h1>
          <p className="mt-1 text-sm text-slate-500">
            Organize AI workforce tasks, documentation, and agent automations by business initiative.
          </p>
        </div>

        <Button size="sm">
          <Plus size={14} /> New Project
        </Button>
      </div>

      <Panel title="Active Projects" description="Initiatives managed by Helios IQ agents">
        <EmptyState
          icon={<FolderKanban size={24} />}
          title="No projects configured"
          description="Projects group tasks, knowledge bases, and agent runs under focused business goals."
          action={<Button size="sm">Create First Project</Button>}
        />
      </Panel>
    </div>
  );
}
