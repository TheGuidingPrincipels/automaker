/**
 * Create Agent Dialog - Dialog for creating and editing custom agents
 */

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { X } from 'lucide-react';
import type { CustomAgent, CustomAgentTool, CustomAgentModelConfig } from '@automaker/types';

interface CreateAgentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agent: CustomAgent | null;
  onSave: (data: Partial<CustomAgent>) => void;
}

const DEFAULT_TOOLS: CustomAgentTool[] = [
  { name: 'read', enabled: true },
  { name: 'write', enabled: false },
  { name: 'edit', enabled: false },
  { name: 'bash', enabled: false },
  { name: 'grep', enabled: true },
  { name: 'glob', enabled: true },
];

export function CreateAgentDialog({ open, onOpenChange, agent, onSave }: CreateAgentDialogProps) {
  const isEditing = !!agent;

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [model, setModel] = useState<string>('sonnet');
  const [tools, setTools] = useState<CustomAgentTool[]>(DEFAULT_TOOLS);
  const [tagInput, setTagInput] = useState('');
  const [tags, setTags] = useState<string[]>([]);

  // Reset form when dialog opens/closes or agent changes
  useEffect(() => {
    if (open) {
      if (agent) {
        setName(agent.name);
        setDescription(agent.description);
        setSystemPrompt(agent.systemPrompt);
        setModel(agent.modelConfig.model);
        setTools(agent.tools.length > 0 ? agent.tools : DEFAULT_TOOLS);
        setTags(agent.tags || []);
      } else {
        setName('');
        setDescription('');
        setSystemPrompt('');
        setModel('sonnet');
        setTools(DEFAULT_TOOLS);
        setTags([]);
      }
    }
  }, [open, agent]);

  const handleToolToggle = (toolName: string) => {
    setTools((prev) => prev.map((t) => (t.name === toolName ? { ...t, enabled: !t.enabled } : t)));
  };

  const handleAddTag = () => {
    const trimmed = tagInput.trim().toLowerCase();
    if (trimmed && !tags.includes(trimmed)) {
      setTags((prev) => [...prev, trimmed]);
      setTagInput('');
    }
  };

  const handleRemoveTag = (tag: string) => {
    setTags((prev) => prev.filter((t) => t !== tag));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddTag();
    }
  };

  const handleSave = () => {
    const modelConfig: CustomAgentModelConfig = { model };
    onSave({
      name,
      description,
      systemPrompt,
      modelConfig,
      tools,
      tags,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Edit Agent' : 'Create Agent'}</DialogTitle>
          <DialogDescription>
            {isEditing ? 'Update your agent configuration' : 'Configure a new custom AI agent'}
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="basic" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="basic">Basic</TabsTrigger>
            <TabsTrigger value="prompt">Prompt</TabsTrigger>
            <TabsTrigger value="tools">Tools</TabsTrigger>
          </TabsList>

          <TabsContent value="basic" className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                placeholder="Code Reviewer"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Describe what this agent does..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="model">Model</Label>
              <Select value={model} onValueChange={setModel}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a model" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="haiku">Claude Haiku (Fast)</SelectItem>
                  <SelectItem value="sonnet">Claude Sonnet (Balanced)</SelectItem>
                  <SelectItem value="opus">Claude Opus (Powerful)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Tags</Label>
              <div className="flex flex-wrap gap-2 mb-2">
                {tags.map((tag) => (
                  <Badge key={tag} variant="secondary" className="gap-1">
                    {tag}
                    <button
                      type="button"
                      onClick={() => handleRemoveTag(tag)}
                      className="ml-1 rounded-full hover:bg-muted-foreground/20"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
              <Input
                placeholder="Add tag and press Enter..."
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={handleKeyDown}
              />
            </div>
          </TabsContent>

          <TabsContent value="prompt" className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label htmlFor="systemPrompt">System Prompt</Label>
              <Textarea
                id="systemPrompt"
                placeholder="You are an expert code reviewer..."
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                rows={12}
                className="font-mono text-sm"
              />
              <p className="text-xs text-muted-foreground">
                Define the agent's behavior, expertise, and instructions
              </p>
            </div>
          </TabsContent>

          <TabsContent value="tools" className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label>Available Tools</Label>
              <p className="text-xs text-muted-foreground mb-4">
                Select which tools this agent can use
              </p>
              <div className="space-y-3">
                {tools.map((tool) => (
                  <div
                    key={tool.name}
                    className="flex items-center justify-between py-2 px-3 rounded-lg border"
                  >
                    <div>
                      <p className="font-medium capitalize">{tool.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {getToolDescription(tool.name)}
                      </p>
                    </div>
                    <Switch
                      checked={tool.enabled}
                      onCheckedChange={() => handleToolToggle(tool.name)}
                    />
                  </div>
                ))}
              </div>
            </div>
          </TabsContent>
        </Tabs>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={!name.trim()}>
            {isEditing ? 'Save Changes' : 'Create Agent'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function getToolDescription(toolName: string): string {
  const descriptions: Record<string, string> = {
    read: 'Read file contents',
    write: 'Create new files',
    edit: 'Modify existing files',
    bash: 'Execute shell commands',
    grep: 'Search file contents',
    glob: 'Find files by pattern',
  };
  return descriptions[toolName] || 'No description available';
}
