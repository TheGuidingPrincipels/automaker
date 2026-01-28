/**
 * Plan Review
 *
 * Container for reviewing cleanup and routing plans.
 * Shows the current phase content and allows user to make decisions.
 *
 * Note: Phase stepper is now in the header, mode toggle is in the control row.
 */

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CheckCircle2, Loader2, Play } from 'lucide-react';
import {
  useKLCleanupPlan,
  useKLSession,
  useKLRoutingPlan,
  useKLDecideCleanupItem,
  useKLSelectDestination,
  useKLRejectBlock,
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
  const sessionQuery = useKLSession(sessionId);
  const cleanupPlan = useKLCleanupPlan(sessionId);
  const routingPlan = useKLRoutingPlan(sessionId, sessionQuery.data?.phase);
  const decideCleanupMutation = useKLDecideCleanupItem(sessionId);
  const selectDestinationMutation = useKLSelectDestination(sessionId);
  const rejectBlockMutation = useKLRejectBlock(sessionId);

  return (
    <div className="h-full flex flex-col p-4">
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
            sessionId={sessionId}
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
