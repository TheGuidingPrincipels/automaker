/**
 * Session List - Display existing Knowledge Library sessions
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Spinner } from '@/components/ui/spinner';
import { cn } from '@/lib/utils';
import { useKLSessions } from '@/hooks/queries/use-knowledge-library';
import { Clock, FolderOpen } from 'lucide-react';

interface SessionListProps {
  activeSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
}

const formatTimestamp = (value: string): string => new Date(value).toLocaleString();

export const SessionList = ({ activeSessionId, onSelectSession }: SessionListProps) => {
  const { data, isLoading, isError, error } = useKLSessions();

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium">Recent Sessions</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {isLoading && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Spinner size="sm" />
            Loading sessions...
          </div>
        )}

        {isError && (
          <p className="text-sm text-destructive">
            {error instanceof Error ? error.message : 'Failed to load sessions'}
          </p>
        )}

        {!isLoading && !isError && (data?.sessions.length ?? 0) === 0 && (
          <p className="text-sm text-muted-foreground">No sessions yet.</p>
        )}

        {data?.sessions.map((session) => (
          <div
            key={session.id}
            className={cn(
              'flex items-center justify-between gap-3 rounded-md border px-3 py-2',
              activeSessionId === session.id ? 'border-primary/40 bg-primary/5' : 'border-border'
            )}
          >
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <FolderOpen className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium truncate">
                  {session.source_file ?? 'Session'}
                </span>
              </div>
              <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" />
                <span>{formatTimestamp(session.updated_at)}</span>
                <Badge variant="outline" className="text-[10px]">
                  {session.phase}
                </Badge>
                <Badge variant="secondary" className="text-[10px]">
                  {session.content_mode}
                </Badge>
              </div>
            </div>
            <Button
              variant={activeSessionId === session.id ? 'secondary' : 'outline'}
              size="sm"
              onClick={() => onSelectSession(session.id)}
            >
              {activeSessionId === session.id ? 'Active' : 'Select'}
            </Button>
          </div>
        ))}
      </CardContent>
    </Card>
  );
};
