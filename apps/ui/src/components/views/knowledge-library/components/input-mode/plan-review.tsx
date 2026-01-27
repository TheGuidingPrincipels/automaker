/**
 * Plan Review
 *
 * Container for reviewing cleanup and routing plans.
 * Shows the current phase and allows user to make decisions.
 */

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { CheckCircle2, Circle, Loader2, ArrowRight, Play } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  useKLCleanupPlan,
  useKLRoutingPlan,
  useKLDecideCleanupItem,
  useKLSelectDestination,
  useKLRejectBlock,
  useKLSetMode,
  useKLSession,
} from '@/hooks/queries/use-knowledge-library';
import type { WorkflowState } from '../../hooks/use-session-workflow';

import { CleanupReview } from './components/cleanup-review';
import { RoutingReview } from './components/routing-review';

interface PlanReviewProps {
  sessionId: string;
  workflowState: WorkflowState;
  onApproveCleanup: () => Promise<void>;
  onApproveRouting: () => Promise<void>;
  onExecute: () => Promise<void>;
  isLoading: {
    cleanup: boolean;
    routing: boolean;
    executing: boolean;
  };
}

export function PlanReview({
  sessionId,
  workflowState,
  onApproveCleanup,
  onApproveRouting,
  onExecute,
  isLoading,
}: PlanReviewProps) {
  const cleanupPlan = useKLCleanupPlan(sessionId);
  const routingPlan = useKLRoutingPlan(sessionId);
  const sessionQuery = useKLSession(sessionId);
  const decideCleanupMutation = useKLDecideCleanupItem(sessionId);
  const selectDestinationMutation = useKLSelectDestination(sessionId);
  const rejectBlockMutation = useKLRejectBlock(sessionId);
  const setModeMutation = useKLSetMode(sessionId);

  const isCleanupPhase =
    workflowState === 'cleanup_generating' || workflowState === 'cleanup_review';
  const isRoutingPhase =
    workflowState === 'routing_generating' || workflowState === 'routing_review';
  const isExecuteReady = workflowState === 'ready_to_execute';
  const contentMode = sessionQuery.data?.content_mode ?? 'strict';

  const handleModeChange = async (checked: boolean) => {
    const nextMode = checked ? 'refinement' : 'strict';
    try {
      await setModeMutation.mutateAsync(nextMode);
    } catch (error) {
      console.error('Failed to update content mode:', error);
    }
  };

  return (
    <div className="h-full flex flex-col p-4">
      {/* Phase indicator */}
      <div className="flex flex-col gap-4 mb-4 shrink-0">
        <div className="flex items-center justify-center gap-4">
          <PhaseStep
            label="Cleanup"
            isActive={isCleanupPhase}
            isComplete={!isCleanupPhase && (isRoutingPhase || isExecuteReady)}
            isLoading={workflowState === 'cleanup_generating'}
          />
          <ArrowRight className="h-4 w-4 text-muted-foreground" />
          <PhaseStep
            label="Routing"
            isActive={isRoutingPhase}
            isComplete={isExecuteReady}
            isLoading={workflowState === 'routing_generating'}
          />
          <ArrowRight className="h-4 w-4 text-muted-foreground" />
          <PhaseStep
            label="Execute"
            isActive={isExecuteReady}
            isComplete={false}
            isLoading={false}
          />
        </div>

        <ModeToggle
          contentMode={contentMode}
          isUpdating={setModeMutation.isPending}
          isDisabled={!sessionQuery.data}
          onToggle={handleModeChange}
        />
      </div>

      {/* Content area */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {workflowState === 'cleanup_generating' && (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
              <p className="text-muted-foreground">Analyzing content for cleanup...</p>
            </div>
          </div>
        )}

        {workflowState === 'cleanup_review' && (
          <CleanupReview
            data={cleanupPlan.data}
            isLoading={cleanupPlan.isLoading}
            onApprove={onApproveCleanup}
            onDecide={async (blockId, disposition) => {
              await decideCleanupMutation.mutateAsync({ blockId, disposition });
            }}
            isApproving={isLoading.cleanup}
          />
        )}

        {workflowState === 'routing_generating' && (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
              <p className="text-muted-foreground">Generating routing suggestions...</p>
            </div>
          </div>
        )}

        {workflowState === 'routing_review' && (
          <RoutingReview
            data={routingPlan.data}
            isLoading={routingPlan.isLoading}
            onApprove={onApproveRouting}
            isApproving={isLoading.routing}
            onSelectOption={async (blockId, optionIndex, payload) => {
              await selectDestinationMutation.mutateAsync({
                blockId,
                data: { option_index: optionIndex, ...payload },
              });
            }}
            onRejectBlock={async (blockId) => {
              await rejectBlockMutation.mutateAsync(blockId);
            }}
          />
        )}

        {workflowState === 'ready_to_execute' && (
          <ExecuteReady onExecute={onExecute} isExecuting={isLoading.executing} />
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Phase Step Indicator
// ============================================================================

interface PhaseStepProps {
  label: string;
  isActive: boolean;
  isComplete: boolean;
  isLoading: boolean;
}

function PhaseStep({ label, isActive, isComplete, isLoading }: PhaseStepProps) {
  return (
    <div className="flex items-center gap-2">
      <div
        className={cn(
          'h-6 w-6 rounded-full flex items-center justify-center',
          isComplete && 'bg-primary text-primary-foreground',
          isActive && !isComplete && 'bg-primary/20 border-2 border-primary',
          !isActive && !isComplete && 'bg-muted border-2 border-muted-foreground/20'
        )}
      >
        {isLoading ? (
          <Loader2 className="h-3 w-3 animate-spin" />
        ) : isComplete ? (
          <CheckCircle2 className="h-4 w-4" />
        ) : (
          <Circle className="h-3 w-3" />
        )}
      </div>
      <span
        className={cn(
          'text-sm font-medium',
          isActive ? 'text-foreground' : 'text-muted-foreground'
        )}
      >
        {label}
      </span>
    </div>
  );
}

// ============================================================================
// Mode Toggle
// ============================================================================

interface ModeToggleProps {
  contentMode: 'strict' | 'refinement';
  isUpdating: boolean;
  isDisabled: boolean;
  onToggle: (checked: boolean) => void;
}

const ModeToggle = ({ contentMode, isUpdating, isDisabled, onToggle }: ModeToggleProps) => (
  <div className="flex items-center justify-between rounded-lg border bg-muted/30 px-3 py-2">
    <div className="flex items-center gap-2">
      <span className="text-xs text-muted-foreground">Mode</span>
      <Badge variant="outline" className="text-[10px] uppercase">
        {contentMode}
      </Badge>
    </div>
    <div className="flex items-center gap-2 text-xs">
      <span className={cn(contentMode === 'strict' ? 'text-foreground' : 'text-muted-foreground')}>
        Strict
      </span>
      <Switch
        checked={contentMode === 'refinement'}
        onCheckedChange={onToggle}
        disabled={isDisabled || isUpdating}
      />
      <span
        className={cn(contentMode === 'refinement' ? 'text-foreground' : 'text-muted-foreground')}
      >
        Refinement
      </span>
    </div>
  </div>
);

// ============================================================================
// Execute Ready
// ============================================================================

interface ExecuteReadyProps {
  onExecute: () => void;
  isExecuting: boolean;
}

function ExecuteReady({ onExecute, isExecuting }: ExecuteReadyProps) {
  return (
    <div className="h-full flex items-center justify-center">
      <Card className="max-w-md w-full">
        <CardHeader>
          <CardTitle className="text-center">Ready to Execute</CardTitle>
        </CardHeader>
        <CardContent className="text-center">
          <div className="mx-auto mb-6 p-4 bg-green-100 dark:bg-green-900/30 rounded-full w-fit">
            <CheckCircle2 className="h-12 w-12 text-green-600" />
          </div>
          <p className="text-muted-foreground mb-6">
            All blocks have been reviewed and routing decisions approved. Click below to write the
            blocks to your knowledge library.
          </p>
          <Button onClick={onExecute} disabled={isExecuting} className="w-full" size="lg">
            {isExecuting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Executing...
              </>
            ) : (
              <>
                <Play className="h-4 w-4 mr-2" />
                Execute Session
              </>
            )}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
