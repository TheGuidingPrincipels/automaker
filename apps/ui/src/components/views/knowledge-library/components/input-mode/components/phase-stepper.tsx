/**
 * Phase Stepper
 *
 * Visual indicator for the session workflow phases: Cleanup → Routing → Execute.
 * Extracted from plan-review.tsx for reuse in the header.
 */

import { CheckCircle2, Circle, Loader2, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { WorkflowState } from '../../../hooks/use-session-workflow';

interface PhaseStepperProps {
  workflowState: WorkflowState;
  /** Compact mode for header use - smaller icons and text */
  compact?: boolean;
}

interface PhaseStepProps {
  label: string;
  isActive: boolean;
  isComplete: boolean;
  isLoading: boolean;
  compact?: boolean;
}

function PhaseStep({ label, isActive, isComplete, isLoading, compact }: PhaseStepProps) {
  const iconSize = compact ? 'h-4 w-4' : 'h-6 w-6';
  const innerIconSize = compact ? 'h-2.5 w-2.5' : 'h-3 w-3';
  const checkIconSize = compact ? 'h-3 w-3' : 'h-4 w-4';

  return (
    <div className="flex items-center gap-1.5">
      <div
        className={cn(
          'rounded-full flex items-center justify-center',
          iconSize,
          isComplete && 'bg-primary text-primary-foreground',
          isActive && !isComplete && 'bg-primary/20 border-2 border-primary',
          !isActive && !isComplete && 'bg-muted border-2 border-muted-foreground/20'
        )}
      >
        {isLoading ? (
          <Loader2 className={cn(innerIconSize, 'animate-spin')} />
        ) : isComplete ? (
          <CheckCircle2 className={checkIconSize} />
        ) : (
          <Circle className={innerIconSize} />
        )}
      </div>
      <span
        className={cn(
          'font-medium',
          compact ? 'text-xs' : 'text-sm',
          isActive ? 'text-foreground' : 'text-muted-foreground'
        )}
      >
        {label}
      </span>
    </div>
  );
}

export function PhaseStepper({ workflowState, compact = false }: PhaseStepperProps) {
  const isCleanupPhase =
    workflowState === 'cleanup_generating' || workflowState === 'cleanup_review';
  const isRoutingPhase =
    workflowState === 'routing_generating' || workflowState === 'routing_review';
  const isExecuteReady = workflowState === 'ready_to_execute';
  const isExecuting = workflowState === 'executing';
  const isCompleted = workflowState === 'completed';

  const arrowSize = compact ? 'h-3 w-3' : 'h-4 w-4';

  return (
    <div className={cn('flex items-center', compact ? 'gap-2' : 'gap-4')}>
      <PhaseStep
        label="Cleanup"
        isActive={isCleanupPhase}
        isComplete={
          !isCleanupPhase && (isRoutingPhase || isExecuteReady || isExecuting || isCompleted)
        }
        isLoading={workflowState === 'cleanup_generating'}
        compact={compact}
      />
      <ArrowRight className={cn(arrowSize, 'text-muted-foreground')} />
      <PhaseStep
        label="Routing"
        isActive={isRoutingPhase}
        isComplete={isExecuteReady || isExecuting || isCompleted}
        isLoading={workflowState === 'routing_generating'}
        compact={compact}
      />
      <ArrowRight className={cn(arrowSize, 'text-muted-foreground')} />
      <PhaseStep
        label="Execute"
        isActive={isExecuteReady || isExecuting}
        isComplete={isCompleted}
        isLoading={isExecuting}
        compact={compact}
      />
    </div>
  );
}
