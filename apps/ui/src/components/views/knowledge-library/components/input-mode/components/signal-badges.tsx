import { memo, useMemo } from 'react';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import {
  Clock,
  CheckSquare,
  Lightbulb,
  AlertTriangle,
  AlertCircle,
  Calendar,
  FileText,
  MessageCircle,
  Loader,
  Sparkles,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { KLDetectedSignalResponse } from '@automaker/types';

interface SignalBadgesProps {
  signals: KLDetectedSignalResponse[];
  className?: string;
  /** Maximum number of signals to show before collapsing */
  maxVisible?: number;
}

/** Signal type styling configuration */
interface SignalTypeStyle {
  icon: LucideIcon;
  bgClass: string;
  textClass: string;
  borderClass: string;
  label: string;
}

/**
 * Maps signal types to their visual styling.
 * Signal types come from Python AI analysis and indicate specific patterns
 * detected in content that influence keep/discard recommendations.
 *
 * Python signal types: explicit_marker, date_reference, completed_task,
 * temporary_note, reference_value, original_work, incomplete_content,
 * conversational, work_in_progress
 */
const signalTypeStyles: Record<string, SignalTypeStyle> = {
  // Explicit markers like "DELETE THIS" or "TODO: remove"
  explicit_marker: {
    icon: AlertTriangle,
    bgClass: 'bg-amber-50 dark:bg-amber-950/30',
    textClass: 'text-amber-700 dark:text-amber-400',
    borderClass: 'border-amber-200 dark:border-amber-800',
    label: 'Explicit Marker',
  },
  // References to specific dates or time periods
  date_reference: {
    icon: Calendar,
    bgClass: 'bg-slate-50 dark:bg-slate-950/30',
    textClass: 'text-slate-700 dark:text-slate-400',
    borderClass: 'border-slate-200 dark:border-slate-800',
    label: 'Date Reference',
  },
  // Completed tasks, done items, finished work
  completed_task: {
    icon: CheckSquare,
    bgClass: 'bg-green-50 dark:bg-green-950/30',
    textClass: 'text-green-700 dark:text-green-400',
    borderClass: 'border-green-200 dark:border-green-800',
    label: 'Completed Task',
  },
  // Temporary notes, reminders, ephemeral content
  temporary_note: {
    icon: Clock,
    bgClass: 'bg-cyan-50 dark:bg-cyan-950/30',
    textClass: 'text-cyan-700 dark:text-cyan-400',
    borderClass: 'border-cyan-200 dark:border-cyan-800',
    label: 'Temporary Note',
  },
  // Reference values, external links, citations
  reference_value: {
    icon: FileText,
    bgClass: 'bg-blue-50 dark:bg-blue-950/30',
    textClass: 'text-blue-700 dark:text-blue-400',
    borderClass: 'border-blue-200 dark:border-blue-800',
    label: 'Reference Value',
  },
  // Original creative or intellectual work
  original_work: {
    icon: Lightbulb,
    bgClass: 'bg-purple-50 dark:bg-purple-950/30',
    textClass: 'text-purple-700 dark:text-purple-400',
    borderClass: 'border-purple-200 dark:border-purple-800',
    label: 'Original Work',
  },
  // Incomplete, partial, or stub content
  incomplete_content: {
    icon: AlertCircle,
    bgClass: 'bg-orange-50 dark:bg-orange-950/30',
    textClass: 'text-orange-700 dark:text-orange-400',
    borderClass: 'border-orange-200 dark:border-orange-800',
    label: 'Incomplete',
  },
  // Conversational, chat-like, or informal content
  conversational: {
    icon: MessageCircle,
    bgClass: 'bg-sky-50 dark:bg-sky-950/30',
    textClass: 'text-sky-700 dark:text-sky-400',
    borderClass: 'border-sky-200 dark:border-sky-800',
    label: 'Conversational',
  },
  // Work in progress, draft, unfinished
  work_in_progress: {
    icon: Loader,
    bgClass: 'bg-violet-50 dark:bg-violet-950/30',
    textClass: 'text-violet-700 dark:text-violet-400',
    borderClass: 'border-violet-200 dark:border-violet-800',
    label: 'Work in Progress',
  },
};

/** Default styling for unknown signal types */
const defaultStyle: SignalTypeStyle = {
  icon: Sparkles,
  bgClass: 'bg-gray-50 dark:bg-gray-950/30',
  textClass: 'text-gray-700 dark:text-gray-400',
  borderClass: 'border-gray-200 dark:border-gray-800',
  label: 'Signal',
};

/**
 * Get the styling configuration for a signal type
 */
function getSignalStyle(type: string): SignalTypeStyle {
  // Normalize the type (handle variations like "time-sensitive" vs "time_sensitive")
  const normalizedType = type.toLowerCase().replace(/-/g, '_');
  return signalTypeStyles[normalizedType] || defaultStyle;
}

/**
 * Format signal type for display when label is not predefined
 */
function formatSignalType(type: string): string {
  return type.replace(/[_-]/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

/**
 * SignalBadges - Displays detected signals from AI analysis as compact badges
 *
 * Signals indicate specific patterns detected in content that influence
 * AI recommendations (e.g., time-sensitive content, original work, completed items).
 *
 * Each badge shows an icon with a tooltip containing the full signal detail.
 */
export const SignalBadges = memo(function SignalBadges({
  signals,
  className,
  maxVisible = 5,
}: SignalBadgesProps) {
  // Memoize computed values to avoid recalculation on every render
  const { visibleSignals, hiddenCount } = useMemo(
    () => ({
      visibleSignals: signals?.slice(0, maxVisible) ?? [],
      hiddenCount: Math.max(0, (signals?.length ?? 0) - maxVisible),
    }),
    [signals, maxVisible]
  );

  // Don't render if no signals
  if (!signals || signals.length === 0) {
    return null;
  }

  return (
    <TooltipProvider delayDuration={200}>
      <div className={cn('flex flex-wrap items-center gap-1.5', className)}>
        {visibleSignals.map((signal, index) => {
          const style = getSignalStyle(signal.type);
          const Icon = style.icon;
          const label = signalTypeStyles[signal.type.toLowerCase().replace(/-/g, '_')]
            ? style.label
            : formatSignalType(signal.type);

          return (
            <Tooltip key={`${signal.type}-${index}`}>
              <TooltipTrigger asChild>
                <Badge
                  variant="outline"
                  className={cn(
                    'text-xs cursor-help',
                    style.bgClass,
                    style.textClass,
                    style.borderClass
                  )}
                >
                  <Icon className="h-3 w-3 mr-1" />
                  {label}
                </Badge>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="max-w-xs">
                <p className="font-semibold mb-1">{label}</p>
                <p className="text-xs text-muted-foreground">{signal.detail}</p>
              </TooltipContent>
            </Tooltip>
          );
        })}

        {/* Overflow indicator for many signals */}
        {hiddenCount > 0 && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Badge variant="outline" className="text-xs cursor-help">
                +{hiddenCount} more
              </Badge>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="max-w-xs">
              <p className="font-semibold mb-1">Additional Signals</p>
              <ul className="text-xs text-muted-foreground space-y-1">
                {signals.slice(maxVisible).map((signal, index) => (
                  <li key={index}>
                    <span className="font-medium">{formatSignalType(signal.type)}:</span>{' '}
                    {signal.detail}
                  </li>
                ))}
              </ul>
            </TooltipContent>
          </Tooltip>
        )}
      </div>
    </TooltipProvider>
  );
});

/**
 * CompactSignalBadges - Icon-only version for space-constrained layouts
 *
 * Shows only icons without labels, useful for card headers or dense lists.
 */
export const CompactSignalBadges = memo(function CompactSignalBadges({
  signals,
  className,
  maxVisible = 4,
}: SignalBadgesProps) {
  // Memoize computed values to avoid recalculation on every render
  const { visibleSignals, hiddenCount } = useMemo(
    () => ({
      visibleSignals: signals?.slice(0, maxVisible) ?? [],
      hiddenCount: Math.max(0, (signals?.length ?? 0) - maxVisible),
    }),
    [signals, maxVisible]
  );

  if (!signals || signals.length === 0) {
    return null;
  }

  const uniformBadgeClass =
    'inline-flex items-center justify-center w-6 h-6 rounded-md border-[1.5px]';

  return (
    <TooltipProvider delayDuration={200}>
      <div className={cn('flex items-center gap-1', className)}>
        {visibleSignals.map((signal, index) => {
          const style = getSignalStyle(signal.type);
          const Icon = style.icon;
          const label = signalTypeStyles[signal.type.toLowerCase().replace(/-/g, '_')]
            ? style.label
            : formatSignalType(signal.type);

          return (
            <Tooltip key={`${signal.type}-${index}`}>
              <TooltipTrigger asChild>
                <div
                  className={cn(
                    uniformBadgeClass,
                    style.bgClass,
                    style.textClass,
                    style.borderClass
                  )}
                >
                  <Icon className="w-3.5 h-3.5" />
                </div>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="max-w-xs">
                <p className="font-semibold mb-1">{label}</p>
                <p className="text-xs text-muted-foreground">{signal.detail}</p>
              </TooltipContent>
            </Tooltip>
          );
        })}

        {hiddenCount > 0 && (
          <Tooltip>
            <TooltipTrigger asChild>
              <div
                className={cn(
                  uniformBadgeClass,
                  'bg-muted text-muted-foreground border-border text-xs font-medium'
                )}
              >
                +{hiddenCount}
              </div>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="max-w-xs">
              <p className="font-semibold mb-1">Additional Signals</p>
              <ul className="text-xs text-muted-foreground space-y-1">
                {signals.slice(maxVisible).map((signal, index) => (
                  <li key={index}>
                    <span className="font-medium">{formatSignalType(signal.type)}:</span>{' '}
                    {signal.detail}
                  </li>
                ))}
              </ul>
            </TooltipContent>
          </Tooltip>
        )}
      </div>
    </TooltipProvider>
  );
});

export default SignalBadges;
