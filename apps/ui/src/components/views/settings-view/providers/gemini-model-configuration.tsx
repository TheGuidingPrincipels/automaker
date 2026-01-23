import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';
import type { GeminiModelId } from '@automaker/types';
import { GeminiIcon } from '@/components/ui/provider-icon';
import { GEMINI_MODEL_MAP } from '@automaker/types';

interface GeminiModelConfigurationProps {
  enabledGeminiModels: GeminiModelId[];
  geminiDefaultModel: GeminiModelId;
  isSaving: boolean;
  onDefaultModelChange: (model: GeminiModelId) => void;
  onModelToggle: (model: GeminiModelId, enabled: boolean) => void;
}

interface GeminiModelInfo {
  id: GeminiModelId;
  label: string;
  description: string;
  supportsThinking: boolean;
}

// Build model info from the GEMINI_MODEL_MAP
const GEMINI_MODEL_INFO: Record<GeminiModelId, GeminiModelInfo> = Object.fromEntries(
  Object.entries(GEMINI_MODEL_MAP).map(([id, config]) => [
    id as GeminiModelId,
    {
      id: id as GeminiModelId,
      label: config.label,
      description: config.description,
      supportsThinking: config.supportsThinking,
    },
  ])
) as Record<GeminiModelId, GeminiModelInfo>;

export function GeminiModelConfiguration({
  enabledGeminiModels,
  geminiDefaultModel,
  isSaving,
  onDefaultModelChange,
  onModelToggle,
}: GeminiModelConfigurationProps) {
  const availableModels = Object.values(GEMINI_MODEL_INFO);

  return (
    <div
      className={cn(
        'rounded-2xl overflow-hidden',
        'border border-border/50',
        'bg-gradient-to-br from-card/90 via-card/70 to-card/80 backdrop-blur-xl',
        'shadow-sm shadow-black/5'
      )}
    >
      <div className="p-6 border-b border-border/50 bg-gradient-to-r from-transparent via-accent/5 to-transparent">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500/20 to-blue-600/10 flex items-center justify-center border border-blue-500/20">
            <GeminiIcon className="w-5 h-5 text-blue-500" />
          </div>
          <h2 className="text-lg font-semibold text-foreground tracking-tight">
            Model Configuration
          </h2>
        </div>
        <p className="text-sm text-muted-foreground/80 ml-12">
          Configure which Gemini models are available in the feature modal
        </p>
      </div>
      <div className="p-6 space-y-6">
        <div className="space-y-2">
          <Label>Default Model</Label>
          <Select
            value={geminiDefaultModel}
            onValueChange={(v) => onDefaultModelChange(v as GeminiModelId)}
            disabled={isSaving}
          >
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {availableModels.map((model) => (
                <SelectItem key={model.id} value={model.id}>
                  <div className="flex items-center gap-2">
                    <span>{model.label}</span>
                    {model.supportsThinking && (
                      <Badge variant="outline" className="text-xs">
                        Thinking
                      </Badge>
                    )}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-3">
          <Label>Available Models</Label>
          <div className="grid gap-3">
            {availableModels.map((model) => {
              const isEnabled = enabledGeminiModels.includes(model.id);
              const isDefault = model.id === geminiDefaultModel;

              return (
                <div
                  key={model.id}
                  className="flex items-center justify-between p-3 rounded-xl border border-border/50 bg-card/50 hover:bg-accent/30 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <Checkbox
                      checked={isEnabled}
                      onCheckedChange={(checked) => onModelToggle(model.id, !!checked)}
                      disabled={isSaving || isDefault}
                    />
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">{model.label}</span>
                        {model.supportsThinking && (
                          <Badge variant="outline" className="text-xs">
                            Thinking
                          </Badge>
                        )}
                        {isDefault && (
                          <Badge variant="secondary" className="text-xs">
                            Default
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">{model.description}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
