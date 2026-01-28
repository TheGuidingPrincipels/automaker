/**
 * Control Row
 *
 * Compact single-row control for session management.
 * Pre-session: Upload area + staged file info + Cleanup Mode selector + Start Session button
 * Active session: Mode toggle + Cancel Session button
 */

import { useState, useRef, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Upload, FileText, X, Play, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { WorkflowState } from '../../../hooks/use-session-workflow';
import { CleanupModeSelector } from './cleanup-mode-selector';
import { useKnowledgeLibraryStore } from '@/store/knowledge-library-store';

interface ControlRowProps {
  workflowState: WorkflowState;
  sessionId: string | null;
  contentMode: 'strict' | 'refinement' | undefined;
  stagedFile: { file: File; fileName: string } | null;
  isConnected: boolean;
  isStarting: boolean;
  isModeUpdating: boolean;
  onStageFile: (file: File) => void;
  onClearStagedFile: () => void;
  onStartSession: () => Promise<void>;
  onCancel: () => void;
  onModeChange: (checked: boolean) => void;
}

const workflowStateLabels: Record<WorkflowState, string> = {
  idle: 'Ready',
  file_staged: 'File Ready',
  creating_session: 'Creating...',
  cleanup_generating: 'Analyzing...',
  cleanup_review: 'Review Cleanup',
  routing_generating: 'Planning...',
  routing_review: 'Review Routing',
  ready_to_execute: 'Ready to Execute',
  executing: 'Executing...',
  completed: 'Completed',
  error: 'Error',
};

export function ControlRow({
  workflowState,
  sessionId,
  contentMode = 'strict',
  stagedFile,
  isConnected,
  isStarting,
  isModeUpdating,
  onStageFile,
  onClearStagedFile,
  onStartSession,
  onCancel,
  onModeChange,
}: ControlRowProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Cleanup mode from global store
  const cleanupMode = useKnowledgeLibraryStore((state) => state.cleanupMode);
  const setCleanupMode = useKnowledgeLibraryStore((state) => state.setCleanupMode);

  const hasActiveSession = !!sessionId;
  const canStartSession = !!stagedFile && !hasActiveSession && !isStarting;

  const isProcessing =
    workflowState === 'creating_session' ||
    workflowState === 'cleanup_generating' ||
    workflowState === 'routing_generating' ||
    workflowState === 'executing';
  const isComplete = workflowState === 'completed';
  const isError = workflowState === 'error';

  // File upload handlers
  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.currentTarget.files?.[0];
      if (file) {
        onStageFile(file);
      }
      e.currentTarget.value = '';
    },
    [onStageFile]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);

      const file = e.dataTransfer.files[0];
      if (file && (file.name.endsWith('.md') || file.type === 'text/markdown')) {
        onStageFile(file);
      }
    },
    [onStageFile]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  // Pre-session view: Upload + Staged file + Start
  if (!hasActiveSession) {
    return (
      <div className="flex items-center gap-3 px-4 py-2 border-b bg-muted/30 shrink-0">
        <input
          ref={fileInputRef}
          type="file"
          accept=".md,text/markdown"
          onChange={handleFileSelect}
          className="hidden"
        />

        {/* Upload area / Staged file display */}
        {!stagedFile ? (
          <div
            className={cn(
              'flex items-center gap-2 px-3 py-1.5 border-2 border-dashed rounded-lg',
              'cursor-pointer transition-colors',
              isDragOver && 'border-primary bg-primary/5',
              !isDragOver && 'border-muted-foreground/25 hover:border-muted-foreground/50'
            )}
            onClick={() => fileInputRef.current?.click()}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
          >
            <Upload
              className={cn('h-4 w-4', isDragOver ? 'text-primary' : 'text-muted-foreground')}
            />
            <span className="text-sm text-muted-foreground">
              {isDragOver ? 'Drop file here' : 'Upload .md file'}
            </span>
          </div>
        ) : (
          <div className="flex items-center gap-2 px-3 py-1.5 border rounded-lg bg-primary/5 border-primary/20">
            <FileText className="h-4 w-4 text-primary" />
            <span
              className="text-sm font-medium truncate max-w-[180px]"
              title={stagedFile.fileName}
            >
              {stagedFile.fileName}
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClearStagedFile}
              className="h-5 w-5 p-0 text-muted-foreground hover:text-destructive"
            >
              <X className="h-3 w-3" />
            </Button>
          </div>
        )}

        {/* Cleanup mode selector - shown when a file is staged */}
        {stagedFile && (
          <CleanupModeSelector
            value={cleanupMode}
            onChange={setCleanupMode}
            disabled={isStarting}
          />
        )}

        <div className="flex-1" />

        {/* Start session button */}
        <Button onClick={onStartSession} disabled={!canStartSession} loading={isStarting} size="sm">
          {isStarting ? (
            'Starting...'
          ) : (
            <>
              <Play className="h-4 w-4 mr-1.5" />
              Start Session
            </>
          )}
        </Button>
      </div>
    );
  }

  // Active session view: Mode toggle + Status + Cancel
  return (
    <div className="flex items-center gap-3 px-4 py-2 border-b bg-muted/30 shrink-0">
      {/* Mode toggle */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Mode:</span>
        <div className="flex items-center gap-1.5 text-xs">
          <span
            className={cn(
              contentMode === 'strict' ? 'text-foreground font-medium' : 'text-muted-foreground'
            )}
          >
            Strict
          </span>
          <Switch
            checked={contentMode === 'refinement'}
            onCheckedChange={onModeChange}
            disabled={isModeUpdating}
            className="h-4 w-7"
          />
          <span
            className={cn(
              contentMode === 'refinement' ? 'text-foreground font-medium' : 'text-muted-foreground'
            )}
          >
            Refine
          </span>
        </div>
      </div>

      <div className="flex-1" />

      {/* Status badge */}
      <Badge
        variant={isComplete ? 'default' : isError ? 'destructive' : 'outline'}
        className="text-xs"
      >
        {isProcessing && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
        {isComplete && <CheckCircle2 className="h-3 w-3 mr-1" />}
        {isError && <AlertCircle className="h-3 w-3 mr-1" />}
        {workflowStateLabels[workflowState]}
      </Badge>

      {!isConnected && (
        <Badge variant="outline" className="text-xs text-amber-600">
          Reconnecting...
        </Badge>
      )}

      {/* Cancel button */}
      <Button
        variant="ghost"
        size="sm"
        onClick={onCancel}
        className="text-muted-foreground hover:text-destructive"
      >
        <X className="h-4 w-4 mr-1" />
        Cancel
      </Button>
    </div>
  );
}
