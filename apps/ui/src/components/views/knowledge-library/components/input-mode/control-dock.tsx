/**
 * Control Dock
 *
 * Bottom dock that's always visible during the Input Mode workflow.
 * Contains:
 * - Left: Session controls (start button when file staged, cancel when active)
 * - Center: Transcript + message input
 * - Right: Upload area (drag/drop + file picker)
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Send,
  X,
  MessageSquare,
  HelpCircle,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Upload,
  FileText,
  Play,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { KLTranscriptEntry } from '@/store/knowledge-library-store';
import type { WorkflowState, PendingQuestion } from '../../hooks/use-session-workflow';

interface ControlDockProps {
  // Session state
  workflowState: WorkflowState;
  sessionId: string | null;
  isConnected: boolean;

  // Staged file
  stagedFile: { file: File; fileName: string } | null;
  onStageFile: (file: File) => void;
  onClearStagedFile: () => void;

  // Session actions
  onStartSession: () => Promise<void>;
  onCancel: () => void;
  isStarting: boolean;

  // Transcript
  transcript: KLTranscriptEntry[];
  pendingQuestions: PendingQuestion[];
  onSendMessage: (message: string) => void;
  onAnswerQuestion: (questionId: string, answer: string) => void;
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

export function ControlDock({
  workflowState,
  sessionId,
  isConnected,
  stagedFile,
  onStageFile,
  onClearStagedFile,
  onStartSession,
  onCancel,
  isStarting,
  transcript,
  pendingQuestions,
  onSendMessage,
  onAnswerQuestion,
}: ControlDockProps) {
  const [message, setMessage] = useState('');
  const [answerInputs, setAnswerInputs] = useState<Record<string, string>>({});
  const [isDragOver, setIsDragOver] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [transcript]);

  const handleSendMessage = () => {
    if (!message.trim()) return;
    onSendMessage(message);
    setMessage('');
  };

  const handleAnswerQuestion = (questionId: string) => {
    const answer = answerInputs[questionId];
    if (!answer?.trim()) return;
    onAnswerQuestion(questionId, answer);
    setAnswerInputs((prev) => {
      const { [questionId]: _, ...rest } = prev;
      return rest;
    });
  };

  // File upload handlers
  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.currentTarget.files?.[0];
      if (file) {
        onStageFile(file);
      }
      // Reset input so same file can be selected again
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

  const isProcessing =
    workflowState === 'creating_session' ||
    workflowState === 'cleanup_generating' ||
    workflowState === 'routing_generating' ||
    workflowState === 'executing';

  const isComplete = workflowState === 'completed';
  const isError = workflowState === 'error';
  const hasActiveSession = !!sessionId;
  const canStartSession = !!stagedFile && !hasActiveSession && !isStarting;

  return (
    <Card className="mx-4 mb-4 border-t">
      <div className="p-4">
        {/* Three-column layout */}
        <div className="flex gap-4">
          {/* Left Column: Start/Cancel Controls */}
          <div className="w-48 shrink-0 flex flex-col justify-center">
            {!hasActiveSession ? (
              // Pre-session: Start button
              <div className="space-y-2">
                <Button
                  onClick={onStartSession}
                  disabled={!canStartSession}
                  loading={isStarting}
                  className="w-full h-11 rounded-xl"
                >
                  {isStarting ? (
                    'Starting...'
                  ) : (
                    <>
                      <Play className="h-4 w-4 mr-2" />
                      Start Session
                    </>
                  )}
                </Button>
                {stagedFile && (
                  <p className="text-xs text-muted-foreground text-center">Ready to process file</p>
                )}
                {!stagedFile && (
                  <p className="text-xs text-muted-foreground text-center">
                    Upload a file to begin
                  </p>
                )}
              </div>
            ) : (
              // Active session: Status + Cancel
              <div className="space-y-2">
                <Badge
                  variant={isComplete ? 'default' : isError ? 'destructive' : 'outline'}
                  className="w-full justify-center py-1.5"
                >
                  {isProcessing && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
                  {isComplete && <CheckCircle2 className="h-3 w-3 mr-1" />}
                  {isError && <AlertCircle className="h-3 w-3 mr-1" />}
                  {workflowStateLabels[workflowState]}
                </Badge>
                {!isConnected && (
                  <Badge variant="outline" className="w-full justify-center text-amber-600">
                    Reconnecting...
                  </Badge>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onCancel}
                  className="w-full text-muted-foreground hover:text-destructive"
                >
                  <X className="h-4 w-4 mr-1" />
                  Cancel Session
                </Button>
              </div>
            )}
          </div>

          {/* Center Column: Transcript + Input */}
          <div className="flex-1 min-w-0">
            {/* Header */}
            <div className="flex items-center gap-2 mb-2">
              <MessageSquare className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Session Activity</span>
            </div>

            {/* Transcript area */}
            <ScrollArea className="h-24 rounded-md border bg-muted/30 mb-3" ref={scrollRef}>
              <div className="p-3 space-y-2">
                {transcript.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    {hasActiveSession
                      ? 'Session activity will appear here...'
                      : 'Start a session to see activity'}
                  </p>
                ) : (
                  transcript.map((entry) => (
                    <div
                      key={entry.id}
                      className={cn(
                        'text-sm rounded-md px-3 py-2',
                        entry.role === 'user' && 'bg-primary/10 ml-8',
                        entry.role === 'assistant' && 'bg-muted mr-8',
                        entry.role === 'system' &&
                          'bg-transparent text-muted-foreground italic text-xs',
                        entry.level === 'error' && 'text-destructive bg-destructive/10'
                      )}
                    >
                      {entry.role !== 'system' && (
                        <span className="font-medium text-xs uppercase text-muted-foreground mb-1 block">
                          {entry.role === 'user' ? 'You' : 'Assistant'}
                        </span>
                      )}
                      <span>{entry.content}</span>
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>

            {/* Pending questions */}
            {pendingQuestions.length > 0 && (
              <div className="mb-3 space-y-2">
                {pendingQuestions.map((question) => (
                  <div
                    key={question.id}
                    className="bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-md p-3"
                  >
                    <div className="flex items-start gap-2 mb-2">
                      <HelpCircle className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" />
                      <p className="text-sm text-amber-800 dark:text-amber-200">
                        {question.question}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Input
                        placeholder="Type your answer..."
                        value={answerInputs[question.id] ?? ''}
                        onChange={(e) =>
                          setAnswerInputs((prev) => ({
                            ...prev,
                            [question.id]: e.target.value,
                          }))
                        }
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            handleAnswerQuestion(question.id);
                          }
                        }}
                        className="flex-1"
                      />
                      <Button
                        size="sm"
                        onClick={() => handleAnswerQuestion(question.id)}
                        disabled={!answerInputs[question.id]?.trim()}
                      >
                        Answer
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Message input */}
            <div className="flex gap-2">
              <Input
                placeholder={
                  hasActiveSession ? 'Send guidance or feedback...' : 'Start a session first...'
                }
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                disabled={!hasActiveSession || isComplete || isError}
                className="flex-1 rounded-xl"
              />
              <Button
                onClick={handleSendMessage}
                disabled={!message.trim() || !hasActiveSession || isComplete || isError}
                size="icon"
                className="h-9 w-9 rounded-xl"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>

            <p className="text-xs text-muted-foreground mt-2">
              Press <kbd className="px-1 py-0.5 bg-muted rounded text-xs">Enter</kbd> to send
            </p>
          </div>

          {/* Right Column: Upload Area */}
          <div className="w-48 shrink-0">
            <input
              ref={fileInputRef}
              type="file"
              accept=".md,text/markdown"
              onChange={handleFileSelect}
              className="hidden"
              disabled={hasActiveSession}
            />

            <div
              className={cn(
                'h-full min-h-[120px] border-2 border-dashed rounded-xl p-4',
                'flex flex-col items-center justify-center text-center',
                'transition-colors duration-200',
                isDragOver && 'border-primary bg-primary/5',
                !isDragOver && 'border-muted-foreground/25 hover:border-muted-foreground/50',
                hasActiveSession && 'opacity-50 cursor-not-allowed',
                !hasActiveSession && 'cursor-pointer'
              )}
              onClick={() => !hasActiveSession && fileInputRef.current?.click()}
              onDrop={!hasActiveSession ? handleDrop : undefined}
              onDragOver={!hasActiveSession ? handleDragOver : undefined}
              onDragLeave={!hasActiveSession ? handleDragLeave : undefined}
            >
              {stagedFile ? (
                // File staged
                <div className="space-y-2">
                  <div className="mx-auto p-2 bg-primary/10 rounded-full w-fit">
                    <FileText className="h-6 w-6 text-primary" />
                  </div>
                  <div className="flex items-center gap-1">
                    <span
                      className="text-sm font-medium truncate max-w-[120px]"
                      title={stagedFile.fileName}
                    >
                      {stagedFile.fileName}
                    </span>
                    {!hasActiveSession && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          onClearStagedFile();
                        }}
                        className="h-5 w-5 p-0 text-muted-foreground hover:text-destructive"
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">Ready to upload</p>
                </div>
              ) : (
                // No file
                <div className="space-y-2">
                  <Upload
                    className={cn(
                      'h-8 w-8 mx-auto',
                      isDragOver ? 'text-primary' : 'text-muted-foreground'
                    )}
                  />
                  <p className="text-sm font-medium">
                    {isDragOver ? 'Drop file here' : 'Upload File'}
                  </p>
                  <p className="text-xs text-muted-foreground">Drag & drop or click to select</p>
                  <p className="text-xs text-muted-foreground">.md files only</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}
