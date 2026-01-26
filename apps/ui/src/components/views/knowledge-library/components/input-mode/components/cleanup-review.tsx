import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { SkeletonPulse } from '@/components/ui/skeleton';
import { CheckCircle2, Trash2, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { useKLCleanupPlan } from '@/hooks/queries/use-knowledge-library';

interface CleanupReviewProps {
  data: ReturnType<typeof useKLCleanupPlan>['data'];
  isLoading: boolean;
  onApprove: () => void;
  onDecide: (blockId: string, disposition: 'keep' | 'discard') => Promise<void>;
  isApproving: boolean;
}

interface CleanupItemCardProps {
  item: NonNullable<ReturnType<typeof useKLCleanupPlan>['data']>['items'][number];
  isDeciding: boolean;
  onDecide: (blockId: string, disposition: 'keep' | 'discard') => void;
}

function CleanupItemCard({ item, isDeciding, onDecide }: CleanupItemCardProps) {
  const isDecided = item.final_disposition !== null;
  const isKeep = item.final_disposition === 'keep';

  return (
    <Card className={cn(isDecided && 'opacity-60')}>
      <CardContent className="pt-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="outline" className="text-xs">
                {item.heading_path.join(' > ')}
              </Badge>
              {isDecided && (
                <Badge variant={isKeep ? 'default' : 'destructive'} className="text-xs">
                  {item.final_disposition}
                </Badge>
              )}
            </div>
            <p className="text-sm line-clamp-2 text-muted-foreground">{item.content_preview}</p>
            <p className="text-xs text-muted-foreground mt-2 italic">
              AI suggests: {item.suggested_disposition} - {item.suggestion_reason}
            </p>
          </div>

          {!isDecided && (
            <div className="flex gap-2 shrink-0">
              <Button
                variant="outline"
                size="sm"
                className="text-green-600 hover:bg-green-50"
                onClick={() => onDecide(item.block_id, 'keep')}
                disabled={isDeciding}
              >
                <CheckCircle2 className="h-4 w-4 mr-1" />
                Keep
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="text-red-600 hover:bg-red-50"
                onClick={() => onDecide(item.block_id, 'discard')}
                disabled={isDeciding}
              >
                <Trash2 className="h-4 w-4 mr-1" />
                Discard
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function CleanupReview({
  data,
  isLoading,
  onApprove,
  onDecide,
  isApproving,
}: CleanupReviewProps) {
  const [decidingBlockId, setDecidingBlockId] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <SkeletonPulse className="h-24 w-full" />
        <SkeletonPulse className="h-24 w-full" />
        <SkeletonPulse className="h-24 w-full" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center text-muted-foreground">
        <p>No cleanup plan available</p>
      </div>
    );
  }

  const decidedItems = data.items.filter((item) => item.final_disposition !== null);

  const handleDecision = async (blockId: string, disposition: 'keep' | 'discard') => {
    setDecidingBlockId(blockId);
    try {
      await onDecide(blockId, disposition);
    } finally {
      setDecidingBlockId(null);
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Stats */}
      <div className="flex gap-4 mb-4">
        <Badge variant="outline">{data.total_count} blocks total</Badge>
        <Badge variant="outline" className="text-amber-600 border-amber-300">
          {data.pending_count} pending
        </Badge>
        <Badge variant="outline" className="text-green-600 border-green-300">
          {decidedItems.filter((i) => i.final_disposition === 'keep').length} to keep
        </Badge>
        <Badge variant="outline" className="text-red-600 border-red-300">
          {decidedItems.filter((i) => i.final_disposition === 'discard').length} to discard
        </Badge>
      </div>

      {/* Items list */}
      <ScrollArea className="flex-1">
        <div className="space-y-3 pr-4">
          {data.items.map((item) => (
            <CleanupItemCard
              key={item.block_id}
              item={item}
              isDeciding={decidingBlockId === item.block_id}
              onDecide={handleDecision}
            />
          ))}
        </div>
      </ScrollArea>

      {/* Approve button */}
      <div className="pt-4 border-t mt-4">
        <Button onClick={onApprove} disabled={!data.all_decided || isApproving} className="w-full">
          {isApproving ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Approving...
            </>
          ) : (
            <>
              <CheckCircle2 className="h-4 w-4 mr-2" />
              Approve Cleanup Plan ({decidedItems.length}/{data.total_count})
            </>
          )}
        </Button>
        {!data.all_decided && (
          <p className="text-xs text-muted-foreground text-center mt-2">
            Decide on all pending blocks to continue
          </p>
        )}
      </div>
    </div>
  );
}
