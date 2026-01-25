/**
 * Session Transcript
 *
 * Displays WebSocket stream events as a chat-like log.
 * Shows system progress, AI messages, and user messages.
 */

import { useRef, useEffect } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import type { KLTranscriptEntry } from '@/store/knowledge-library-store';

interface SessionTranscriptProps {
  entries: KLTranscriptEntry[];
  className?: string;
}

export function SessionTranscript({ entries, className }: SessionTranscriptProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new entries arrive
  useEffect(() => {
    if (scrollRef.current) {
      const scrollContainer = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
      }
    }
  }, [entries]);

  if (entries.length === 0) {
    return (
      <div className={cn('flex items-center justify-center text-muted-foreground', className)}>
        <p className="text-sm">Session activity will appear here...</p>
      </div>
    );
  }

  return (
    <ScrollArea className={className} ref={scrollRef}>
      <div className="p-4 space-y-3">
        {entries.map((entry) => (
          <TranscriptEntry key={entry.id} entry={entry} />
        ))}
      </div>
    </ScrollArea>
  );
}

interface TranscriptEntryProps {
  entry: KLTranscriptEntry;
}

function TranscriptEntry({ entry }: TranscriptEntryProps) {
  const isUser = entry.role === 'user';
  const isSystem = entry.role === 'system';
  const isError = entry.level === 'error';

  return (
    <div
      className={cn(
        'rounded-lg px-4 py-2 max-w-[85%]',
        isUser && 'ml-auto bg-primary text-primary-foreground',
        !isUser && !isSystem && 'bg-muted',
        isSystem && 'bg-transparent text-muted-foreground text-sm italic mx-auto text-center',
        isError && 'bg-destructive/10 text-destructive border border-destructive/20'
      )}
    >
      {!isSystem && (
        <div className="flex items-center gap-2 mb-1">
          <span
            className={cn(
              'text-xs font-medium uppercase',
              isUser ? 'text-primary-foreground/70' : 'text-muted-foreground'
            )}
          >
            {isUser ? 'You' : 'Assistant'}
          </span>
          {entry.timestamp && (
            <span
              className={cn(
                'text-xs',
                isUser ? 'text-primary-foreground/50' : 'text-muted-foreground/50'
              )}
            >
              {formatTime(entry.timestamp)}
            </span>
          )}
        </div>
      )}
      <p className="text-sm whitespace-pre-wrap">{entry.content}</p>
    </div>
  );
}

function formatTime(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}
