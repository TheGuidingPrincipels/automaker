import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { Sparkles, Lightbulb, AlertTriangle, CheckCircle, X } from 'lucide-react';

import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ConfidenceBar, type ConfidenceLevel } from '@/components/ui/confidence-bar';

const aiRecommendationBoxVariants = cva(
  'relative overflow-hidden rounded-xl border backdrop-blur-md transition-all duration-200',
  {
    variants: {
      variant: {
        default:
          'bg-card text-card-foreground border-white/10 shadow-[0_1px_2px_rgba(0,0,0,0.05),0_4px_6px_rgba(0,0,0,0.05),0_10px_20px_rgba(0,0,0,0.04)]',
        suggestion:
          'bg-[var(--status-info-bg)] border-[var(--status-info)]/20 text-card-foreground',
        warning:
          'bg-[var(--status-warning-bg)] border-[var(--status-warning)]/20 text-card-foreground',
        success:
          'bg-[var(--status-success-bg)] border-[var(--status-success)]/20 text-card-foreground',
      },
      size: {
        default: 'p-4',
        sm: 'p-3',
        lg: 'p-6',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

const iconContainerVariants = cva(
  'flex items-center justify-center rounded-lg transition-colors duration-200',
  {
    variants: {
      variant: {
        default: 'bg-primary/10 text-primary',
        suggestion: 'bg-[var(--status-info)]/10 text-[var(--status-info)]',
        warning: 'bg-[var(--status-warning)]/10 text-[var(--status-warning)]',
        success: 'bg-[var(--status-success)]/10 text-[var(--status-success)]',
      },
      size: {
        default: 'size-9',
        sm: 'size-7',
        lg: 'size-11',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export type RecommendationType = 'insight' | 'suggestion' | 'warning' | 'improvement';

export interface AIRecommendationBoxProps
  extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'>,
    VariantProps<typeof aiRecommendationBoxVariants> {
  /** The title of the recommendation */
  title: React.ReactNode;
  /** Optional description or supporting text */
  description?: React.ReactNode;
  /** Type of recommendation - affects the icon shown */
  type?: RecommendationType;
  /** Confidence score between 0 and 1 */
  confidence?: number;
  /** Override confidence level color */
  confidenceLevel?: ConfidenceLevel;
  /** Show confidence label */
  showConfidenceLabel?: boolean;
  /** Whether the recommendation can be dismissed */
  dismissible?: boolean;
  /** Callback when dismiss button is clicked */
  onDismiss?: () => void;
  /** Primary action button label */
  actionLabel?: string;
  /** Callback when action button is clicked */
  onAction?: () => void;
  /** Secondary action button label */
  secondaryActionLabel?: string;
  /** Callback when secondary action button is clicked */
  onSecondaryAction?: () => void;
  /** Loading state for the action button */
  actionLoading?: boolean;
  /** Custom icon to override the default type-based icon */
  icon?: React.ReactNode;
  /** Badge text to show next to the title */
  badge?: string;
  /** Source or attribution text */
  source?: string;
}

const typeIcons: Record<RecommendationType, React.ElementType> = {
  insight: Sparkles,
  suggestion: Lightbulb,
  warning: AlertTriangle,
  improvement: CheckCircle,
};

/**
 * A card component for displaying AI-generated recommendations, insights, and suggestions.
 * Supports confidence scoring, dismissible state, and action buttons.
 *
 * @example
 * // Basic usage
 * <AIRecommendationBox
 *   title="Consider adding error handling"
 *   description="This function could fail silently. Adding try-catch would improve reliability."
 *   type="suggestion"
 *   confidence={0.85}
 * />
 *
 * @example
 * // With actions
 * <AIRecommendationBox
 *   title="Performance optimization available"
 *   description="Memoizing this component could reduce re-renders by 40%."
 *   type="improvement"
 *   confidence={0.92}
 *   actionLabel="Apply Fix"
 *   onAction={() => applyFix()}
 *   dismissible
 *   onDismiss={() => dismiss()}
 * />
 *
 * @example
 * // Warning variant
 * <AIRecommendationBox
 *   variant="warning"
 *   title="Potential security issue"
 *   description="User input is not being sanitized before database query."
 *   type="warning"
 *   badge="High Priority"
 * />
 */
function AIRecommendationBox({
  className,
  variant,
  size,
  title,
  description,
  type = 'insight',
  confidence,
  confidenceLevel,
  showConfidenceLabel = true,
  dismissible = false,
  onDismiss,
  actionLabel,
  onAction,
  secondaryActionLabel,
  onSecondaryAction,
  actionLoading = false,
  icon,
  badge,
  source,
  children,
  ...props
}: AIRecommendationBoxProps) {
  const IconComponent = typeIcons[type];
  const iconSize = size === 'sm' ? 'h-3.5 w-3.5' : size === 'lg' ? 'h-5 w-5' : 'h-4 w-4';

  return (
    <div
      data-slot="ai-recommendation-box"
      className={cn(aiRecommendationBoxVariants({ variant, size }), className)}
      {...props}
    >
      {/* Header */}
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className={cn(iconContainerVariants({ variant, size }))}>
          {icon ?? <IconComponent className={iconSize} />}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className={cn(
              'font-semibold leading-tight text-foreground',
              size === 'sm' ? 'text-sm' : size === 'lg' ? 'text-lg' : 'text-base'
            )}>
              {title}
            </h4>
            {badge && (
              <Badge variant="brand" size="sm">
                {badge}
              </Badge>
            )}
          </div>

          {description && (
            <p className={cn(
              'mt-1 text-muted-foreground leading-relaxed',
              size === 'sm' ? 'text-xs' : 'text-sm'
            )}>
              {description}
            </p>
          )}

          {/* Custom content */}
          {children && (
            <div className="mt-3">
              {children}
            </div>
          )}

          {/* Confidence bar */}
          {confidence !== undefined && (
            <div className="mt-3">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs text-muted-foreground">Confidence</span>
              </div>
              <ConfidenceBar
                value={confidence}
                level={confidenceLevel}
                showLabel={showConfidenceLabel}
                size={size === 'lg' ? 'default' : 'sm'}
              />
            </div>
          )}

          {/* Source attribution */}
          {source && (
            <p className="mt-2 text-xs text-muted-foreground/70 italic">
              Source: {source}
            </p>
          )}

          {/* Actions */}
          {(actionLabel || secondaryActionLabel) && (
            <div className="flex items-center gap-2 mt-4">
              {actionLabel && (
                <Button
                  size={size === 'lg' ? 'default' : 'sm'}
                  onClick={onAction}
                  loading={actionLoading}
                >
                  {actionLabel}
                </Button>
              )}
              {secondaryActionLabel && (
                <Button
                  variant="outline"
                  size={size === 'lg' ? 'default' : 'sm'}
                  onClick={onSecondaryAction}
                >
                  {secondaryActionLabel}
                </Button>
              )}
            </div>
          )}
        </div>

        {/* Dismiss button */}
        {dismissible && (
          <Button
            variant="ghost"
            size="icon-sm"
            className="shrink-0 -mt-1 -mr-1 text-muted-foreground hover:text-foreground"
            onClick={onDismiss}
            aria-label="Dismiss recommendation"
          >
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}

AIRecommendationBox.displayName = 'AIRecommendationBox';

export { AIRecommendationBox, aiRecommendationBoxVariants };
