import React from 'react';
import { cn } from '@/lib/utils';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'warning' | 'error' | 'neutral' | 'blue';
  dot?: boolean;
}

export function Badge({
  children,
  variant = 'default',
  dot = false,
  className,
  ...props
}: BadgeProps) {
  const variantStyles = {
    default: 'bg-slate-100 text-slate-700 border-slate-200/80',
    neutral: 'bg-slate-100 text-slate-700 border-slate-200/80',
    success: 'bg-emerald-50 text-emerald-700 border-emerald-200/80',
    warning: 'bg-amber-50 text-amber-700 border-amber-200/80',
    error: 'bg-rose-50 text-rose-700 border-rose-200/80',
    blue: 'bg-blue-50 text-blue-700 border-blue-200/80',
  };

  const dotStyles = {
    default: 'bg-slate-400',
    neutral: 'bg-slate-400',
    success: 'bg-emerald-500',
    warning: 'bg-amber-500',
    error: 'bg-rose-500',
    blue: 'bg-blue-500',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border transition-colors',
        variantStyles[variant],
        className
      )}
      {...props}
    >
      {dot && (
        <span
          className={cn('h-1.5 w-1.5 rounded-full shrink-0', dotStyles[variant])}
          aria-hidden="true"
        />
      )}
      {children}
    </span>
  );
}

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  const normalized = status.toLowerCase();

  let variant: 'success' | 'warning' | 'error' | 'neutral' | 'blue' = 'neutral';
  let label = status;

  if (normalized.includes('completed') || normalized === 'success') {
    variant = 'success';
    label = 'Completed';
  } else if (
    normalized.includes('running') ||
    normalized.includes('pending') ||
    normalized.includes('queued') ||
    normalized === 'in_progress'
  ) {
    variant = 'warning';
    label = normalized.includes('running') ? 'Running' : normalized.includes('pending') ? 'Pending' : 'Queued';
  } else if (normalized.includes('failed') || normalized.includes('error')) {
    variant = 'error';
    label = 'Failed';
  } else if (normalized === 'active' || normalized === 'available') {
    variant = 'success';
    label = normalized === 'available' ? 'Available' : 'Active';
  } else if (normalized === 'idle') {
    variant = 'neutral';
    label = 'Idle';
  }

  return (
    <Badge variant={variant} dot className={className}>
      {label}
    </Badge>
  );
}
