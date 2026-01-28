/**
 * Cleanup Mode Selector
 *
 * Dropdown component for selecting the cleanup mode (conservative, balanced, aggressive).
 * Each mode has different confidence thresholds for AI-assisted cleanup suggestions.
 */

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { cn } from '@/lib/utils';
import { ChevronDown, Check, Shield, Scale, Zap } from 'lucide-react';
import {
  KL_CLEANUP_MODE_CONFIG,
  getKLCleanupModeOptions,
  type KLCleanupMode,
} from '@automaker/types';

interface CleanupModeSelectorProps {
  value: KLCleanupMode;
  onChange: (mode: KLCleanupMode) => void;
  disabled?: boolean;
}

/** Icon mapping for each cleanup mode */
const modeIcons: Record<KLCleanupMode, React.ComponentType<{ className?: string }>> = {
  conservative: Shield,
  balanced: Scale,
  aggressive: Zap,
};

export function CleanupModeSelector({ value, onChange, disabled }: CleanupModeSelectorProps) {
  const [open, setOpen] = useState(false);
  const options = getKLCleanupModeOptions();
  const currentConfig = KL_CLEANUP_MODE_CONFIG[value];
  const CurrentIcon = modeIcons[value];

  const handleSelect = (mode: KLCleanupMode) => {
    onChange(mode);
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          disabled={disabled}
          className="gap-2 h-8"
          aria-label={`Cleanup mode: ${currentConfig.label}`}
        >
          <CurrentIcon className="h-4 w-4" />
          <span className="text-xs">{currentConfig.label}</span>
          <ChevronDown className={cn('h-3 w-3 transition-transform', open && 'rotate-180')} />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-72 p-0">
        <div className="p-3 border-b">
          <h4 className="font-medium text-sm">Cleanup Mode</h4>
          <p className="text-xs text-muted-foreground mt-0.5">
            Controls how aggressively AI suggests discarding content
          </p>
        </div>

        <div className="p-2 space-y-1">
          {options.map((option) => {
            const isActive = value === option.value;
            const Icon = modeIcons[option.value];
            const config = KL_CLEANUP_MODE_CONFIG[option.value];

            return (
              <button
                key={option.value}
                onClick={() => handleSelect(option.value)}
                className={cn(
                  'w-full flex items-start gap-3 rounded-md px-3 py-2.5 text-left transition-colors',
                  'hover:bg-accent/50',
                  isActive && 'bg-accent'
                )}
              >
                <Icon className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{option.label}</span>
                    {isActive && <Check className="h-3.5 w-3.5 text-primary shrink-0" />}
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">{option.description}</p>
                  <p className="text-[10px] text-muted-foreground/70 mt-1">
                    Confidence threshold: {Math.round(config.confidenceThreshold * 100)}%
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      </PopoverContent>
    </Popover>
  );
}
