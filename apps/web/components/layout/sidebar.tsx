'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Activity,
  Bot,
  BriefcaseBusiness,
  Database,
  FolderKanban,
  LayoutDashboard,
  Settings,
  Workflow,
  X,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useLayout } from './layout-context';

interface NavItem {
  href: Route;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
}

const primaryNav: NavItem[] = [
  { href: '/command-center', label: 'Home', icon: LayoutDashboard },
  { href: '/ai-employees', label: 'AI Employees', icon: Bot },
  { href: '/tasks', label: 'Tasks', icon: BriefcaseBusiness },
  { href: '/knowledge', label: 'Knowledge', icon: Database },
  { href: '/analytics', label: 'Analytics', icon: Activity },
];

const secondaryNav: NavItem[] = [
  { href: '/projects', label: 'Projects', icon: FolderKanban },
  { href: '/automations', label: 'Automations', icon: Workflow },
  { href: '/integrations', label: 'Integrations', icon: Zap },
  { href: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarOpen, setSidebarOpen } = useLayout();

  const isNavActive = (href: string) => {
    if (href === '/command-center' && (pathname === '/' || pathname === '/command-center')) {
      return true;
    }
    return pathname === href;
  };

  const navContent = (
    <div className="flex h-full flex-col justify-between">
      <div>
        {/* Brand Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <Link
            href="/command-center"
            className="flex items-center gap-2.5 transition opacity-90 hover:opacity-100"
            onClick={() => setSidebarOpen(false)}
          >
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-600 text-xs font-bold text-white shadow-xs">
              H
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-sm font-semibold tracking-tight text-slate-900">Helios IQ</span>
            </div>
          </Link>
          <button
            type="button"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close sidebar"
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 md:hidden"
          >
            <X size={18} />
          </button>
        </div>

        {/* Primary Navigation */}
        <div className="px-3 py-3">
          <div className="px-3 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
            Workspace
          </div>
          <nav className="space-y-0.5">
            {primaryNav.map(({ href, label, icon: Icon }) => {
              const active = isNavActive(href);
              return (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setSidebarOpen(false)}
                  className={cn(
                    'flex items-center gap-2.5 rounded-lg px-3 py-2 text-xs font-medium transition-colors',
                    active
                      ? 'bg-blue-50 text-blue-700 font-semibold'
                      : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                  )}
                >
                  <Icon
                    size={15}
                    className={cn(
                      'shrink-0 transition-colors',
                      active ? 'text-blue-600' : 'text-slate-400'
                    )}
                  />
                  <span>{label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Secondary Navigation */}
        <div className="px-3 pt-2">
          <div className="px-3 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
            Manage
          </div>
          <nav className="space-y-0.5">
            {secondaryNav.map(({ href, label, icon: Icon }) => {
              const active = pathname === href;
              return (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setSidebarOpen(false)}
                  className={cn(
                    'flex items-center gap-2.5 rounded-lg px-3 py-2 text-xs font-medium transition-colors',
                    active
                      ? 'bg-blue-50 text-blue-700 font-semibold'
                      : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                  )}
                >
                  <Icon
                    size={15}
                    className={cn(
                      'shrink-0 transition-colors',
                      active ? 'text-blue-600' : 'text-slate-400'
                    )}
                  />
                  <span>{label}</span>
                </Link>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Footer Info / Status */}
      <div className="px-4 py-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
        <div className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          <span>Operational</span>
        </div>
        <span>v0.1</span>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop fixed sidebar */}
      <aside className="hidden h-screen w-56 shrink-0 flex-col border-r border-slate-200/80 bg-white md:flex sticky top-0">
        {navContent}
      </aside>

      {/* Mobile Drawer Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/30 backdrop-blur-xs md:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Mobile Drawer */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-60 bg-white shadow-xl transition-transform duration-200 ease-in-out md:hidden',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {navContent}
      </aside>
    </>
  );
}
