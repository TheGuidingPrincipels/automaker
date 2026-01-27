import { useState, type CSSProperties } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { ChevronDown, ChevronUp } from 'lucide-react';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import type { KLCleanupDisposition } from '@automaker/types';

const contentPreviewBoxVariants = cva(
  'relative rounded-md border font-mono text-sm whitespace-pre-wrap transition-colors duration-200',
  {
    variants: {
      variant: {
        default: 'bg-muted/30 border-border',
        keep: 'bg-[var(--status-success-bg)]/30 border-[var(--status-success)]/30',
        discard: 'bg-[var(--status-error-bg)]/30 border-[var(--status-error)]/30',
      },
      size: {
        sm: 'p-2 text-xs',
        default: 'p-3 text-sm',
        lg: 'p-4 text-base',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface ContentPreviewBoxProps
  extends Omit<React.HTMLAttributes<HTMLDivElement>, 'content'>,
    VariantProps<typeof contentPreviewBoxVariants> {
  /** The truncated content preview to display initially */
  content: string;
  /** The full content to show when expanded */
  fullContent: string;
  /** The suggested disposition, affects visual styling */
  suggestedDisposition?: KLCleanupDisposition;
  /** Maximum number of lines to show when collapsed (default: no limit) */
  maxCollapsedLines?: number;
  /** Whether to start in expanded state */
  defaultExpanded?: boolean;
  /** Called when expand/collapse state changes */
  onExpandedChange?: (expanded: boolean) => void;
}

/**
 * A preview box component for displaying content with expand/collapse functionality.
 * Commonly used in the Knowledge Library cleanup review to show block content.
 *
 * @example
 * // Basic usage
 * <ContentPreviewBox
 *   content="First 200 characters of content..."
 *   fullContent="The full content of the block that can be quite long..."
 *   suggestedDisposition="keep"
 * />
 *
 * @example
 * // Discard styling
 * <ContentPreviewBox
 *   content="Content to be discarded..."
 *   fullContent="Full content..."
 *   suggestedDisposition="discard"
 * />
 *
 * @example
 * // With size variant
 * <ContentPreviewBox
 *   content="Preview..."
 *   fullContent="Full content..."
 *   size="sm"
 * />
 */
function ContentPreviewBox({
  className,
  variant,
  size,
  content,
  fullContent,
  suggestedDisposition,
  maxCollapsedLines,
  defaultExpanded = false,
  onExpandedChange,
  ...props
}: ContentPreviewBoxProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  // Derive variant from suggestedDisposition if not explicitly set
  const effectiveVariant = variant ?? (suggestedDisposition === 'discard' ? 'discard' : suggestedDisposition === 'keep' ? 'keep' : 'default');

  const hasMoreContent = fullContent.length > content.length;
  const displayContent = isExpanded ? fullContent : content;
  const collapsedStyle: CSSProperties | undefined =
    maxCollapsedLines && !isExpanded
      ? {
          display: '-webkit-box',
          WebkitBoxOrient: 'vertical',
          WebkitLineClamp: maxCollapsedLines,
          overflow: 'hidden',
        }
      : undefined;

  const handleToggle = () => {
    const newExpanded = !isExpanded;
    setIsExpanded(newExpanded);
    onExpandedChange?.(newExpanded);
  };

  return (
    <div
      data-slot="content-preview-box"
      className={cn(contentPreviewBoxVariants({ variant: effectiveVariant, size }), className)}
      {...props}
    >
      <div style={collapsedStyle}>
        {displayContent}
        {!isExpanded && hasMoreContent && (
          <span className="text-muted-foreground">...</span>
        )}
      </div>

      {hasMoreContent && (
        <Button
          variant="ghost"
          size="sm"
          className="absolute top-1 right-1 h-6 text-xs opacity-70 hover:opacity-100 transition-opacity"
          onClick={handleToggle}
          aria-expanded={isExpanded}
          aria-label={isExpanded ? 'Collapse content' : 'Expand content'}
        >
          {isExpanded ? (
            <>
              <ChevronUp className="h-3 w-3 mr-1" />
              Collapse
            </>
          ) : (
            <>
              <ChevronDown className="h-3 w-3 mr-1" />
              Expand
            </>
          )}
        </Button>
      )}
    </div>
  );
}

ContentPreviewBox.displayName = 'ContentPreviewBox';

export { ContentPreviewBox, contentPreviewBoxVariants };
