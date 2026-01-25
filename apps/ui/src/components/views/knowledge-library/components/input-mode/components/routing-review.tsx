import { useEffect, useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { SkeletonPulse } from '@/components/ui/skeleton';
import { Loader2, FileOutput, Ban } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { useKLRoutingPlan } from '@/hooks/queries/use-knowledge-library';
import {
  useKnowledgeLibraryStore,
  selectInvalidProposedFilesCount,
} from '@/store/knowledge-library-store';
import { collectCreateFileProposals, groupRoutingBlocks } from '../plan-review.utils';
import { ProposedFilesPanel } from './proposed-files-panel';

interface RoutingReviewProps {
  data: ReturnType<typeof useKLRoutingPlan>['data'];
  isLoading: boolean;
  onApprove: () => void;
  isApproving: boolean;
  onSelectOption: (
    blockId: string,
    optionIndex: number,
    payload?: { proposed_file_title?: string; proposed_file_overview?: string }
  ) => Promise<void>;
  onRejectBlock: (blockId: string) => Promise<void>;
}

interface RoutingBlockCardProps {
  block: NonNullable<ReturnType<typeof useKLRoutingPlan>['data']>['blocks'][number];
  isSaving: boolean;
  onSelectOption: (blockId: string, optionIndex: number) => void;
  onReject: (blockId: string) => void;
}

function RoutingBlockCard({ block, isSaving, onSelectOption, onReject }: RoutingBlockCardProps) {
  const isResolved = block.status !== 'pending';
  const selectedOption =
    block.selected_option_index !== null ? block.options[block.selected_option_index] : null;

  return (
    <Card className={cn(isResolved && 'border-green-500/50')}>
      <CardContent className="pt-4">
        <div className="flex items-start justify-between gap-4 mb-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="outline" className="text-xs">
                {block.heading_path.join(' > ')}
              </Badge>
              <Badge
                variant={
                  block.status === 'selected'
                    ? 'default'
                    : block.status === 'rejected'
                      ? 'destructive'
                      : 'outline'
                }
                className="text-xs"
              >
                {block.status}
              </Badge>
            </div>
            <p className="text-sm line-clamp-2 text-muted-foreground">{block.content_preview}</p>
          </div>
        </div>

        {/* Destination options */}
        <div className="space-y-2">
          {block.options.slice(0, 3).map((option, idx) => (
            <button
              key={idx}
              type="button"
              className={cn(
                'w-full text-left p-3 rounded-md border transition-colors',
                block.selected_option_index === idx
                  ? 'border-primary bg-primary/5'
                  : 'hover:bg-muted'
              )}
              onClick={() => onSelectOption(block.block_id, idx)}
              disabled={isSaving}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-sm truncate">{option.destination_file}</span>
                <Badge variant="secondary" className="text-xs ml-2">
                  {Math.round(option.confidence * 100)}%
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground mt-1 line-clamp-1">{option.reasoning}</p>
            </button>
          ))}
        </div>

        <div className="mt-3 flex items-center justify-between">
          <Button
            variant="outline"
            size="sm"
            className="text-xs"
            onClick={() => onReject(block.block_id)}
            disabled={isSaving || block.status === 'rejected'}
          >
            <Ban className="h-3.5 w-3.5 mr-1" />
            {block.status === 'rejected' ? 'Rejected' : 'Reject Block'}
          </Button>
          {selectedOption && (
            <span className="text-xs text-muted-foreground">
              Selected: {selectedOption.destination_file}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function RoutingReview({
  data,
  isLoading,
  onApprove,
  isApproving,
  onSelectOption,
  onRejectBlock,
}: RoutingReviewProps) {
  const proposedNewFiles = useKnowledgeLibraryStore((state) => state.proposedNewFiles);
  const setProposedNewFile = useKnowledgeLibraryStore((state) => state.setProposedNewFile);
  const updateProposedNewFile = useKnowledgeLibraryStore((state) => state.updateProposedNewFile);
  const removeProposedNewFile = useKnowledgeLibraryStore((state) => state.removeProposedNewFile);
  const invalidProposedCount = useKnowledgeLibraryStore(selectInvalidProposedFilesCount);
  const blocks = data?.blocks ?? [];
  const [actionBlockId, setActionBlockId] = useState<string | null>(null);

  const createFileProposals = useMemo(() => collectCreateFileProposals(blocks), [blocks]);
  const groupedBlocks = useMemo(() => groupRoutingBlocks(blocks), [blocks]);

  useEffect(() => {
    if (!data) return;

    const proposalPaths = new Set(createFileProposals.map((proposal) => proposal.destinationFile));

    for (const proposal of createFileProposals) {
      if (!proposedNewFiles[proposal.destinationFile]) {
        setProposedNewFile(proposal.destinationFile, {
          title: proposal.title,
          overview: proposal.overview,
          isValid: true,
          errors: [],
        });
      }
    }

    for (const existingPath of Object.keys(proposedNewFiles)) {
      if (!proposalPaths.has(existingPath)) {
        removeProposedNewFile(existingPath);
      }
    }
  }, [createFileProposals, data, proposedNewFiles, removeProposedNewFile, setProposedNewFile]);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <SkeletonPulse className="h-32 w-full" />
        <SkeletonPulse className="h-32 w-full" />
        <SkeletonPulse className="h-32 w-full" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center text-muted-foreground">
        <p>No routing plan available</p>
      </div>
    );
  }

  const handleSelectOption = async (blockId: string, optionIndex: number) => {
    const block = blocks.find((item) => item.block_id === blockId);
    const option = block?.options[optionIndex];
    if (!option) return;

    setActionBlockId(blockId);
    try {
      const payload =
        option.action === 'create_file'
          ? {
              proposed_file_title:
                proposedNewFiles[option.destination_file]?.title ??
                option.proposed_file_title ??
                '',
              proposed_file_overview:
                proposedNewFiles[option.destination_file]?.overview ??
                option.proposed_file_overview ??
                '',
            }
          : undefined;
      await onSelectOption(blockId, optionIndex, payload);
    } finally {
      setActionBlockId(null);
    }
  };

  const handleRejectBlock = async (blockId: string) => {
    setActionBlockId(blockId);
    try {
      await onRejectBlock(blockId);
    } finally {
      setActionBlockId(null);
    }
  };

  const hasInvalidProposals = createFileProposals.length > 0 && invalidProposedCount > 0;
  const canApprove = data.all_blocks_resolved && !hasInvalidProposals;

  return (
    <div className="h-full flex flex-col">
      {/* Stats */}
      <div className="flex gap-4 mb-4">
        <Badge variant="outline">{data.blocks.length} blocks</Badge>
        <Badge variant="outline" className="text-amber-600 border-amber-300">
          {data.pending_count} pending
        </Badge>
        <Badge variant="outline" className="text-green-600 border-green-300">
          {data.accepted_count} routed
        </Badge>
        {data.summary && (
          <>
            <Badge variant="outline">{data.summary.blocks_to_new_files} new files</Badge>
            <Badge variant="outline">{data.summary.blocks_to_existing_files} existing files</Badge>
          </>
        )}
      </div>

      <ProposedFilesPanel
        proposals={createFileProposals}
        proposedFiles={proposedNewFiles}
        onUpdate={updateProposedNewFile}
      />

      {/* Blocks list */}
      <ScrollArea className="flex-1">
        <div className="space-y-6 pr-4">
          {groupedBlocks.map((group) => (
            <div key={group.key} className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-xs">
                    {group.destinationFile}
                  </Badge>
                  <Badge variant="secondary" className="text-xs">
                    {group.blocks.length} blocks
                  </Badge>
                </div>
              </div>
              {group.blocks.map((block) => (
                <RoutingBlockCard
                  key={block.block_id}
                  block={block}
                  isSaving={actionBlockId === block.block_id}
                  onSelectOption={handleSelectOption}
                  onReject={handleRejectBlock}
                />
              ))}
            </div>
          ))}
        </div>
      </ScrollArea>

      {/* Approve button */}
      <div className="pt-4 border-t mt-4">
        <Button onClick={onApprove} disabled={!canApprove || isApproving} className="w-full">
          {isApproving ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Approving...
            </>
          ) : (
            <>
              <FileOutput className="h-4 w-4 mr-2" />
              Approve Routing Plan ({data.accepted_count}/{data.blocks.length})
            </>
          )}
        </Button>
        {!data.all_blocks_resolved && (
          <p className="text-xs text-muted-foreground text-center mt-2">
            Select destinations for all blocks to continue
          </p>
        )}
        {hasInvalidProposals && (
          <p className="text-xs text-destructive text-center mt-2">
            Provide valid Title and Overview for all proposed new files to approve routing.
          </p>
        )}
      </div>
    </div>
  );
}
