import React from 'react';
import { Check, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface StepItem {
  id: string | number;
  label: string;
  detail?: string;
}

export function StepLoader({
  agentName = 'AI Agent',
  currentStepIndex = 1,
  steps,
  className,
}: {
  agentName?: string;
  currentStepIndex: number;
  steps: StepItem[];
  className?: string;
}) {
  return (
    <div className={cn('rounded-xl border border-slate-200/90 bg-white p-5 shadow-xs', className)}>
      <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-3">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-blue-600">{agentName}</span>
          <div className="text-sm font-medium text-slate-800">Working on your task...</div>
        </div>
        <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
      </div>

      <div className="space-y-2.5">
        {steps.map((step, index) => {
          const isCompleted = index < currentStepIndex;
          const isCurrent = index === currentStepIndex;
          const isPending = index > currentStepIndex;

          return (
            <div key={step.id} className="flex items-start gap-3 text-xs">
              <div className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full">
                {isCompleted ? (
                  <span className="flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500 text-white">
                    <Check size={10} strokeWidth={3} />
                  </span>
                ) : isCurrent ? (
                  <span className="flex h-3 w-3 items-center justify-center rounded-full bg-blue-600 ring-4 ring-blue-100" />
                ) : (
                  <span className="h-2 w-2 rounded-full border-2 border-slate-300" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <span
                  className={cn(
                    'font-medium transition-colors',
                    isCompleted && 'text-slate-700',
                    isCurrent && 'text-blue-700 font-semibold',
                    isPending && 'text-slate-400'
                  )}
                >
                  Step {index + 1}: {step.label}
                </span>
                {step.detail && (isCurrent || isCompleted) && (
                  <p className="mt-0.5 text-[11px] text-slate-500 truncate">{step.detail}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
