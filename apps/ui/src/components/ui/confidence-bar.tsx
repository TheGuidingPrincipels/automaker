import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';

import { cn } from '@/lib/utils';

const confidenceBarVariants = cva(
  'relative overflow-hidden rounded-full transition-all duration-200',
  {
    variants: {
      size: {
        default: 'h-2',
        sm: 'h-1.5',
        lg: 'h-3',
      },
    },
    defaultVariants: {
      size: 'default',
    },
  }
);

const confidenceFillVariants = cva(
  'h-full rounded-full transition-all duration-300 ease-out',
  {
    variants: {
      level: {
        high: 'bg-[var(--status-success)]',
        medium: 'bg-[var(--status-warning)]',
        low: 'bg-[var(--status-error)]',
        default: 'bg-primary',
      },
    },
    defaultVariants: {
      level: 'default',
    },
  }
);

export type ConfidenceLevel = 'high' | 'medium' | 'low' | 'default';

export interface ConfidenceBarProps
  extends Omit<React.HTMLAttributes<HTMLDivElement>, 'children'>,
    VariantProps<typeof confidenceBarVariants> {
  /** Confidence value between 0 and 1 (or 0-100 if using percentage) */
  value: number;
  /** Whether the value is a percentage (0-100) instead of decimal (0-1) */
  isPercentage?: boolean;
  /** Show percentage label next to the bar */
  showLabel?: boolean;
  /** Custom label format function */
  formatLabel?: (value: number) => string;
  /** Override automatic color level based on value */
  level?: ConfidenceLevel;
  /** Animate the bar on mount/change */
  animated?: boolean;
  /** Track background class override */
  trackClassName?: string;
  /** Fill bar class override */
  fillClassName?: string;
}

/**
 * Determines the confidence level based on a normalized value (0-1)
 */
function getConfidenceLevel(value: number): ConfidenceLevel {
  if (value >= 0.7) return 'high';
  if (value >= 0.4) return 'medium';
  return 'low';
}

/**
 * A visual progress bar component for displaying confidence scores.
 * Automatically colors based on confidence level (high/medium/low) or accepts custom level override.
 *
 * @example
 * // Basic usage with decimal value
 * <ConfidenceBar value={0.85} />
 *
 * @example
 * // With percentage and label
 * <ConfidenceBar value={75} isPercentage showLabel />
 *
 * @example
 * // Compact size with custom level
 * <ConfidenceBar value={0.5} size="sm" level="high" />
 */
function ConfidenceBar({
  className,
  value,
  isPercentage = false,
  showLabel = false,
  formatLabel,
  level,
  size,
  animated = true,
  trackClassName,
  fillClassName,
  ...props
}: ConfidenceBarProps) {
  const safeValue = Number.isFinite(value) ? value : 0.5;

  // Normalize value to 0-1 range
  const normalizedValue = isPercentage
    ? Math.min(100, Math.max(0, safeValue)) / 100
    : Math.min(1, Math.max(0, safeValue));

  // Calculate percentage for display and width
  const percentage = Math.round(normalizedValue * 100);

  // Determine color level
  const computedLevel = level ?? getConfidenceLevel(normalizedValue);

  // Format label
  const labelText = formatLabel ? formatLabel(normalizedValue) : `${percentage}%`;

  return (
    <div
      className={cn('flex items-center gap-2', className)}
      role="progressbar"
      aria-valuenow={percentage}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`Confidence: ${percentage}%`}
      {...props}
    >
      <div
        className={cn(
          confidenceBarVariants({ size }),
          'flex-1 bg-muted',
          trackClassName
        )}
      >
        <div
          className={cn(
            confidenceFillVariants({ level: computedLevel }),
            animated && 'transition-[width] duration-500 ease-out',
            fillClassName
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-xs font-medium text-muted-foreground tabular-nums min-w-[3ch] text-right">
          {labelText}
        </span>
      )}
    </div>
  );
}

ConfidenceBar.displayName = 'ConfidenceBar';

export { ConfidenceBar, confidenceBarVariants, confidenceFillVariants, getConfidenceLevel };
