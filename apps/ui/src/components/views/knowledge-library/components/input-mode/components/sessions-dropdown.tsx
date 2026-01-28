/**
 * Sessions Dropdown
 *
 * Dropdown component for selecting existing Knowledge Library sessions.
 * Replaces the SessionList card with a more compact header-friendly design.
 */

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Spinner } from '@/components/ui/spinner';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { useKLSessions } from '@/hooks/queries/use-knowledge-library';
import { Clock, FolderOpen, ChevronDown, Check } from 'lucide-react';

interface SessionsDropdownProps {
  activeSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
}

const formatTimestamp = (value: string): string => {
  const date = new Date(value);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
};

export const truncateFileName = (name: string, maxLength = 20): string => {
  if (name.length <= maxLength) return name;

  const dotIndex = name.lastIndexOf('.');
  const hasExtension = dotIndex > 0 && dotIndex < name.length - 1;
  const ext = hasExtension ? name.slice(dotIndex) : '';
  const baseName = hasExtension ? name.slice(0, dotIndex) : name;
  const truncatedBase = baseName.slice(0, Math.max(0, maxLength - ext.length - 3));

  return `${truncatedBase}...${ext}`;
};

export function SessionsDropdown({ activeSessionId, onSelectSession }: SessionsDropdownProps) {
  const [open, setOpen] = useState(false);
  const { data, isLoading, isError, error } = useKLSessions();

  const sessions = data?.sessions ?? [];
  const activeSession = sessions.find((s) => s.id === activeSessionId);

  const handleSelect = (sessionId: string) => {
    onSelectSession(sessionId);
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2 h-8">
          <FolderOpen className="h-4 w-4" />
          <span className="max-w-[120px] truncate">
            {activeSession ? truncateFileName(activeSession.source_file ?? 'Session') : 'Sessions'}
          </span>
          <ChevronDown className={cn('h-3 w-3 transition-transform', open && 'rotate-180')} />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 p-0">
        <div className="p-3 border-b">
          <h4 className="font-medium text-sm">Recent Sessions</h4>
          <p className="text-xs text-muted-foreground mt-0.5">
            {sessions.length} session{sessions.length !== 1 ? 's' : ''} available
          </p>
        </div>

        {isLoading && (
          <div className="flex items-center justify-center gap-2 p-6 text-sm text-muted-foreground">
            <Spinner size="sm" />
            Loading sessions...
          </div>
        )}

        {isError && (
          <div className="p-4 text-sm text-destructive">
            {error instanceof Error ? error.message : 'Failed to load sessions'}
          </div>
        )}

        {!isLoading && !isError && sessions.length === 0 && (
          <div className="p-6 text-center text-sm text-muted-foreground">
            No sessions yet. Upload a file to create one.
          </div>
        )}

        {!isLoading && !isError && sessions.length > 0 && (
          <ScrollArea className="max-h-[280px]">
            <div className="p-2 space-y-1">
              {sessions.map((session) => {
                const isActive = activeSessionId === session.id;
                return (
                  <button
                    key={session.id}
                    onClick={() => handleSelect(session.id)}
                    className={cn(
                      'w-full flex items-start gap-3 rounded-md px-3 py-2 text-left transition-colors',
                      'hover:bg-accent/50',
                      isActive && 'bg-accent'
                    )}
                  >
                    <FolderOpen className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium truncate">
                          {session.source_file ?? 'Session'}
                        </span>
                        {isActive && <Check className="h-3.5 w-3.5 text-primary shrink-0" />}
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatTimestamp(session.updated_at)}
                        </span>
                        <Badge variant="outline" className="text-[10px] h-4 px-1">
                          {session.phase}
                        </Badge>
                        <Badge variant="secondary" className="text-[10px] h-4 px-1">
                          {session.content_mode}
                        </Badge>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </ScrollArea>
        )}
      </PopoverContent>
    </Popover>
  );
}
