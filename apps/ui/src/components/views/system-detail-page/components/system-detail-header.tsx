/**
 * System Detail Header - Header component for the System Detail page
 */

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, Play, Settings, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { System, SystemStatus } from '@automaker/types';

interface SystemDetailHeaderProps {
  system: System;
  onBack: () => void;
  onRun: () => void;
  isRunning: boolean;
}

const STATUS_COLORS: Record<SystemStatus, string> = {
  draft: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
  active: 'bg-green-500/10 text-green-500 border-green-500/20',
  archived: 'bg-gray-500/10 text-gray-500 border-gray-500/20',
};

export function SystemDetailHeader({ system, onBack, onRun, isRunning }: SystemDetailHeaderProps) {
  return (
    <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center justify-between px-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={onBack}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>

          <div className="h-6 w-px bg-border" />

          <div className="flex items-center gap-3">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-semibold">{system.name}</h1>
                <Badge
                  variant="outline"
                  className={cn('text-xs capitalize', STATUS_COLORS[system.status])}
                >
                  {system.status}
                </Badge>
                {system.isBuiltIn && (
                  <Badge variant="secondary" className="text-xs">
                    Built-in
                  </Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                {system.agents.length} agents • {system.category || 'Uncategorized'}
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {!system.isBuiltIn && (
            <Button variant="outline" size="sm">
              <Settings className="mr-2 h-4 w-4" />
              Configure
            </Button>
          )}
          <Button size="sm" onClick={onRun} disabled={isRunning}>
            {isRunning ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Run System
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
