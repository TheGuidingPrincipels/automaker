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
 * Layout:
 * - Top: Review area (cleanup/routing phases) or empty state
 * - Bottom: Control dock (always visible with upload, transcript, and start)
 */

import { useSessionWorkflow } from '../../hooks/use-session-workflow';
import { ControlDock } from './control-dock';
import { DropzoneOverlay } from './dropzone-overlay';
import { EmptyState } from './empty-state';
import { PlanReview } from './plan-review';
import { ExecutionStatus } from './execution-status';
import { SessionList } from './session-list';
import { AlertCircle } from 'lucide-react';

export function InputMode() {
  const workflow = useSessionWorkflow();
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

  return (
    <DropzoneOverlay onFileDrop={actions.stageFile} disabled={!!sessionId}>
      <div className="h-full flex flex-col">
        {/* Error alert */}
        {error && (
          <div className="mx-4 mt-4 p-4 rounded-lg border border-destructive/50 bg-destructive/10 flex items-start gap-3 shrink-0">
            <AlertCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {/* Session list */}
        <div className="mx-4 mt-4 shrink-0">
          <SessionList activeSessionId={sessionId} onSelectSession={actions.selectSession} />
        </div>

        {/* Top area: Review content or empty state */}
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

        {/* Bottom dock: Always visible with upload, transcript, and start button */}
        <ControlDock
          workflowState={workflowState}
          sessionId={sessionId}
          isConnected={isConnected}
          stagedFile={stagedFile}
          onStageFile={actions.stageFile}
          onClearStagedFile={actions.clearStagedFile}
          onStartSession={actions.startSession}
          onCancel={actions.cancelSession}
          isStarting={isLoading.creating}
          transcript={transcript}
          pendingQuestions={pendingQuestions}
          onSendMessage={actions.sendMessage}
          onAnswerQuestion={actions.answerQuestion}
        />
      </div>
    </DropzoneOverlay>
  );
}
