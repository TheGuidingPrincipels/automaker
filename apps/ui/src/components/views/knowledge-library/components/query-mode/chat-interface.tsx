/**
 * Chat Interface - Reusable chat UI component
 *
 * Note: This component provides the visual structure for a chat interface.
 * It's currently used by QueryMode but could be reused elsewhere.
 */

import { forwardRef, type ReactNode } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';

interface ChatInterfaceProps {
  children: ReactNode;
  className?: string;
}

/**
 * Chat container with proper scrolling behavior
 */
export const ChatInterface = forwardRef<HTMLDivElement, ChatInterfaceProps>(
  ({ children, className }, ref) => {
    return (
      <ScrollArea className={cn('flex-1', className)} ref={ref}>
        <div className="max-w-3xl mx-auto p-6 space-y-6">{children}</div>
      </ScrollArea>
    );
  }
);

ChatInterface.displayName = 'ChatInterface';

/**
 * Message bubble wrapper
 */
interface MessageBubbleProps {
  children: ReactNode;
  variant: 'user' | 'assistant' | 'system';
  className?: string;
}

export function MessageBubble({ children, variant, className }: MessageBubbleProps) {
  return (
    <div
      className={cn(
        'flex',
        variant === 'user' && 'justify-end',
        variant === 'assistant' && 'justify-start',
        variant === 'system' && 'justify-center'
      )}
    >
      <div
        className={cn(
          'max-w-[85%] rounded-lg px-4 py-2',
          variant === 'user' && 'bg-primary text-primary-foreground',
          variant === 'assistant' && 'bg-muted',
          variant === 'system' && 'text-sm text-muted-foreground italic',
          className
        )}
      >
        {children}
      </div>
    </div>
  );
}

/**
 * Typing indicator for when the AI is processing
 */
export function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-4 py-2">
      <div
        className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce"
        style={{ animationDelay: '0ms' }}
      />
      <div
        className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce"
        style={{ animationDelay: '150ms' }}
      />
      <div
        className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce"
        style={{ animationDelay: '300ms' }}
      />
    </div>
  );
}
