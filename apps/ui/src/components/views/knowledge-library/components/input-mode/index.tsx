/**
 * Input Mode Container
 *
 * Main container for the Knowledge Library Input Mode workflow.
 * Handles the full session lifecycle:
 * 1. File staging and upload
 * 2. Cleanup plan review
 * 3. Routing plan review
 * 4. Execution
 *
 * Layout (redesigned for more vertical space):
 * - Top: Control row (upload/mode toggle/session actions)
 * - Middle: Review area (cleanup/routing phases) or empty state - scrollable
 * - Bottom: Collapsible transcript (expandable)
 */

import type { UseSessionWorkflowResult } from '../../hooks/use-session-workflow';
import { useKLSession, useKLSetMode } from '@/hooks/queries/use-knowledge-library';
import { ControlRow } from './components/control-row';
import { CollapsibleTranscript } from './components/collapsible-transcript';
import { DropzoneOverlay } from './dropzone-overlay';
import { EmptyState } from './empty-state';
import { PlanReview } from './plan-review';
import { ExecutionStatus } from './execution-status';
import { AlertCircle } from 'lucide-react';

interface InputModeProps {
  workflow: UseSessionWorkflowResult;
}

export function InputMode({ workflow }: InputModeProps) {
  const {
    workflowState,
    sessionId,
    stagedFile,
    transcript,
    pendingQuestions,
    isConnected,
    error,
    isLoading,
    actions,
  } = workflow;

  // Get session data for mode toggle
  const sessionQuery = useKLSession(sessionId ?? undefined);
  const setModeMutation = useKLSetMode(sessionId ?? '');
  const contentMode = sessionQuery.data?.content_mode ?? 'strict';

  const handleModeChange = async (checked: boolean) => {
    const nextMode = checked ? 'refinement' : 'strict';
    try {
      await setModeMutation.mutateAsync(nextMode);
    } catch (err) {
      console.error('Failed to update content mode:', err);
    }
  };

  return (
    <DropzoneOverlay onFileDrop={actions.stageFile} disabled={!!sessionId}>
      <div className="h-full flex flex-col">
        {/* Error alert */}
        {error && (
          <div className="mx-4 mt-4 p-3 rounded-lg border border-destructive/50 bg-destructive/10 flex items-start gap-3 shrink-0">
            <AlertCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {/* Control Row - upload/mode toggle/session actions */}
        <ControlRow
          workflowState={workflowState}
          sessionId={sessionId}
          contentMode={contentMode}
          stagedFile={stagedFile}
          isConnected={isConnected}
          isStarting={isLoading.creating}
          isModeUpdating={setModeMutation.isPending}
          onStageFile={actions.stageFile}
          onClearStagedFile={actions.clearStagedFile}
          onStartSession={actions.startSession}
          onCancel={actions.cancelSession}
          onModeChange={handleModeChange}
        />

        {/* Main content area */}
        <div className="flex-1 min-h-0 overflow-hidden">
          {/* Empty/idle state - show when no session and no staged file */}
          {(workflowState === 'idle' || workflowState === 'file_staged') && <EmptyState />}

          {/* Creating session - show loading indicator */}
          {workflowState === 'creating_session' && (
            <div className="h-full flex items-center justify-center p-4">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
                <p className="text-muted-foreground">Creating session and uploading file...</p>
              </div>
            </div>
          )}

          {/* Plan review phases */}
          {(workflowState === 'cleanup_generating' ||
            workflowState === 'cleanup_review' ||
            workflowState === 'routing_generating' ||
            workflowState === 'routing_review' ||
            workflowState === 'ready_to_execute') &&
            sessionId && (
              <PlanReview
                sessionId={sessionId}
                workflowState={workflowState}
                onApproveCleanup={actions.approveCleanup}
                onApproveRouting={actions.approveRouting}
                onExecute={actions.execute}
                isLoading={isLoading}
              />
            )}

          {/* Executing - show loading indicator */}
          {workflowState === 'executing' && sessionId && (
            <div className="h-full flex items-center justify-center p-4">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
                <p className="text-muted-foreground">Executing session...</p>
                <p className="text-sm text-muted-foreground mt-2">
                  Writing blocks to your knowledge library
                </p>
              </div>
            </div>
          )}

          {/* Completed - show execution status */}
          {workflowState === 'completed' && sessionId && (
            <ExecutionStatus sessionId={sessionId} onReset={actions.reset} />
          )}

          {/* Error state */}
          {workflowState === 'error' && (
            <div className="h-full flex items-center justify-center p-4">
              <div className="text-center">
                <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
                <p className="text-destructive font-medium">An error occurred</p>
                <p className="text-sm text-muted-foreground mt-2">{error}</p>
                <button
                  onClick={actions.reset}
                  className="mt-4 text-sm text-primary hover:underline"
                >
                  Start over
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Collapsible transcript - only show when session is active */}
        {sessionId && (
          <CollapsibleTranscript
            transcript={transcript}
            pendingQuestions={pendingQuestions}
            sessionId={sessionId}
            isConnected={isConnected}
            onSendMessage={actions.sendMessage}
            onAnswerQuestion={actions.answerQuestion}
          />
        )}
      </div>
    </DropzoneOverlay>
  );
}
