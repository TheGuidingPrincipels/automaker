/**
 * SessionTranscript Component
 *
 * A reusable component for displaying chat-like transcripts.
 * Shows messages from different roles (user, assistant, system) with
 * appropriate styling and auto-scroll functionality.
 *
 * @example
 * ```tsx
 * <SessionTranscript
 *   entries={[
 *     { id: '1', role: 'user', content: 'Hello!' },
 *     { id: '2', role: 'assistant', content: 'Hi there!' },
 *   ]}
 * />
 * ```
 */

import { useRef, useEffect } from 'react';
import { Bot, User, Info, AlertCircle } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';

// ============================================================================
// Types
// ============================================================================

/** Role of a transcript entry */
export type TranscriptRole = 'user' | 'assistant' | 'system';

/** Level/severity of a transcript entry */
export type TranscriptLevel = 'info' | 'error' | 'warning';

/** A single entry in the transcript */
export interface TranscriptEntry {
  /** Unique identifier for the entry */
  id: string;
  /** Role of the message sender */
  role: TranscriptRole;
  /** Message content */
  content: string;
  /** Optional timestamp (ISO string) */
  timestamp?: string;
  /** Optional level for styling (defaults to 'info') */
  level?: TranscriptLevel;
}

/** Props for the SessionTranscript component */
export interface SessionTranscriptProps {
  /** Array of transcript entries to display */
  entries: TranscriptEntry[];
  /** Optional className for the container */
  className?: string;
  /** Whether to show avatars for each entry (default: true) */
  showAvatars?: boolean;
  /** Whether to show timestamps (default: true) */
  showTimestamps?: boolean;
  /** Custom empty state message */
  emptyMessage?: string;
  /** Whether to auto-scroll to bottom on new entries (default: true) */
  autoScroll?: boolean;
  /** Compact mode with reduced padding (default: false) */
  compact?: boolean;
}

// ============================================================================
// Sub-components
// ============================================================================

interface EntryAvatarProps {
  role: TranscriptRole;
  level?: TranscriptLevel;
}

function EntryAvatar({ role, level }: EntryAvatarProps) {
  const isError = level === 'error';

  const avatarClasses = cn(
    'w-8 h-8 rounded-lg flex items-center justify-center shrink-0 shadow-sm',
    isError && 'bg-destructive/10 ring-1 ring-destructive/20',
    !isError && role === 'assistant' && 'bg-primary/10 ring-1 ring-primary/20',
    !isError && role === 'user' && 'bg-muted ring-1 ring-border',
    !isError && role === 'system' && 'bg-muted/50 ring-1 ring-border/50'
  );

  const iconClasses = 'w-4 h-4';

  return (
    <div className={avatarClasses}>
      {isError ? (
        <AlertCircle className={cn(iconClasses, 'text-destructive')} />
      ) : role === 'assistant' ? (
        <Bot className={cn(iconClasses, 'text-primary')} />
      ) : role === 'system' ? (
        <Info className={cn(iconClasses, 'text-muted-foreground')} />
      ) : (
        <User className={cn(iconClasses, 'text-muted-foreground')} />
      )}
    </div>
  );
}

interface EntryBubbleProps {
  entry: TranscriptEntry;
  showTimestamps: boolean;
  compact: boolean;
}

function EntryBubble({ entry, showTimestamps, compact }: EntryBubbleProps) {
  const isUser = entry.role === 'user';
  const isSystem = entry.role === 'system';
  const isError = entry.level === 'error';
  const isWarning = entry.level === 'warning';

  const bubbleClasses = cn(
    'rounded-xl',
    compact ? 'px-3 py-2' : 'px-4 py-3',
    'max-w-[85%] shadow-sm',
    // User messages
    isUser && 'bg-primary text-primary-foreground',
    // System messages
    isSystem &&
      !isError &&
      !isWarning &&
      'bg-muted/50 text-muted-foreground border border-border/50',
    // Assistant messages
    !isUser && !isSystem && !isError && !isWarning && 'bg-card border border-border',
    // Error state
    isError && 'bg-destructive/10 text-destructive border border-destructive/20',
    // Warning state
    isWarning && 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border border-yellow-500/20'
  );

  const roleLabel = isUser ? 'You' : isSystem ? 'System' : 'Assistant';

  return (
    <div className={bubbleClasses}>
      {/* Role label and timestamp */}
      <div className="flex items-center gap-2 mb-1">
        <span
          className={cn(
            'text-xs font-medium uppercase',
            isUser && 'text-primary-foreground/70',
            isSystem && 'text-muted-foreground/70',
            !isUser && !isSystem && !isError && !isWarning && 'text-muted-foreground',
            isError && 'text-destructive/70',
            isWarning && 'text-yellow-700/70 dark:text-yellow-400/70'
          )}
        >
          {roleLabel}
        </span>
        {showTimestamps && entry.timestamp && (
          <span
            className={cn(
              'text-xs',
              isUser && 'text-primary-foreground/50',
              !isUser && 'text-muted-foreground/50',
              isError && 'text-destructive/50',
              isWarning && 'text-yellow-700/50 dark:text-yellow-400/50'
            )}
          >
            {formatTime(entry.timestamp)}
          </span>
        )}
      </div>

      {/* Content */}
      <p className={cn('text-sm whitespace-pre-wrap leading-relaxed', compact && 'text-xs')}>
        {entry.content}
      </p>
    </div>
  );
}

interface TranscriptEntryRowProps {
  entry: TranscriptEntry;
  showAvatars: boolean;
  showTimestamps: boolean;
  compact: boolean;
}

function TranscriptEntryRow({
  entry,
  showAvatars,
  showTimestamps,
  compact,
}: TranscriptEntryRowProps) {
  const isUser = entry.role === 'user';

  return (
    <div className={cn('flex', compact ? 'gap-2' : 'gap-3', isUser ? 'flex-row-reverse' : '')}>
      {showAvatars && <EntryAvatar role={entry.role} level={entry.level} />}
      <EntryBubble entry={entry} showTimestamps={showTimestamps} compact={compact} />
    </div>
  );
}

// ============================================================================
// Utilities
// ============================================================================

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

// ============================================================================
// Main Component
// ============================================================================

export function SessionTranscript({
  entries,
  className,
  showAvatars = true,
  showTimestamps = true,
  emptyMessage = 'No messages yet...',
  autoScroll = true,
  compact = false,
}: SessionTranscriptProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new entries arrive
  useEffect(() => {
    if (!autoScroll) return;

    if (scrollRef.current) {
      const scrollContainer = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
      }
    }
  }, [entries, autoScroll]);

  // Empty state
  if (entries.length === 0) {
    return (
      <div
        className={cn('flex items-center justify-center text-muted-foreground h-full', className)}
      >
        <p className="text-sm">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <ScrollArea className={cn('h-full', className)} ref={scrollRef}>
      <div className={cn('space-y-4', compact ? 'p-3' : 'p-4')}>
        {entries.map((entry) => (
          <TranscriptEntryRow
            key={entry.id}
            entry={entry}
            showAvatars={showAvatars}
            showTimestamps={showTimestamps}
            compact={compact}
          />
        ))}
      </div>
    </ScrollArea>
  );
}

export default SessionTranscript;
