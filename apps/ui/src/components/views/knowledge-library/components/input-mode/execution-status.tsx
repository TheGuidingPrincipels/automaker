/**
 * Execution Status
 *
 * Shows the result of session execution.
 * Displays success/failure information and allows starting a new session.
 */

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { CheckCircle2, AlertTriangle, RefreshCw, FileText, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useKLSession } from '@/hooks/queries/use-knowledge-library';

interface ExecutionStatusProps {
  sessionId: string;
  onReset: () => void;
}

export function ExecutionStatus({ sessionId, onReset }: ExecutionStatusProps) {
  const session = useKLSession(sessionId);

  if (session.isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  const data = session.data;
  if (!data) {
    return (
      <div className="h-full flex items-center justify-center p-4">
        <Card className="max-w-md w-full">
          <CardContent className="pt-6 text-center">
            <AlertTriangle className="h-12 w-12 text-amber-500 mx-auto mb-4" />
            <p className="text-muted-foreground mb-4">Could not load session details</p>
            <Button onClick={onReset}>Start New Session</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const hasErrors = data.errors && data.errors.length > 0;
  const isFullSuccess = !hasErrors && data.kept_blocks === data.total_blocks;

  return (
    <div className="h-full flex items-center justify-center p-4">
      <Card className="max-w-lg w-full">
        <CardHeader>
          <CardTitle className="text-center flex items-center justify-center gap-2">
            {isFullSuccess ? (
              <>
                <CheckCircle2 className="h-6 w-6 text-green-600" />
                Session Complete
              </>
            ) : hasErrors ? (
              <>
                <AlertTriangle className="h-6 w-6 text-amber-500" />
                Session Completed with Issues
              </>
            ) : (
              <>
                <CheckCircle2 className="h-6 w-6 text-green-600" />
                Session Complete
              </>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {/* Stats */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="text-center p-3 bg-muted rounded-lg">
              <p className="text-2xl font-bold">{data.total_blocks}</p>
              <p className="text-xs text-muted-foreground">Total Blocks</p>
            </div>
            <div className="text-center p-3 bg-green-50 dark:bg-green-900/30 rounded-lg">
              <p className="text-2xl font-bold text-green-600">{data.kept_blocks}</p>
              <p className="text-xs text-muted-foreground">Kept</p>
            </div>
            <div className="text-center p-3 bg-red-50 dark:bg-red-900/30 rounded-lg">
              <p className="text-2xl font-bold text-red-600">{data.discarded_blocks}</p>
              <p className="text-xs text-muted-foreground">Discarded</p>
            </div>
          </div>

          {/* Session info */}
          <div className="space-y-2 mb-6">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Source File</span>
              <span className="font-medium truncate max-w-[200px]" title={data.source_file ?? ''}>
                {data.source_file?.split('/').pop() ?? 'N/A'}
              </span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Content Mode</span>
              <Badge variant="outline">{data.content_mode}</Badge>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Completed At</span>
              <span className="font-medium">{new Date(data.updated_at).toLocaleString()}</span>
            </div>
          </div>

          {/* Errors */}
          {hasErrors && (
            <div className="mb-6 p-4 rounded-lg border border-destructive/50 bg-destructive/10">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-destructive mb-2">Some issues occurred:</p>
                  <ScrollArea className="max-h-24">
                    <ul className="list-disc list-inside space-y-1">
                      {data.errors.map((error, idx) => (
                        <li key={idx} className="text-sm text-destructive/90">
                          {error}
                        </li>
                      ))}
                    </ul>
                  </ScrollArea>
                </div>
              </div>
            </div>
          )}

          {/* Success message */}
          {isFullSuccess && (
            <div className="text-center mb-6 p-4 bg-green-50 dark:bg-green-900/30 rounded-lg">
              <CheckCircle2 className="h-8 w-8 text-green-600 mx-auto mb-2" />
              <p className="text-sm text-green-700 dark:text-green-300">
                All blocks have been successfully written to your knowledge library!
              </p>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <Button onClick={onReset} className="flex-1">
              <RefreshCw className="h-4 w-4 mr-2" />
              Start New Session
            </Button>
            <Button variant="outline" className="flex-1" asChild>
              <a
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  // Navigate to library browser - handled by parent
                }}
              >
                <FileText className="h-4 w-4 mr-2" />
                View Library
                <ArrowRight className="h-4 w-4 ml-2" />
              </a>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
