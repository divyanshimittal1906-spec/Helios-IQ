export type WorkspaceRole = 'admin' | 'member' | 'viewer';

export interface WorkspaceSummary {
  id: string;
  name: string;
  role: WorkspaceRole;
}
