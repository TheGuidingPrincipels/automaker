/**
 * Knowledge Hub Header - Header component for the Knowledge Hub page
 */

import { BookOpenCheck } from 'lucide-react';

interface KnowledgeHubHeaderProps {
  totalItems: number;
}

export function KnowledgeHubHeader({ totalItems }: KnowledgeHubHeaderProps) {
  return (
    <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
            <BookOpenCheck className="h-4 w-4 text-primary" />
          </div>
          <div>
            <h1 className="text-lg font-semibold">Knowledge Hub</h1>
            <p className="text-xs text-muted-foreground">{totalItems} total items</p>
          </div>
        </div>
      </div>
    </div>
  );
}
