import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { MoreHorizontal, Wand2, Zap, Bot } from 'lucide-react';
import { AutoModeSettingsPopover } from './dialogs/auto-mode-settings-popover';
import { PlanSettingsPopover } from './dialogs/plan-settings-popover';
import { cn } from '@/lib/utils';

interface HeaderOverflowMenuProps {
  // Agents control
  shouldCollapseAgents: boolean;
  maxConcurrency: number;
  runningAgentsCount: number;
  onConcurrencyChange: (value: number) => void;
  // Auto mode
  shouldCollapseAutoMode: boolean;
  isAutoModeRunning: boolean;
  onAutoModeToggle: (enabled: boolean) => void;
  skipVerificationInAutoMode: boolean;
  onSkipVerificationChange: (value: boolean) => void;
  // Plan button
  onOpenPlanDialog: () => void;
  planUseSelectedWorktreeBranch: boolean;
  onPlanUseSelectedWorktreeBranchChange: (value: boolean) => void;
}

/**
 * Overflow menu for toolbar items (Agents, Plan and Auto Mode) that collapse
 * when the window width is narrow but not yet mobile-sized.
 */
export function HeaderOverflowMenu({
  shouldCollapseAgents,
  maxConcurrency,
  runningAgentsCount,
  onConcurrencyChange,
  shouldCollapseAutoMode,
  isAutoModeRunning,
  onAutoModeToggle,
  skipVerificationInAutoMode,
  onSkipVerificationChange,
  onOpenPlanDialog,
  planUseSelectedWorktreeBranch,
  onPlanUseSelectedWorktreeBranchChange,
}: HeaderOverflowMenuProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="h-8 w-8 p-0 shrink-0 mr-2"
          data-testid="header-overflow-menu-trigger"
        >
          <MoreHorizontal className="w-4 h-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">
          Controls
        </DropdownMenuLabel>
        <DropdownMenuSeparator />

        {/* Agents Control */}
        {shouldCollapseAgents && (
          <>
            <div className="px-2 py-2" data-testid="overflow-agents-control-container">
              <div className="flex items-center gap-2 mb-3">
                <Bot className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm font-medium">Agents</span>
                <span className="text-sm text-muted-foreground ml-auto">
                  {runningAgentsCount}/{maxConcurrency}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <Slider
                  value={[maxConcurrency]}
                  onValueChange={(value) => onConcurrencyChange(value[0])}
                  min={1}
                  max={10}
                  step={1}
                  className="flex-1"
                  data-testid="overflow-concurrency-slider"
                />
                <span className="text-sm font-medium min-w-[2ch] text-right">{maxConcurrency}</span>
              </div>
            </div>
            <DropdownMenuSeparator />
          </>
        )}

        {/* Auto Mode Toggle */}
        {shouldCollapseAutoMode && (
          <div
            className="flex items-center justify-between px-2 py-2 cursor-pointer hover:bg-accent rounded-sm"
            onClick={() => onAutoModeToggle(!isAutoModeRunning)}
            data-testid="overflow-auto-mode-toggle-container"
          >
            <div className="flex items-center gap-2">
              <Zap
                className={cn(
                  'w-4 h-4',
                  isAutoModeRunning ? 'text-yellow-500' : 'text-muted-foreground'
                )}
              />
              <span className="text-sm font-medium">Auto Mode</span>
            </div>
            <div className="flex items-center gap-2">
              <Switch
                id="overflow-auto-mode-toggle"
                checked={isAutoModeRunning}
                onCheckedChange={onAutoModeToggle}
                onClick={(e) => e.stopPropagation()}
                data-testid="overflow-auto-mode-toggle"
              />
              <div onClick={(e) => e.stopPropagation()}>
                <AutoModeSettingsPopover
                  skipVerificationInAutoMode={skipVerificationInAutoMode}
                  onSkipVerificationChange={onSkipVerificationChange}
                  maxConcurrency={maxConcurrency}
                  runningAgentsCount={runningAgentsCount}
                  onConcurrencyChange={onConcurrencyChange}
                />
              </div>
            </div>
          </div>
        )}

        <DropdownMenuSeparator />

        {/* Plan Button with Settings */}
        <div
          className="flex items-center justify-between px-2 py-2 cursor-pointer hover:bg-accent rounded-sm"
          onClick={onOpenPlanDialog}
          data-testid="overflow-plan-button-container"
        >
          <div className="flex items-center gap-2">
            <Wand2 className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm font-medium">Plan</span>
          </div>
          <div onClick={(e) => e.stopPropagation()}>
            <PlanSettingsPopover
              planUseSelectedWorktreeBranch={planUseSelectedWorktreeBranch}
              onPlanUseSelectedWorktreeBranchChange={onPlanUseSelectedWorktreeBranchChange}
            />
          </div>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
