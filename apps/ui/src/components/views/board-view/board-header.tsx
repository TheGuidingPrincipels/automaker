import { useState, useCallback } from 'react';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Bot, Wand2, GitBranch, PanelLeft } from 'lucide-react';
import { UsagePopover } from '@/components/usage-popover';
import { useAppStore } from '@/store/app-store';
import { useSetupStore } from '@/store/setup-store';
import {
  useIsMobile,
  useIsNarrowToolbarForPlan,
  useIsNarrowToolbarForAutoMode,
  useIsNarrowToolbarForAgents,
} from '@/hooks/use-media-query';

import { AutoModeSettingsPopover } from './dialogs/auto-mode-settings-popover';
import { WorktreeSettingsPopover } from './dialogs/worktree-settings-popover';
import { PlanSettingsPopover } from './dialogs/plan-settings-popover';
import { getHttpApiClient } from '@/lib/http-api-client';
import { BoardSearchBar } from './board-search-bar';
import { BoardControls } from './board-controls';
import { ViewToggle, type ViewMode } from './components';
import { HeaderMobileMenu } from './header-mobile-menu';
import { HeaderOverflowMenu } from './header-overflow-menu';

export type { ViewMode };

interface BoardHeaderProps {
  projectPath: string;
  maxConcurrency: number;
  runningAgentsCount: number;
  onConcurrencyChange: (value: number) => void;
  isAutoModeRunning: boolean;
  onAutoModeToggle: (enabled: boolean) => void;
  onOpenPlanDialog: () => void;
  isMounted: boolean;
  // Search bar props
  searchQuery: string;
  onSearchChange: (query: string) => void;
  isCreatingSpec: boolean;
  creatingSpecProjectPath?: string;
  // Board controls props
  onShowBoardBackground: () => void;
  // View toggle props
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
}

// Shared styles for header control containers
const controlContainerClass =
  'flex flex-shrink-0 items-center gap-1.5 px-3 h-8 rounded-md bg-secondary border border-border whitespace-nowrap';

