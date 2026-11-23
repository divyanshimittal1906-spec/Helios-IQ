import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

export function StatCard({
  title,
  value,
  accent,
  hint,
  icon,
}: {
  title: string;
  value: string;
  accent?: string;
  hint?: string;
  icon?: ReactNode;
}) {
  return (
    <div className="rounded-xl border border-slate-200/90 bg-white p-5 shadow-xs transition-all hover:border-slate-300">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</span>
        {icon ? (
          <div className="text-slate-400">{icon}</div>
        ) : accent ? (
          <span className={cn('h-2 w-2 rounded-full', accent.replace('bg-', 'bg-'))} />
        ) : null}
      </div>
      <div className="mt-2 text-2xl font-bold tracking-tight text-slate-900">{value}</div>
      {hint ? <p className="mt-1 text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
}

export function Panel({
  title,
  description,
  children,
  action,
  className,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn('rounded-xl border border-slate-200/90 bg-white shadow-xs', className)}>
      <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
          {description ? <p className="mt-0.5 text-xs text-slate-500">{description}</p> : null}
        </div>
        {action ? <div className="flex items-center gap-2">{action}</div> : null}
      </div>
      <div className="p-6">{children}</div>
    </section>
  );
}
