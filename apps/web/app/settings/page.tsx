import { Building, Shield, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Panel } from '@/components/ui/stat-card';
import { DEFAULT_WORKSPACE_ID } from '@/lib/api';

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div className="border-b border-slate-200/80 pb-5">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Settings</h1>
        <p className="mt-1 text-sm text-slate-500">
          Manage organization preferences, workspace configuration, and AI agent permissions.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Workspace Configuration" description="Current tenant scope and deployment parameters">
          <div className="space-y-4 text-xs">
            <div>
              <label className="block font-medium text-slate-700 mb-1">Workspace ID</label>
              <input
                type="text"
                disabled
                value={`Workspace #${DEFAULT_WORKSPACE_ID} (Enterprise Default)`}
                className="w-full rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-slate-600 font-mono"
              />
            </div>
            <div>
              <label className="block font-medium text-slate-700 mb-1">Organization Name</label>
              <input
                type="text"
                defaultValue="Helios Enterprise Demo"
                className="w-full rounded-lg border border-slate-200 bg-white p-2.5 text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
              />
            </div>
            <div className="pt-2">
              <Button size="sm">Save Preferences</Button>
            </div>
          </div>
        </Panel>

        <Panel title="Security & Compliance" description="Enterprise authentication and isolation">
          <div className="space-y-3 text-xs text-slate-600">
            <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50/50 p-3">
              <Shield size={16} className="text-emerald-600" />
              <div>
                <span className="font-semibold text-slate-800">Argon2 Password Hashing</span>
                <p className="text-[11px] text-slate-500">Industry-standard cryptographic credentials</p>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50/50 p-3">
              <Building size={16} className="text-blue-600" />
              <div>
                <span className="font-semibold text-slate-800">Multi-Tenant Isolation</span>
                <p className="text-[11px] text-slate-500">Workspace data scoped per tenant</p>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50/50 p-3">
              <User size={16} className="text-indigo-600" />
              <div>
                <span className="font-semibold text-slate-800">Signed JWT Tokens</span>
                <p className="text-[11px] text-slate-500">Secure session cookies and bearer authorization</p>
              </div>
            </div>
          </div>
        </Panel>
      </div>
    </div>
  );
}
