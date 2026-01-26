/**
 * Conversation List - Sidebar showing conversation history
 */

import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Spinner } from '@/components/ui/spinner';
import { MessageSquare, Plus, Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { KLConversation } from '@automaker/types';

interface ConversationListProps {
  conversations: KLConversation[];
  currentConversationId: string | null;
  isLoading: boolean;
  onSelectConversation: (conv: KLConversation) => void;
  onDeleteConversation: (convId: string) => void;
  onNewConversation: () => void;
}

export function ConversationList({
  conversations,
  currentConversationId,
  isLoading,
  onSelectConversation,
  onDeleteConversation,
  onNewConversation,
}: ConversationListProps) {
  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b">
        <Button onClick={onNewConversation} className="w-full" size="sm">
          <Plus className="h-4 w-4 mr-2" />
          New Conversation
        </Button>
      </div>

      {/* Conversation list */}
      <ScrollArea className="flex-1">
        {isLoading ? (
          <div className="flex items-center justify-center p-8">
            <Spinner size="md" />
          </div>
        ) : conversations.length === 0 ? (
          <div className="p-4 text-center text-muted-foreground">
            <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No conversations yet</p>
          </div>
        ) : (
          <div className="p-2 space-y-1">
            {conversations.map((conv) => (
              <ConversationItem
                key={conv.id}
                conversation={conv}
                isSelected={conv.id === currentConversationId}
                onSelect={() => onSelectConversation(conv)}
                onDelete={() => onDeleteConversation(conv.id)}
              />
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}

interface ConversationItemProps {
  conversation: KLConversation;
  isSelected: boolean;
  onSelect: () => void;
  onDelete: () => void;
}

function ConversationItem({ conversation, isSelected, onSelect, onDelete }: ConversationItemProps) {
  // Get first user message as preview
  const firstUserTurn = conversation.turns.find((t) => t.role === 'user');
  const preview = firstUserTurn?.content?.slice(0, 50) || 'Empty conversation';
  const title = conversation.title || preview;

  // Format date
  const date = new Date(conversation.updated_at);
  const dateStr = date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  });

  return (
    <div
      className={cn(
        'group flex items-start gap-2 p-2 rounded-lg cursor-pointer',
        'hover:bg-muted transition-colors',
        isSelected && 'bg-primary/10'
      )}
      onClick={onSelect}
    >
      <MessageSquare className="h-4 w-4 mt-1 text-muted-foreground shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{title}</p>
        <p className="text-xs text-muted-foreground">
          {conversation.turns.length} messages - {dateStr}
        </p>
      </div>
      <Button
        variant="ghost"
        size="sm"
        className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
      >
        <Trash2 className="h-3 w-3 text-muted-foreground hover:text-destructive" />
      </Button>
    </div>
  );
}
