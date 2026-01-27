import { useState, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { SkeletonPulse } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { CheckCircle2, Trash2, Loader2, ArrowLeftRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { useKLCleanupPlan } from '@/hooks/queries/use-knowledge-library';

type CleanupTab = 'all' | 'pending' | 'keep' | 'discard';

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
  viewMode: CleanupTab;
}

function CleanupItemCard({ item, isDeciding, onDecide, viewMode }: CleanupItemCardProps) {
  const isDecided = item.final_disposition !== null;
  const isKeep = item.final_disposition === 'keep';

  // Determine which buttons to show based on view mode
  const renderButtons = () => {
    if (isDeciding) {
      return (
        <Button variant="outline" size="sm" disabled>
          <Loader2 className="h-4 w-4 animate-spin" />
        </Button>
      );
    }

    // Pending view or undecided item in All view: show Keep/Discard
    if (viewMode === 'pending' || (viewMode === 'all' && !isDecided)) {
      return (
        <>
          <Button
            variant="outline"
            size="sm"
            className="text-green-600 hover:bg-green-50"
            onClick={() => onDecide(item.block_id, 'keep')}
          >
            <CheckCircle2 className="h-4 w-4 mr-1" />
            Keep
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="text-red-600 hover:bg-red-50"
            onClick={() => onDecide(item.block_id, 'discard')}
          >
            <Trash2 className="h-4 w-4 mr-1" />
            Discard
          </Button>
        </>
      );
    }

    // Keep view: show Move to Discard
    if (viewMode === 'keep') {
      return (
        <Button
          variant="outline"
          size="sm"
          className="text-red-600 hover:bg-red-50"
          onClick={() => onDecide(item.block_id, 'discard')}
        >
          <ArrowLeftRight className="h-4 w-4 mr-1" />
          Move to Discard
        </Button>
      );
    }

    // Discard view: show Move to Keep
    if (viewMode === 'discard') {
      return (
        <Button
          variant="outline"
          size="sm"
          className="text-green-600 hover:bg-green-50"
          onClick={() => onDecide(item.block_id, 'keep')}
        >
          <ArrowLeftRight className="h-4 w-4 mr-1" />
          Move to Keep
        </Button>
      );
    }

    // All view with decided item: show Switch button
    if (viewMode === 'all' && isDecided) {
      const targetDisposition = isKeep ? 'discard' : 'keep';
      return (
        <Button
          variant="outline"
          size="sm"
          className={isKeep ? 'text-red-600 hover:bg-red-50' : 'text-green-600 hover:bg-green-50'}
          onClick={() => onDecide(item.block_id, targetDisposition)}
        >
          <ArrowLeftRight className="h-4 w-4 mr-1" />
          Switch to {targetDisposition}
        </Button>
      );
    }

    return null;
  };

  return (
    <Card className={cn(viewMode === 'all' && isDecided && 'opacity-60')}>
      <CardContent className="pt-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="outline" className="text-xs">
                {item.heading_path.join(' > ')}
              </Badge>
              {viewMode === 'all' && isDecided && (
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

          <div className="flex gap-2 shrink-0">{renderButtons()}</div>
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
  const [activeTab, setActiveTab] = useState<CleanupTab>('pending');

  const categorizedItems = useMemo(() => {
    if (!data) return { all: [], pending: [], keep: [], discard: [] };

    const pending: typeof data.items = [];
    const keep: typeof data.items = [];
    const discard: typeof data.items = [];

    for (const item of data.items) {
      if (item.final_disposition === null) {
        pending.push(item);
      } else if (item.final_disposition === 'keep') {
        keep.push(item);
      } else {
        discard.push(item);
      }
    }

    return { all: data.items, pending, keep, discard };
  }, [data]);

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

  const handleDecision = async (blockId: string, disposition: 'keep' | 'discard') => {
    setDecidingBlockId(blockId);
    try {
      await onDecide(blockId, disposition);
    } finally {
      setDecidingBlockId(null);
    }
  };

  const renderItemsList = (items: typeof data.items, viewMode: CleanupTab) => {
    if (items.length === 0) {
      if (viewMode === 'pending') {
        return (
          <div className="text-center text-muted-foreground py-8">
            <CheckCircle2 className="h-8 w-8 mx-auto mb-2 text-green-500" />
            <p>All blocks have been reviewed!</p>
          </div>
        );
      }
      return (
        <div className="text-center text-muted-foreground py-8">
          <p>No items in this category</p>
        </div>
      );
    }

    return (
      <div className="space-y-3 pb-2">
        {items.map((item) => (
          <CleanupItemCard
            key={item.block_id}
            item={item}
            isDeciding={decidingBlockId === item.block_id}
            onDecide={handleDecision}
            viewMode={viewMode}
          />
        ))}
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col min-h-0">
      <Tabs
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as CleanupTab)}
        className="flex-1 flex flex-col min-h-0"
      >
        <TabsList className="mb-4 shrink-0">
          <TabsTrigger value="all">
            All Blocks
            <Badge variant="outline" className="ml-1.5">
              {data.total_count}
            </Badge>
          </TabsTrigger>
          <TabsTrigger value="pending">
            Pending
            <Badge variant="outline" className="text-amber-600 border-amber-300 ml-1.5">
              {categorizedItems.pending.length}
            </Badge>
          </TabsTrigger>
          <TabsTrigger value="keep">
            To Keep
            <Badge variant="outline" className="text-green-600 border-green-300 ml-1.5">
              {categorizedItems.keep.length}
            </Badge>
          </TabsTrigger>
          <TabsTrigger value="discard">
            To Discard
            <Badge variant="outline" className="text-red-600 border-red-300 ml-1.5">
              {categorizedItems.discard.length}
            </Badge>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="relative min-h-0 m-0">
          <div className="absolute inset-0 overflow-y-auto pr-2">
            {renderItemsList(categorizedItems.all, 'all')}
          </div>
        </TabsContent>

        <TabsContent value="pending" className="relative min-h-0 m-0">
          <div className="absolute inset-0 overflow-y-auto pr-2">
            {renderItemsList(categorizedItems.pending, 'pending')}
          </div>
        </TabsContent>

        <TabsContent value="keep" className="relative min-h-0 m-0">
          <div className="absolute inset-0 overflow-y-auto pr-2">
            {renderItemsList(categorizedItems.keep, 'keep')}
          </div>
        </TabsContent>

        <TabsContent value="discard" className="relative min-h-0 m-0">
          <div className="absolute inset-0 overflow-y-auto pr-2">
            {renderItemsList(categorizedItems.discard, 'discard')}
          </div>
        </TabsContent>
      </Tabs>

      {/* Approve button */}
      <div className="pt-4 border-t mt-4 shrink-0">
        <Button onClick={onApprove} disabled={!data.all_decided || isApproving} className="w-full">
          {isApproving ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Approving...
            </>
          ) : (
            <>
              <CheckCircle2 className="h-4 w-4 mr-2" />
              Approve Cleanup Plan ({categorizedItems.keep.length + categorizedItems.discard.length}
              /{data.total_count})
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
