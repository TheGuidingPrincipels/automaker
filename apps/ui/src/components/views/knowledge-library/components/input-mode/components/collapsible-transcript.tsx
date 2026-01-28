/**
 * Collapsible Transcript
 *
 * Bottom panel showing session activity with expand/collapse functionality.
 * Collapsed: Shows message count and quick input field.
 * Expanded: Full transcript area with pending questions and message input.
 */

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Send, MessageSquare, HelpCircle, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useKnowledgeLibraryStore, type KLTranscriptEntry } from '@/store/knowledge-library-store';
import type { PendingQuestion } from '../../../hooks/use-session-workflow';

interface CollapsibleTranscriptProps {
  transcript: KLTranscriptEntry[];
  pendingQuestions: PendingQuestion[];
  sessionId: string | null;
  isConnected: boolean;
  onSendMessage: (message: string) => void;
  onAnswerQuestion: (questionId: string, answer: string) => void;
}

export function CollapsibleTranscript({
  transcript,
  pendingQuestions,
  sessionId,
  isConnected,
  onSendMessage,
  onAnswerQuestion,
}: CollapsibleTranscriptProps) {
  const { isTranscriptExpanded, setTranscriptExpanded } = useKnowledgeLibraryStore();
  const [message, setMessage] = useState('');
  const [answerInputs, setAnswerInputs] = useState<Record<string, string>>({});
  const scrollRef = useRef<HTMLDivElement>(null);

  const hasActiveSession = !!sessionId;

  // Auto-expand when there are pending questions
  useEffect(() => {
    if (pendingQuestions.length > 0 && !isTranscriptExpanded) {
      setTranscriptExpanded(true);
    }
  }, [pendingQuestions.length, isTranscriptExpanded, setTranscriptExpanded]);

  // Auto-scroll to bottom when new messages arrive (only when expanded)
  useEffect(() => {
    if (!isTranscriptExpanded) return;
    if (!scrollRef.current) return;

    const scrollContainer = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]');
    if (!scrollContainer) return;

    scrollContainer.scrollTop = scrollContainer.scrollHeight;
  }, [transcript, isTranscriptExpanded]);

  const handleSendMessage = () => {
    if (!message.trim()) return;
    onSendMessage(message);
    setMessage('');
  };

  const handleAnswerQuestion = (questionId: string) => {
    const answer = answerInputs[questionId];
    if (!answer?.trim()) return;
    onAnswerQuestion(questionId, answer);
    setAnswerInputs(({ [questionId]: _, ...rest }) => rest);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Get last message for collapsed view preview
  const lastMessage = transcript[transcript.length - 1];
  const lastMessagePreview = lastMessage
    ? `${lastMessage.role === 'user' ? 'You: ' : ''}${lastMessage.content.slice(0, 50)}${lastMessage.content.length > 50 ? '...' : ''}`
    : null;

  return (
    <Collapsible
      open={isTranscriptExpanded}
      onOpenChange={setTranscriptExpanded}
      className="border-t bg-card shrink-0"
    >
      {/* Collapsed header with quick input */}
      <div className="flex items-center gap-2 px-4 py-2">
        <CollapsibleTrigger asChild>
          <Button variant="ghost" size="sm" className="gap-2 px-2 shrink-0">
            <ChevronRight
              className={cn('h-4 w-4 transition-transform', isTranscriptExpanded && 'rotate-90')}
            />
            <MessageSquare className="h-4 w-4" />
            <span className="text-sm font-medium">Session Activity</span>
            {transcript.length > 0 && (
              <span className="text-xs text-muted-foreground">({transcript.length})</span>
            )}
            {pendingQuestions.length > 0 && (
              <span className="text-xs text-amber-600 font-medium ml-1">
                {pendingQuestions.length} question{pendingQuestions.length > 1 ? 's' : ''}
              </span>
            )}
          </Button>
        </CollapsibleTrigger>

        {/* Quick input when collapsed */}
        {!isTranscriptExpanded && hasActiveSession && (
          <div className="flex-1 flex items-center gap-2">
            {lastMessagePreview && (
              <span className="text-xs text-muted-foreground truncate max-w-[200px]">
                {lastMessagePreview}
              </span>
            )}
            <div className="flex-1" />
            <Input
              placeholder="Quick message..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              className="h-7 text-xs max-w-[200px]"
            />
            <Button
              size="sm"
              variant="ghost"
              className="h-7 w-7 p-0"
              onClick={handleSendMessage}
              disabled={!message.trim()}
            >
              <Send className="h-3.5 w-3.5" />
            </Button>
          </div>
        )}

        {!isConnected && hasActiveSession && (
          <span className="text-xs text-amber-600 ml-auto">Reconnecting...</span>
        )}
      </div>

      {/* Expanded content */}
      <CollapsibleContent>
        <div className="px-4 pb-3 space-y-3">
          {/* Transcript area */}
          <ScrollArea className="h-24 rounded-md border bg-muted/30" ref={scrollRef}>
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
            <div className="space-y-2">
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
              onKeyDown={handleKeyDown}
              disabled={!hasActiveSession}
              className="flex-1"
            />
            <Button
              onClick={handleSendMessage}
              disabled={!message.trim() || !hasActiveSession}
              size="icon"
              className="h-9 w-9"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Press <kbd className="px-1 py-0.5 bg-muted rounded text-xs">Enter</kbd> to send
          </p>
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
