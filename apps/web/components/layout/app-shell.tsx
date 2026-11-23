'use client';

import { Sidebar } from '@/components/layout/sidebar';
import { TopNav } from '@/components/layout/top-nav';
import { LayoutProvider } from '@/components/layout/layout-context';

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <LayoutProvider>
      <div className="flex min-h-screen bg-slate-50 text-slate-900 antialiased">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopNav />
          <main className="flex-1 overflow-x-hidden p-6 lg:p-8 max-w-7xl w-full mx-auto">
            {children}
          </main>
        </div>
      </div>
    </LayoutProvider>
  );
}
