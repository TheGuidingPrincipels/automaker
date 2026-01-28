import { useState, useMemo, useCallback } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { SkeletonPulse } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ConfidenceBar } from '@/components/ui/confidence-bar';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import {
  CheckCircle2,
  Trash2,
  Loader2,
  ArrowLeftRight,
  Check,
  Sparkles,
  AlertTriangle,
  AlertCircle,
  Copy,
  ChevronDown,
  Settings,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { useKLCleanupPlan } from '@/hooks/queries/use-knowledge-library';
import { useKLBlocks } from '@/hooks/queries/use-knowledge-library';
import type { KLBlockResponse } from '@automaker/types';

type CleanupTab = 'all' | 'pending' | 'keep' | 'discard';

interface CleanupReviewProps {
  sessionId: string;
  data: ReturnType<typeof useKLCleanupPlan>['data'];
  isLoading: boolean;
  onApprove: () => void;
  onDecide: (blockId: string, disposition: 'keep' | 'discard') => Promise<void>;
  isApproving: boolean;
}

interface CleanupItemCardProps {
  item: NonNullable<ReturnType<typeof useKLCleanupPlan>['data']>['items'][number];
  block: KLBlockResponse | undefined;
  isDeciding: boolean;
  onDecide: (blockId: string, disposition: 'keep' | 'discard') => void;
  viewMode: CleanupTab;
}

/** Confidence level explanation for tooltip */
function getConfidenceExplanation(confidence: number): string {
  if (confidence >= 0.9) return 'Strong evidence for this suggestion';
  if (confidence >= 0.7) return 'Moderate evidence for this suggestion';
  if (confidence >= 0.5) return 'Uncertain - review carefully';
  return 'Very uncertain - default suggestion';
}

function CleanupItemCard({ item, block, isDeciding, onDecide, viewMode }: CleanupItemCardProps) {
  const isDecided = item.final_disposition !== null;
  const isKeep = item.final_disposition === 'keep';
  const isKeepSuggestion = item.suggested_disposition === 'keep';

  // Use block data when available for full content display
  const fullContent = block?.content ?? item.content_preview;

  // Color-coded border based on suggestion
  const borderColor = isKeepSuggestion
    ? 'border-l-[var(--status-success)] border-l-4'
    : 'border-l-[var(--status-error)] border-l-4';

  // Check for similar blocks (duplicate detection)
  const hasSimilarBlocks = item.similar_block_ids && item.similar_block_ids.length > 0;

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
      const keepIsRecommended = item.suggested_disposition === 'keep';
      const discardIsRecommended = item.suggested_disposition === 'discard';

      return (
        <>
          <Button
            variant={keepIsRecommended ? 'default' : 'outline'}
            size="sm"
            className={cn(
              keepIsRecommended
                ? 'bg-[var(--status-success)] hover:bg-[var(--status-success)]/90 text-white'
                : 'text-[var(--status-success)] hover:bg-[var(--status-success-bg)]'
            )}
            onClick={() => onDecide(item.block_id, 'keep')}
          >
            {keepIsRecommended ? (
              <Check className="h-4 w-4 mr-1" />
            ) : (
              <CheckCircle2 className="h-4 w-4 mr-1" />
            )}
            Keep{keepIsRecommended && ' (Recommended)'}
          </Button>
          <Button
            variant={discardIsRecommended ? 'default' : 'outline'}
            size="sm"
            className={cn(
              discardIsRecommended
                ? 'bg-[var(--status-error)] hover:bg-[var(--status-error)]/90 text-white'
                : 'text-[var(--status-error)] hover:bg-[var(--status-error-bg)]'
            )}
            onClick={() => onDecide(item.block_id, 'discard')}
          >
            <Trash2 className="h-4 w-4 mr-1" />
            Discard{discardIsRecommended && ' (Recommended)'}
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
          className="text-[var(--status-error)] hover:bg-[var(--status-error-bg)]"
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
          className="text-[var(--status-success)] hover:bg-[var(--status-success-bg)]"
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
          className={
            isKeep
              ? 'text-[var(--status-error)] hover:bg-[var(--status-error-bg)]'
              : 'text-[var(--status-success)] hover:bg-[var(--status-success-bg)]'
          }
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
    <div
      className={cn(
        'rounded-lg border bg-card p-4',
        borderColor,
        viewMode === 'all' && isDecided && 'opacity-60'
      )}
    >
      {/* Status badges row */}
      <div className="flex flex-wrap items-center gap-1.5 mb-3">
        {/* Status badge for decided items in All view */}
        {viewMode === 'all' && isDecided && (
          <Badge variant={isKeep ? 'default' : 'destructive'} className="text-xs">
            {item.final_disposition?.toUpperCase()}
          </Badge>
        )}

        {/* AI analysis status badge */}
        {item.ai_analyzed ? (
          <Badge
            variant="outline"
            className="text-xs bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/30 dark:text-blue-400 dark:border-blue-800"
          >
            <Sparkles className="h-3 w-3 mr-1" />
            AI Analyzed
          </Badge>
        ) : (
          <Badge
            variant="outline"
            className="text-xs bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/30 dark:text-amber-400 dark:border-amber-800"
          >
            <AlertCircle className="h-3 w-3 mr-1" />
            Default
          </Badge>
        )}

        {/* Content truncation indicator */}
        {item.content_truncated && (
          <Badge variant="outline" className="text-xs text-muted-foreground">
            {item.original_content_length.toLocaleString()} chars (truncated)
          </Badge>
        )}
      </div>

      {/* Duplicate warning */}
      {hasSimilarBlocks && (
        <div className="mb-3 rounded-md bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 p-2 flex items-center gap-2">
          <Copy className="h-4 w-4 text-amber-600 dark:text-amber-400 shrink-0" />
          <span className="text-xs text-amber-700 dark:text-amber-400">
            Similar to {item.similar_block_ids.length} other block(s)
            {item.similarity_score !== null &&
              ` (${Math.round(item.similarity_score * 100)}% match)`}
          </span>
        </div>
      )}

      {/* Full content block - main focus for user decision */}
      <div className="rounded-md bg-muted/50 p-3 font-mono text-sm whitespace-pre-wrap leading-relaxed">
        {fullContent}
      </div>

      {/* AI reasoning - compact inline display */}
      <div className="mt-3 flex items-start gap-2">
        <div
          className={cn(
            'shrink-0 rounded-full p-1.5',
            isKeepSuggestion ? 'bg-[var(--status-success)]/10' : 'bg-[var(--status-error)]/10'
          )}
        >
          <Sparkles
            className={cn(
              'h-3.5 w-3.5',
              isKeepSuggestion ? 'text-[var(--status-success)]' : 'text-[var(--status-error)]'
            )}
          />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span
              className={cn(
                'text-xs font-semibold',
                isKeepSuggestion ? 'text-[var(--status-success)]' : 'text-[var(--status-error)]'
              )}
            >
              {isKeepSuggestion ? 'KEEP' : 'DISCARD'}
            </span>
            {/* Confidence bar with tooltip explanation */}
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div>
                    <ConfidenceBar
                      value={item.confidence ?? 0.5}
                      level={isKeepSuggestion ? 'high' : 'low'}
                      showLabel={false}
                      size="sm"
                      className="w-16"
                    />
                  </div>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  <p className="font-semibold mb-1">
                    Confidence: {Math.round((item.confidence ?? 0.5) * 100)}%
                  </p>
                  <p className="text-xs mb-2">{getConfidenceExplanation(item.confidence ?? 0.5)}</p>
                  <ul className="text-xs space-y-0.5 text-muted-foreground">
                    <li>90-100%: Strong evidence</li>
                    <li>70-90%: Moderate evidence</li>
                    <li>50-70%: Uncertain</li>
                    <li>&lt;50%: Very uncertain</li>
                  </ul>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
            {item.suggestion_reason}
          </p>
        </div>
      </div>

      {/* Action buttons - prominent placement */}
      <div className="flex justify-end gap-2 mt-4">{renderButtons()}</div>
    </div>
  );
}

export function CleanupReview({
  sessionId,
  data,
  isLoading,
  onApprove,
  onDecide,
  isApproving,
}: CleanupReviewProps) {
  const [decidingBlockId, setDecidingBlockId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<CleanupTab>('pending');

  // Fetch blocks to get full content and metadata
  const blocksQuery = useKLBlocks(sessionId);

  // Build lookup map for blocks by ID
  const blockById = useMemo(() => {
    if (!blocksQuery.data?.blocks) return new Map<string, KLBlockResponse>();
    return new Map(blocksQuery.data.blocks.map((block) => [block.id, block]));
  }, [blocksQuery.data?.blocks]);

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

  // IMPORTANT: This hook must be defined before any early returns to comply
  // with React's Rules of Hooks (hooks must be called in the same order every render)
  const handleDecision = useCallback(
    async (blockId: string, disposition: 'keep' | 'discard') => {
      setDecidingBlockId(blockId);
      try {
        await onDecide(blockId, disposition);
      } catch (error) {
        console.error('Failed to update cleanup decision:', error);
        toast.error('Failed to update cleanup decision');
      } finally {
        setDecidingBlockId(null);
      }
    },
    [onDecide]
  );

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
            block={blockById.get(item.block_id)}
            isDeciding={decidingBlockId === item.block_id}
            onDecide={handleDecision}
            viewMode={viewMode}
          />
        ))}
      </div>
    );
  };

  // Count AI-analyzed vs defaulted blocks
  const aiAnalyzedCount = data.items.filter((item) => item.ai_analyzed).length;
  const defaultedCount = data.items.length - aiAnalyzedCount;

  return (
    <div className="h-full flex flex-col min-h-0 relative">
      {/* AI generation warning banner - more prominent when AI unavailable */}
      {data.ai_generated === false && (
        <div className="mb-3 rounded-lg border-2 border-amber-500 bg-amber-500/10 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-6 w-6 text-amber-500 shrink-0" />
            <div className="flex-1">
              <p className="font-semibold text-amber-600 dark:text-amber-400">
                AI Analysis Unavailable
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                {data.generation_error ||
                  'All blocks are showing default "Keep" suggestions with 50% confidence.'}
              </p>
              <p className="text-sm mt-2">
                <strong>What this means:</strong> You'll need to review each block manually. The
                suggestions shown are not AI-powered.
              </p>
              <Button
                variant="outline"
                size="sm"
                className="mt-3"
                onClick={() => (window.location.href = '/settings')}
              >
                <Settings className="h-4 w-4 mr-1" />
                Configure OAuth Token
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Partial AI analysis warning - when some blocks were defaulted */}
      {data.ai_generated && defaultedCount > 0 && (
        <div className="mb-3 rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/20 p-2 flex items-center gap-2">
          <AlertCircle className="h-4 w-4 text-blue-600 dark:text-blue-400 shrink-0" />
          <span className="text-xs text-blue-700 dark:text-blue-400">
            {aiAnalyzedCount} of {data.items.length} blocks analyzed by AI. {defaultedCount}{' '}
            block(s) show default suggestions.
          </span>
        </div>
      )}

      {/* Duplicate groups summary panel */}
      {data.duplicate_groups && data.duplicate_groups.length > 0 && (
        <Collapsible className="mb-3">
          <CollapsibleTrigger className="w-full rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/20 p-2 flex items-center gap-2 hover:bg-amber-100 dark:hover:bg-amber-950/30 transition-colors">
            <Copy className="h-4 w-4 text-amber-600 dark:text-amber-400 shrink-0" />
            <span className="text-xs font-medium text-amber-700 dark:text-amber-400 flex-1 text-left">
              {data.duplicate_groups.length} potential duplicate group(s) detected
            </span>
            <ChevronDown className="h-4 w-4 text-amber-600 dark:text-amber-400" />
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2 space-y-1.5">
            {data.duplicate_groups.map((group, i) => (
              <div key={i} className="text-xs bg-muted/50 p-2 rounded border border-border">
                <span className="font-medium">Group {i + 1}:</span>{' '}
                <span className="text-muted-foreground">Blocks {group.join(', ')}</span>
              </div>
            ))}
            <p className="text-xs text-muted-foreground px-1">
              Tip: Consider discarding duplicate content to keep your library clean.
            </p>
          </CollapsibleContent>
        </Collapsible>
      )}

      <Tabs
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as CleanupTab)}
        className="flex-1 flex flex-col min-h-0"
      >
        <TabsList className="mb-2 shrink-0">
          <TabsTrigger value="all" className="text-xs px-2">
            All
            <Badge variant="outline" className="ml-1 text-[10px] h-4 px-1">
              {data.total_count}
            </Badge>
          </TabsTrigger>
          <TabsTrigger value="pending" className="text-xs px-2">
            Pending
            <Badge
              variant="outline"
              className="text-amber-600 border-amber-300 ml-1 text-[10px] h-4 px-1"
            >
              {categorizedItems.pending.length}
            </Badge>
          </TabsTrigger>
          <TabsTrigger value="keep" className="text-xs px-2">
            Keep
            <Badge
              variant="outline"
              className="text-green-600 border-green-300 ml-1 text-[10px] h-4 px-1"
            >
              {categorizedItems.keep.length}
            </Badge>
          </TabsTrigger>
          <TabsTrigger value="discard" className="text-xs px-2">
            Discard
            <Badge
              variant="outline"
              className="text-red-600 border-red-300 ml-1 text-[10px] h-4 px-1"
            >
              {categorizedItems.discard.length}
            </Badge>
          </TabsTrigger>
        </TabsList>

        {/* Scrollable content area with padding for sticky button */}
        <TabsContent value="all" className="relative min-h-0 m-0 flex-1">
          <div className="absolute inset-0 overflow-y-auto pr-2 pb-16">
            {renderItemsList(categorizedItems.all, 'all')}
          </div>
        </TabsContent>

        <TabsContent value="pending" className="relative min-h-0 m-0 flex-1">
          <div className="absolute inset-0 overflow-y-auto pr-2 pb-16">
            {renderItemsList(categorizedItems.pending, 'pending')}
          </div>
        </TabsContent>

        <TabsContent value="keep" className="relative min-h-0 m-0 flex-1">
          <div className="absolute inset-0 overflow-y-auto pr-2 pb-16">
            {renderItemsList(categorizedItems.keep, 'keep')}
          </div>
        </TabsContent>

        <TabsContent value="discard" className="relative min-h-0 m-0 flex-1">
          <div className="absolute inset-0 overflow-y-auto pr-2 pb-16">
            {renderItemsList(categorizedItems.discard, 'discard')}
          </div>
        </TabsContent>
      </Tabs>

      {/* Sticky approve button at bottom */}
      <div className="absolute bottom-0 left-0 right-0 bg-card/95 backdrop-blur-sm pt-3 pb-1 border-t">
        <Button onClick={onApprove} disabled={!data.all_decided || isApproving} className="w-full">
          {isApproving ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Approving...
            </>
          ) : (
            <>
              <CheckCircle2 className="h-4 w-4 mr-2" />
              Approve Cleanup ({categorizedItems.keep.length + categorizedItems.discard.length}/
              {data.total_count})
            </>
          )}
        </Button>
        {!data.all_decided && (
          <p className="text-xs text-muted-foreground text-center mt-1">
            Decide on all pending blocks to continue
          </p>
        )}
      </div>
    </div>
  );
}