export function BoardHeader({
  projectPath,
  maxConcurrency,
  runningAgentsCount,
  onConcurrencyChange,
  isAutoModeRunning,
  onAutoModeToggle,
  onOpenPlanDialog,
  isMounted,
  searchQuery,
  onSearchChange,
  isCreatingSpec,
  creatingSpecProjectPath,
  onShowBoardBackground,
  viewMode,
  onViewModeChange,
}: BoardHeaderProps) {
  const claudeAuthStatus = useSetupStore((state) => state.claudeAuthStatus);
  const sidebarOpen = useAppStore((state) => state.sidebarOpen);
  const toggleSidebar = useAppStore((state) => state.toggleSidebar);
  const skipVerificationInAutoMode = useAppStore((state) => state.skipVerificationInAutoMode);
  const setSkipVerificationInAutoMode = useAppStore((state) => state.setSkipVerificationInAutoMode);
  const planUseSelectedWorktreeBranch = useAppStore((state) => state.planUseSelectedWorktreeBranch);
  const setPlanUseSelectedWorktreeBranch = useAppStore(
    (state) => state.setPlanUseSelectedWorktreeBranch
  );
  const addFeatureUseSelectedWorktreeBranch = useAppStore(
    (state) => state.addFeatureUseSelectedWorktreeBranch
  );
  const setAddFeatureUseSelectedWorktreeBranch = useAppStore(
    (state) => state.setAddFeatureUseSelectedWorktreeBranch
  );
  const codexAuthStatus = useSetupStore((state) => state.codexAuthStatus);

  // Worktree panel visibility (per-project)
  const worktreePanelVisibleByProject = useAppStore((state) => state.worktreePanelVisibleByProject);
  const setWorktreePanelVisible = useAppStore((state) => state.setWorktreePanelVisible);
  const isWorktreePanelVisible = worktreePanelVisibleByProject[projectPath] ?? true;

  const handleWorktreePanelToggle = useCallback(
    async (visible: boolean) => {
      // Update local store
      setWorktreePanelVisible(projectPath, visible);

      // Persist to server
      try {
        const httpClient = getHttpApiClient();
        await httpClient.settings.updateProject(projectPath, {
          worktreePanelVisible: visible,
        });
      } catch (error) {
        console.error('Failed to persist worktree panel visibility:', error);
      }
    },
    [projectPath, setWorktreePanelVisible]
  );

  const isClaudeCliVerified = !!claudeAuthStatus?.authenticated;
  const showClaudeUsage = isClaudeCliVerified;

  // Codex usage tracking visibility logic
  // Show if Codex is authenticated (CLI or API key)
  const showCodexUsage = !!codexAuthStatus?.authenticated;

  const isMobile = useIsMobile();
  const isNarrowToolbarForAgents = useIsNarrowToolbarForAgents();
  const isNarrowToolbarForPlan = useIsNarrowToolbarForPlan();
  const isNarrowToolbarForAutoMode = useIsNarrowToolbarForAutoMode();

  // Determine cascade collapse
  const shouldCollapseAgents = !isMobile && isNarrowToolbarForAgents;
  const shouldCollapsePlan = !isMobile && isNarrowToolbarForPlan;
  const shouldCollapseAutoMode = !isMobile && isNarrowToolbarForAutoMode;

  return (
    <div className="flex items-center justify-between gap-4 p-4 border-b border-border bg-glass backdrop-blur-md">
      <div className="flex items-center gap-4">
        {/* Sidebar toggle button - only shows when sidebar is closed on mobile */}
        {isMounted && !sidebarOpen && (
          <button
            onClick={toggleSidebar}
            className="h-11 w-11 p-0 shrink-0 inline-flex items-center justify-center rounded-lg border border-border lg:hidden hover:bg-accent/50 transition-colors"
            aria-label="Open sidebar"
          >
            <PanelLeft className="w-5 h-5" />
          </button>
        )}
        <BoardSearchBar
          searchQuery={searchQuery}
          onSearchChange={onSearchChange}
          isCreatingSpec={isCreatingSpec}
          creatingSpecProjectPath={creatingSpecProjectPath}
          currentProjectPath={projectPath}
        />
        {isMounted && <ViewToggle viewMode={viewMode} onViewModeChange={onViewModeChange} />}
        <BoardControls isMounted={isMounted} onShowBoardBackground={onShowBoardBackground} />
      </div>
      <div className="flex flex-nowrap gap-4 items-center">
        {/* Usage Popover - show if either provider is authenticated, only on desktop */}
        {isMounted && !isMobile && (showClaudeUsage || showCodexUsage) && <UsagePopover />}

        {/* Mobile view: show hamburger menu with all controls */}
        {isMounted && isMobile && (
          <HeaderMobileMenu
            isWorktreePanelVisible={isWorktreePanelVisible}
            onWorktreePanelToggle={handleWorktreePanelToggle}
            maxConcurrency={maxConcurrency}
            runningAgentsCount={runningAgentsCount}
            onConcurrencyChange={onConcurrencyChange}
            isAutoModeRunning={isAutoModeRunning}
            onAutoModeToggle={onAutoModeToggle}
            onOpenAutoModeSettings={() => {}}
            onOpenPlanDialog={onOpenPlanDialog}
            showClaudeUsage={showClaudeUsage}
            showCodexUsage={showCodexUsage}
          />
        )}

        {/* Desktop view: show full controls */}
        {/* Worktrees Toggle - only show after mount to prevent hydration issues */}
        {isMounted && !isMobile && (
          <div className={controlContainerClass} data-testid="worktrees-toggle-container">
            <GitBranch className="w-4 h-4 text-muted-foreground" />
            <Label
              htmlFor="worktrees-toggle"
              className="text-sm font-medium cursor-pointer whitespace-nowrap"
            >
              Worktree Bar
            </Label>
            <Switch
              id="worktrees-toggle"
              checked={isWorktreePanelVisible}
              onCheckedChange={handleWorktreePanelToggle}
              data-testid="worktrees-toggle"
            />
            <WorktreeSettingsPopover
              addFeatureUseSelectedWorktreeBranch={addFeatureUseSelectedWorktreeBranch}
              onAddFeatureUseSelectedWorktreeBranchChange={setAddFeatureUseSelectedWorktreeBranch}
            />
          </div>
        )}

        {/* Concurrency Control - only show after mount to prevent hydration issues, hide when toolbar is narrow */}
        {isMounted && !isMobile && !shouldCollapseAgents && (
          <Popover>
            <PopoverTrigger asChild>
              <button
                className={`${controlContainerClass} cursor-pointer hover:bg-accent/50 transition-colors`}
                data-testid="concurrency-slider-container"
              >
                <Bot className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm font-medium">Agents</span>
                <span className="text-sm text-muted-foreground" data-testid="concurrency-value">
                  {runningAgentsCount}/{maxConcurrency}
                </span>
              </button>
            </PopoverTrigger>
            <PopoverContent className="w-64" align="end">
              <div className="space-y-4">
                <div>
                  <h4 className="font-medium text-sm mb-1">Max Concurrent Agents</h4>
                  <p className="text-xs text-muted-foreground">
                    Controls how many AI agents can run simultaneously. Higher values process more
                    features in parallel but use more API resources.
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <Slider
                    value={[maxConcurrency]}
                    onValueChange={(value) => onConcurrencyChange(value[0])}
                    min={1}
                    max={10}
                    step={1}
                    className="flex-1"
                    data-testid="concurrency-slider"
                  />
                  <span className="text-sm font-medium min-w-[2ch] text-right">
                    {maxConcurrency}
                  </span>
                </div>
              </div>
            </PopoverContent>
          </Popover>
        )}

        {/* Auto Mode Toggle - only show on wider desktop screens (not when collapsed to overflow menu) */}
        {isMounted && !isMobile && !shouldCollapseAutoMode && (
          <div className={controlContainerClass} data-testid="auto-mode-toggle-container">
            <Label
              htmlFor="auto-mode-toggle"
              className="text-sm font-medium cursor-pointer whitespace-nowrap"
            >
              Auto Mode
            </Label>
            <Switch
              id="auto-mode-toggle"
              checked={isAutoModeRunning}
              onCheckedChange={onAutoModeToggle}
              data-testid="auto-mode-toggle"
            />
            <AutoModeSettingsPopover
              skipVerificationInAutoMode={skipVerificationInAutoMode}
              onSkipVerificationChange={setSkipVerificationInAutoMode}
              maxConcurrency={maxConcurrency}
              runningAgentsCount={runningAgentsCount}
              onConcurrencyChange={onConcurrencyChange}
            />
          </div>
        )}

        {/* Plan Button with Settings - only show on wider desktop screens (not when collapsed to overflow menu) */}
        {isMounted && !isMobile && !shouldCollapsePlan && (
          <div className={controlContainerClass} data-testid="plan-button-container">
            <button
              onClick={onOpenPlanDialog}
              className="flex items-center gap-1.5 hover:text-foreground transition-colors"
              data-testid="plan-backlog-button"
            >
              <Wand2 className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-medium">Plan</span>
            </button>
            <PlanSettingsPopover
              planUseSelectedWorktreeBranch={planUseSelectedWorktreeBranch}
              onPlanUseSelectedWorktreeBranchChange={setPlanUseSelectedWorktreeBranch}
            />
          </div>
        )}

        {/* Overflow Menu - shows Agents, Plan and Auto Mode when toolbar is narrow but not mobile */}
        {isMounted && (shouldCollapseAgents || shouldCollapsePlan || shouldCollapseAutoMode) && (
          <HeaderOverflowMenu
            shouldCollapseAgents={shouldCollapseAgents}
            maxConcurrency={maxConcurrency}
            runningAgentsCount={runningAgentsCount}
            onConcurrencyChange={onConcurrencyChange}
            shouldCollapseAutoMode={shouldCollapseAutoMode}
            isAutoModeRunning={isAutoModeRunning}
            onAutoModeToggle={onAutoModeToggle}
            skipVerificationInAutoMode={skipVerificationInAutoMode}
            onSkipVerificationChange={setSkipVerificationInAutoMode}
            onOpenPlanDialog={onOpenPlanDialog}
            planUseSelectedWorktreeBranch={planUseSelectedWorktreeBranch}
            onPlanUseSelectedWorktreeBranchChange={setPlanUseSelectedWorktreeBranch}
          />
        )}
      </div>
    </div>
  );
}
