import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuLabel,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
} from '@/components/ui/dropdown-menu';
import {
  Trash2,
  MoreHorizontal,
  GitCommit,
  GitPullRequest,
  Download,
  Upload,
  Play,
  Square,
  Globe,
  MessageSquare,
  GitMerge,
  AlertCircle,
  RefreshCw,
  Copy,
  Eye,
  Terminal,
  ScrollText,
  Undo2,
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import type {
  WorktreeInfo,
  DevServerInfo,
  PRInfo,
  GitRepoStatus,
  ConflictResolutionSource,
} from '../types';
import { TooltipWrapper } from './tooltip-wrapper';
import { useAvailableEditors, useEffectiveDefaultEditor } from '../hooks/use-available-editors';
import { getEditorIcon } from '@/components/icons/editor-icons';

interface WorktreeActionsDropdownProps {
  worktree: WorktreeInfo;
  isSelected: boolean;
  aheadCount: number;
  behindCount: number;
  hasRemoteTracking: boolean;
  isPulling: boolean;
  isPushing: boolean;
  isStartingDevServer: boolean;
  isDevServerRunning: boolean;
  devServerInfo?: DevServerInfo;
  gitRepoStatus: GitRepoStatus;
  /** When true, renders as a standalone button (not attached to another element) */
  standalone?: boolean;
  /** Target branch for merge operations (defaults to 'main') */
  targetBranch?: string;
  onOpenChange: (open: boolean) => void;
  onPull: (worktree: WorktreeInfo) => void;
  onPush: (worktree: WorktreeInfo) => void;
  onOpenInEditor: (worktree: WorktreeInfo, editorCommand?: string) => void;
  onOpenInTerminal: (worktree: WorktreeInfo) => void;
  onViewChanges: (worktree: WorktreeInfo) => void;
  onDiscardChanges: (worktree: WorktreeInfo) => void;
  onCommit: (worktree: WorktreeInfo) => void;
  onCreatePR: (worktree: WorktreeInfo) => void;
  onAddressPRComments: (worktree: WorktreeInfo, prInfo: PRInfo) => void;
  onResolveConflicts: (worktree: WorktreeInfo, source: ConflictResolutionSource) => void;
  onMerge: (worktree: WorktreeInfo) => void;
  onDeleteWorktree: (worktree: WorktreeInfo) => void;
  onStartDevServer: (worktree: WorktreeInfo) => void;
  onStopDevServer: (worktree: WorktreeInfo) => void;
  onOpenDevServerUrl: (worktree: WorktreeInfo) => void;
  onViewDevServerLogs: (worktree: WorktreeInfo) => void;
  onRunInitScript: (worktree: WorktreeInfo) => void;
  hasInitScript: boolean;
}

export function WorktreeActionsDropdown({
  worktree,
  isSelected,
  aheadCount,
  behindCount,
  hasRemoteTracking,
  isPulling,
  isPushing,
  isStartingDevServer,
  isDevServerRunning,
  devServerInfo,
  gitRepoStatus,
  standalone = false,
  targetBranch = 'main',
  onOpenChange,
  onPull,
  onPush,
  onOpenInEditor,
  onOpenInTerminal,
  onViewChanges,
  onDiscardChanges,
  onCommit,
  onCreatePR,
  onAddressPRComments,
  onResolveConflicts,
  onMerge,
  onDeleteWorktree,
  onStartDevServer,
  onStopDevServer,
  onOpenDevServerUrl,
  onViewDevServerLogs,
  onRunInitScript,
  hasInitScript,
}: WorktreeActionsDropdownProps) {
  // Get available editors for the "Open In" submenu
  const { editors } = useAvailableEditors();

  // Use shared hook for effective default editor
  const effectiveDefaultEditor = useEffectiveDefaultEditor(editors);

  // Get other editors (excluding the default) for the submenu
  const otherEditors = editors.filter((e) => e.command !== effectiveDefaultEditor?.command);

  // Get icon component for the effective editor (avoid IIFE in JSX)
  const DefaultEditorIcon = effectiveDefaultEditor
    ? getEditorIcon(effectiveDefaultEditor.command)
    : null;

  // Check if there's a PR associated with this worktree from stored metadata
  const hasPR = !!worktree.pr;

  // Check git operations availability
  const canPerformGitOps = gitRepoStatus.isGitRepo && gitRepoStatus.hasCommits;
  const gitOpsDisabledReason = !gitRepoStatus.isGitRepo
    ? 'Not a git repository'
    : !gitRepoStatus.hasCommits
      ? 'Repository has no commits yet'
      : null;

  return (
    <DropdownMenu onOpenChange={onOpenChange}>
      <DropdownMenuTrigger asChild>
        <Button
          variant={standalone ? 'outline' : isSelected ? 'default' : 'outline'}
          size="sm"
          className={cn(
            'h-7 w-7 p-0',
            !standalone && 'rounded-l-none',
            standalone && 'h-8 w-8 shrink-0',
            !standalone && isSelected && 'bg-primary text-primary-foreground',
            !standalone && !isSelected && 'bg-secondary/50 hover:bg-secondary'
          )}
        >
          <MoreHorizontal className="w-3.5 h-3.5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        {/* Warning label when git operations are not available */}
        {!canPerformGitOps && (
          <>
            <DropdownMenuLabel className="text-xs flex items-center gap-2 text-amber-600 dark:text-amber-400">
              <AlertCircle className="w-3.5 h-3.5" />
              {gitOpsDisabledReason}
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
          </>
        )}
        {isDevServerRunning ? (
          <>
            <DropdownMenuLabel className="text-xs flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              Dev Server Running (:{devServerInfo?.port})
            </DropdownMenuLabel>
            <DropdownMenuItem
              onClick={() => onOpenDevServerUrl(worktree)}
              className="text-xs"
              aria-label={`Open dev server on port ${devServerInfo?.port} in browser`}
            >
              <Globe className="w-3.5 h-3.5 mr-2" aria-hidden="true" />
              Open in Browser
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onViewDevServerLogs(worktree)} className="text-xs">
              <ScrollText className="w-3.5 h-3.5 mr-2" />
              View Logs
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => onStopDevServer(worktree)}
              className="text-xs text-destructive focus:text-destructive"
            >
              <Square className="w-3.5 h-3.5 mr-2" />
              Stop Dev Server
            </DropdownMenuItem>
            <DropdownMenuSeparator />
          </>
        ) : (
          <>
            <DropdownMenuItem
              onClick={() => onStartDevServer(worktree)}
              disabled={isStartingDevServer}
              className="text-xs"
            >
              <Play className={cn('w-3.5 h-3.5 mr-2', isStartingDevServer && 'animate-pulse')} />
              {isStartingDevServer ? 'Starting...' : 'Start Dev Server'}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
          </>
        )}
        <TooltipWrapper showTooltip={!!gitOpsDisabledReason} tooltipContent={gitOpsDisabledReason}>
          <DropdownMenuItem
            onClick={() => canPerformGitOps && onPull(worktree)}
            disabled={isPulling || !canPerformGitOps}
            className={cn('text-xs', !canPerformGitOps && 'opacity-50 cursor-not-allowed')}
          >
            <Download className={cn('w-3.5 h-3.5 mr-2', isPulling && 'animate-pulse')} />
            {isPulling ? 'Pulling...' : 'Pull'}
            {!canPerformGitOps && <AlertCircle className="w-3 h-3 ml-auto text-muted-foreground" />}
            {canPerformGitOps && behindCount > 0 && (
              <span className="ml-auto text-[10px] bg-muted px-1.5 py-0.5 rounded">
                {behindCount} behind
              </span>
            )}
          </DropdownMenuItem>
        </TooltipWrapper>
        <TooltipWrapper showTooltip={!!gitOpsDisabledReason} tooltipContent={gitOpsDisabledReason}>
          <DropdownMenuItem
            onClick={() => canPerformGitOps && onPush(worktree)}
            disabled={isPushing || (hasRemoteTracking && aheadCount === 0) || !canPerformGitOps}
            className={cn('text-xs', !canPerformGitOps && 'opacity-50 cursor-not-allowed')}
          >
            <Upload className={cn('w-3.5 h-3.5 mr-2', isPushing && 'animate-pulse')} />
            {isPushing ? 'Pushing...' : 'Push'}
            {!canPerformGitOps && <AlertCircle className="w-3 h-3 ml-auto text-muted-foreground" />}
            {canPerformGitOps && aheadCount > 0 && (
              <span className="ml-auto text-[10px] bg-primary/20 text-primary px-1.5 py-0.5 rounded">
                {aheadCount} ahead
              </span>
            )}
            {canPerformGitOps && !hasRemoteTracking && (
              <span className="ml-auto text-[10px] bg-amber-500/20 text-amber-600 px-1.5 py-0.5 rounded">
                new
              </span>
            )}
          </DropdownMenuItem>
        </TooltipWrapper>
        {/* For main branch (non-worktree), show direct pull & resolve - uses the main worktree's current branch */}
        {worktree.isMain ? (
          <TooltipWrapper
            showTooltip={!!gitOpsDisabledReason}
            tooltipContent={gitOpsDisabledReason}
          >
            <DropdownMenuItem
              onClick={() => canPerformGitOps && onResolveConflicts(worktree, 'selected')}
              disabled={!canPerformGitOps}
              className={cn(
                'text-xs text-purple-500 focus:text-purple-600',
                !canPerformGitOps && 'opacity-50 cursor-not-allowed'
              )}
            >
              <GitMerge className="w-3.5 h-3.5 mr-2" />
              Pull & Resolve Conflicts
              {!canPerformGitOps && <AlertCircle className="w-3 h-3 ml-2 text-muted-foreground" />}
            </DropdownMenuItem>
          </TooltipWrapper>
        ) : (
          /* For worktrees (non-main), show submenu with options */
          <TooltipWrapper
            showTooltip={!!gitOpsDisabledReason}
            tooltipContent={gitOpsDisabledReason}
          >
            <DropdownMenuSub>
              <DropdownMenuSubTrigger
                disabled={!canPerformGitOps}
                className={cn(
                  'text-xs text-purple-500 focus:text-purple-600',
                  !canPerformGitOps && 'opacity-50 cursor-not-allowed'
                )}
              >
                <GitMerge className="w-3.5 h-3.5 mr-2" />
                Pull & Resolve Conflicts
                {!canPerformGitOps && (
                  <AlertCircle className="w-3 h-3 ml-auto text-muted-foreground" />
                )}
              </DropdownMenuSubTrigger>
              <DropdownMenuSubContent>
                <DropdownMenuItem
                  onClick={() => canPerformGitOps && onResolveConflicts(worktree, 'worktree')}
                  disabled={!canPerformGitOps}
                  className="text-xs"
                >
                  Worktree Branch
                  <span className="ml-1 text-[10px] text-muted-foreground">{worktree.branch}</span>
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => canPerformGitOps && onResolveConflicts(worktree, 'selected')}
                  disabled={!canPerformGitOps}
                  className="text-xs"
                >
                  Main Branch
                  <span className="ml-1 text-[10px] text-muted-foreground">{targetBranch}</span>
                </DropdownMenuItem>
              </DropdownMenuSubContent>
            </DropdownMenuSub>
          </TooltipWrapper>
        )}
        {!worktree.isMain && (
          <TooltipWrapper
            showTooltip={!!gitOpsDisabledReason}
            tooltipContent={gitOpsDisabledReason}
          >
            <DropdownMenuItem
              onClick={() => canPerformGitOps && onMerge(worktree)}
              disabled={!canPerformGitOps}
              className={cn(
                'text-xs text-green-600 focus:text-green-700',
                !canPerformGitOps && 'opacity-50 cursor-not-allowed'
              )}
            >
              <GitMerge className="w-3.5 h-3.5 mr-2" />
              Merge to {targetBranch}
              {!canPerformGitOps && (
                <AlertCircle className="w-3 h-3 ml-auto text-muted-foreground" />
              )}
            </DropdownMenuItem>
          </TooltipWrapper>
        )}
        <DropdownMenuSeparator />
        {/* Open in editor - split button: click main area for default, chevron for other options */}
        {effectiveDefaultEditor && (
          <DropdownMenuSub>
            <div className="flex items-center">
              {/* Main clickable area - opens in default editor */}
              <DropdownMenuItem
                onClick={() => onOpenInEditor(worktree, effectiveDefaultEditor.command)}
                className="text-xs flex-1 pr-0 rounded-r-none"
              >
                {DefaultEditorIcon && <DefaultEditorIcon className="w-3.5 h-3.5 mr-2" />}
                Open in {effectiveDefaultEditor.name}
              </DropdownMenuItem>
              {/* Chevron trigger for submenu with other editors and Copy Path */}
              <DropdownMenuSubTrigger className="text-xs px-1 rounded-l-none border-l border-border/30 h-8" />
            </div>
            <DropdownMenuSubContent>
              {/* Other editors */}
              {otherEditors.map((editor) => {
                const EditorIcon = getEditorIcon(editor.command);
                return (
                  <DropdownMenuItem
                    key={editor.command}
                    onClick={() => onOpenInEditor(worktree, editor.command)}
                    className="text-xs"
                  >
                    <EditorIcon className="w-3.5 h-3.5 mr-2" />
                    {editor.name}
                  </DropdownMenuItem>
                );
              })}
              {otherEditors.length > 0 && <DropdownMenuSeparator />}
              <DropdownMenuItem
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(worktree.path);
                    toast.success('Path copied to clipboard');
                  } catch {
                    toast.error('Failed to copy path to clipboard');
                  }
                }}
                className="text-xs"
              >
                <Copy className="w-3.5 h-3.5 mr-2" />
                Copy Path
              </DropdownMenuItem>
            </DropdownMenuSubContent>
          </DropdownMenuSub>
        )}
        <DropdownMenuItem onClick={() => onOpenInTerminal(worktree)} className="text-xs">
          <Terminal className="w-3.5 h-3.5 mr-2" />
          Open in Terminal
        </DropdownMenuItem>
        {!worktree.isMain && hasInitScript && (
          <DropdownMenuItem onClick={() => onRunInitScript(worktree)} className="text-xs">
            <RefreshCw className="w-3.5 h-3.5 mr-2" />
            Re-run Init Script
          </DropdownMenuItem>
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => onViewChanges(worktree)} className="text-xs">
          <Eye className="w-3.5 h-3.5 mr-2" />
          View Changes
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        {worktree.hasChanges && (
          <TooltipWrapper
            showTooltip={!gitRepoStatus.isGitRepo}
            tooltipContent="Not a git repository"
          >
            <DropdownMenuItem
              onClick={() => gitRepoStatus.isGitRepo && onCommit(worktree)}
              disabled={!gitRepoStatus.isGitRepo}
              className={cn('text-xs', !gitRepoStatus.isGitRepo && 'opacity-50 cursor-not-allowed')}
            >
              <GitCommit className="w-3.5 h-3.5 mr-2" />
              Commit Changes
              {!gitRepoStatus.isGitRepo && (
                <AlertCircle className="w-3 h-3 ml-auto text-muted-foreground" />
              )}
            </DropdownMenuItem>
          </TooltipWrapper>
        )}
        {worktree.hasChanges && (
          <TooltipWrapper
            showTooltip={!gitRepoStatus.isGitRepo}
            tooltipContent="Not a git repository"
          >
            <DropdownMenuItem
              onClick={() => gitRepoStatus.isGitRepo && onDiscardChanges(worktree)}
              disabled={!gitRepoStatus.isGitRepo}
              className={cn(
                'text-xs text-destructive focus:text-destructive',
                !gitRepoStatus.isGitRepo && 'opacity-50 cursor-not-allowed'
              )}
            >
              <Undo2 className="w-3.5 h-3.5 mr-2" />
              Discard Changes
              {!gitRepoStatus.isGitRepo && (
                <AlertCircle className="w-3 h-3 ml-auto text-muted-foreground" />
              )}
            </DropdownMenuItem>
          </TooltipWrapper>
        )}
        {/* Show PR option for non-primary worktrees, or primary worktree with changes */}
        {(!worktree.isMain || worktree.hasChanges) && !hasPR && (
          <TooltipWrapper
            showTooltip={!!gitOpsDisabledReason}
            tooltipContent={gitOpsDisabledReason}
          >
            <DropdownMenuItem
              onClick={() => canPerformGitOps && onCreatePR(worktree)}
              disabled={!canPerformGitOps}
              className={cn('text-xs', !canPerformGitOps && 'opacity-50 cursor-not-allowed')}
            >
              <GitPullRequest className="w-3.5 h-3.5 mr-2" />
              Create Pull Request
              {!canPerformGitOps && (
                <AlertCircle className="w-3 h-3 ml-auto text-muted-foreground" />
              )}
            </DropdownMenuItem>
          </TooltipWrapper>
        )}
        {/* Show PR info and Address Comments button if PR exists */}
        {hasPR && worktree.pr && (
          <>
            <DropdownMenuItem
              onClick={() => {
                window.open(worktree.pr!.url, '_blank', 'noopener,noreferrer');
              }}
              className="text-xs"
            >
              <GitPullRequest className="w-3 h-3 mr-2" />
              PR #{worktree.pr.number}
              <span className="ml-auto text-[10px] bg-green-500/20 text-green-600 px-1.5 py-0.5 rounded uppercase">
                {worktree.pr.state}
              </span>
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => {
                // Convert stored PR info to the full PRInfo format for the handler
                // The handler will fetch full comments from GitHub
                const prInfo: PRInfo = {
                  number: worktree.pr!.number,
                  title: worktree.pr!.title,
                  url: worktree.pr!.url,
                  state: worktree.pr!.state,
                  author: '', // Will be fetched
                  body: '', // Will be fetched
                  comments: [],
                  reviewComments: [],
                };
                onAddressPRComments(worktree, prInfo);
              }}
              className="text-xs text-blue-500 focus:text-blue-600"
            >
              <MessageSquare className="w-3.5 h-3.5 mr-2" />
              Address PR Comments
            </DropdownMenuItem>
          </>
        )}
        {!worktree.isMain && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => onDeleteWorktree(worktree)}
              className="text-xs text-destructive focus:text-destructive"
            >
              <Trash2 className="w-3.5 h-3.5 mr-2" />
              Delete Worktree
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
