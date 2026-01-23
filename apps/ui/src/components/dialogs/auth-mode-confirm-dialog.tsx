/**
 * AuthModeConfirmDialog - Confirmation dialog for switching authentication modes
 *
 * Shows a confirmation dialog when users attempt to switch between:
 * - Auth Token mode (subscription/CLI OAuth)
 * - API Key mode (pay-per-use)
 *
 * Displays the current and target modes with visual indicators,
 * and warns users about any implications of the mode switch.
 */

import { ShieldCheck, Key, ArrowRight, AlertTriangle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { HotkeyButton } from '@/components/ui/hotkey-button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { AnthropicAuthMode, OpenaiAuthMode } from '@automaker/types';

type AuthMode = AnthropicAuthMode | OpenaiAuthMode;

interface AuthModeConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  currentMode: AuthMode;
  targetMode: AuthMode;
  /** Provider name for display (e.g., "Anthropic", "OpenAI") */
  provider?: string;
  /** Whether the switch is in progress */
  isLoading?: boolean;
  /** Test ID for the dialog */
  testId?: string;
}

const modeConfig: Record<
  AuthMode,
  {
    label: string;
    description: string;
    icon: typeof ShieldCheck;
    badgeVariant: 'success' | 'info';
    colorClass: string;
    bgClass: string;
  }
> = {
  auth_token: {
    label: 'Auth Token',
    description: 'CLI OAuth (Subscription)',
    icon: ShieldCheck,
    badgeVariant: 'success',
    colorClass: 'text-green-500',
    bgClass: 'bg-green-500/10 border-green-500/20',
  },
  api_key: {
    label: 'API Key',
    description: 'Pay-per-use',
    icon: Key,
    badgeVariant: 'info',
    colorClass: 'text-blue-500',
    bgClass: 'bg-blue-500/10 border-blue-500/20',
  },
};

function ModeCard({ mode, isActive }: { mode: AuthMode; isActive?: boolean }) {
  const config = modeConfig[mode];
  const Icon = config.icon;

  return (
    <div
      className={cn(
        'flex items-center gap-3 p-3 rounded-lg border',
        isActive ? config.bgClass : 'bg-muted/30 border-border/50'
      )}
    >
      <div
        className={cn(
          'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
          isActive ? `${config.colorClass} bg-background/50` : 'bg-muted text-muted-foreground'
        )}
      >
        <Icon className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={cn('font-medium text-sm', isActive && config.colorClass)}>
            {config.label}
          </span>
          <Badge variant={config.badgeVariant} size="sm">
            {mode === 'auth_token' ? 'Subscription' : 'Pay-per-use'}
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground mt-0.5">{config.description}</p>
      </div>
    </div>
  );
}

export function AuthModeConfirmDialog({
  open,
  onOpenChange,
  onConfirm,
  currentMode,
  targetMode,
  provider = 'Anthropic',
  isLoading = false,
  testId = 'auth-mode-confirm-dialog',
}: AuthModeConfirmDialogProps) {
  const handleConfirm = () => {
    onConfirm();
  };

  const targetConfig = modeConfig[targetMode];
  const TargetIcon = targetConfig.icon;
  const loginCommand = provider.toLowerCase().includes('openai') ? 'codex login' : 'claude login';

  // Determine if we need to show a warning
  const showApiKeyWarning = targetMode === 'auth_token';
  const showOAuthWarning = targetMode === 'api_key';

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-popover border-border max-w-md" data-testid={testId}>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <TargetIcon className={cn('w-5 h-5', targetConfig.colorClass)} />
            Switch Authentication Mode
          </DialogTitle>
          <DialogDescription className="text-muted-foreground">
            Change {provider} authentication from {modeConfig[currentMode].label.toLowerCase()} to{' '}
            {modeConfig[targetMode].label.toLowerCase()} mode.
          </DialogDescription>
        </DialogHeader>

        {/* Mode Transition Visual */}
        <div className="space-y-3 py-2">
          <div className="flex items-center gap-2">
            <div className="flex-1">
              <ModeCard mode={currentMode} isActive={false} />
            </div>
            <ArrowRight className="w-4 h-4 text-muted-foreground flex-shrink-0" />
            <div className="flex-1">
              <ModeCard mode={targetMode} isActive={true} />
            </div>
          </div>
        </div>

        {/* Warning Messages */}
        {showApiKeyWarning && (
          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
              <div className="text-xs">
                <p className="font-medium text-foreground">API keys will be ignored</p>
                <p className="text-muted-foreground mt-0.5">
                  In Auth Token mode, any configured API keys will be ignored. Make sure you have
                  completed CLI authentication with{' '}
                  <code className="bg-muted px-1 rounded">{loginCommand}</code>.
                </p>
              </div>
            </div>
          </div>
        )}

        {showOAuthWarning && (
          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
              <div className="text-xs">
                <p className="font-medium text-foreground">API key required</p>
                <p className="text-muted-foreground mt-0.5">
                  In API Key mode, you will need to provide a valid {provider} API key. Your
                  subscription benefits will not apply.
                </p>
              </div>
            </div>
          </div>
        )}

        <DialogFooter className="gap-2 sm:gap-2 pt-4">
          <Button
            variant="ghost"
            onClick={() => onOpenChange(false)}
            className="px-4"
            disabled={isLoading}
            data-testid="cancel-auth-mode-switch"
          >
            Cancel
          </Button>
          <HotkeyButton
            variant="default"
            onClick={handleConfirm}
            data-testid="confirm-auth-mode-switch"
            hotkey={{ key: 'Enter', cmdCtrl: true }}
            hotkeyActive={open && !isLoading}
            className="px-4"
            disabled={isLoading}
          >
            {isLoading ? (
              'Switching...'
            ) : (
              <>
                <TargetIcon className="w-4 h-4 mr-2" />
                Switch to {modeConfig[targetMode].label}
              </>
            )}
          </HotkeyButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
