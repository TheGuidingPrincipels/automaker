/**
 * Agents Page - Create and manage custom AI agents
 *
 * This page provides a UI for creating, editing, and managing custom agents
 * that can be used independently or within multi-agent systems.
 */

import { useState, useCallback } from 'react';
import { useAppStore } from '@/store/app-store';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Plus, Search, Cpu, MoreVertical, Edit, Trash2, Copy, Play, Archive } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { CustomAgent, CustomAgentStatus } from '@automaker/types';
import { AgentsHeader } from './components/agents-header';
import { CreateAgentDialog } from './dialogs/create-agent-dialog';

// Mock data for initial development - will be replaced with API calls
const MOCK_AGENTS: CustomAgent[] = [
  {
    id: 'agent-1',
    name: 'Code Reviewer',
    description: 'Reviews code for best practices, security issues, and style consistency',
    systemPrompt: 'You are an expert code reviewer...',
    status: 'active',
    modelConfig: { model: 'sonnet' },
    tools: [
      { name: 'read', enabled: true },
      { name: 'grep', enabled: true },
    ],
    mcpServers: [],
    icon: 'FileSearch',
    tags: ['review', 'quality'],
    createdAt: '2024-01-15T10:00:00Z',
    updatedAt: '2024-01-15T10:00:00Z',
  },
  {
    id: 'agent-2',
    name: 'Test Writer',
    description: 'Generates comprehensive test suites for existing code',
    systemPrompt: 'You are an expert test engineer...',
    status: 'active',
    modelConfig: { model: 'sonnet' },
    tools: [
      { name: 'read', enabled: true },
      { name: 'write', enabled: true },
    ],
    mcpServers: [],
    icon: 'TestTube',
    tags: ['testing', 'automation'],
    createdAt: '2024-01-14T10:00:00Z',
    updatedAt: '2024-01-14T10:00:00Z',
  },
  {
    id: 'agent-3',
    name: 'Documentation Writer',
    description: 'Creates and updates documentation based on code analysis',
    systemPrompt: 'You are a technical documentation expert...',
    status: 'draft',
    modelConfig: { model: 'haiku' },
    tools: [
      { name: 'read', enabled: true },
      { name: 'write', enabled: true },
    ],
    mcpServers: [],
    icon: 'FileText',
    tags: ['documentation'],
    createdAt: '2024-01-13T10:00:00Z',
    updatedAt: '2024-01-13T10:00:00Z',
  },
];

const STATUS_COLORS: Record<CustomAgentStatus, string> = {
  draft: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
  active: 'bg-green-500/10 text-green-500 border-green-500/20',
  archived: 'bg-gray-500/10 text-gray-500 border-gray-500/20',
};

function AgentCard({
  agent,
  onEdit,
  onDuplicate,
  onDelete,
  onArchive,
  onRun,
}: {
  agent: CustomAgent;
  onEdit: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
  onArchive: () => void;
  onRun: () => void;
}) {
  return (
    <Card className="group hover:border-primary/50 transition-colors">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <Cpu className="h-5 w-5 text-primary" />
            </div>
            <div>
              <CardTitle className="text-base">{agent.name}</CardTitle>
              <Badge
                variant="outline"
                className={cn('mt-1 text-xs capitalize', STATUS_COLORS[agent.status])}
              >
                {agent.status}
              </Badge>
            </div>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={onRun}>
                <Play className="mr-2 h-4 w-4" />
                Run Agent
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onEdit}>
                <Edit className="mr-2 h-4 w-4" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onDuplicate}>
                <Copy className="mr-2 h-4 w-4" />
                Duplicate
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={onArchive}>
                <Archive className="mr-2 h-4 w-4" />
                {agent.status === 'archived' ? 'Restore' : 'Archive'}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onDelete} className="text-destructive">
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent>
        <CardDescription className="line-clamp-2 mb-3">{agent.description}</CardDescription>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="capitalize">{agent.modelConfig.model}</span>
          <span>•</span>
          <span>{agent.tools.filter((t) => t.enabled).length} tools</span>
          {agent.tags && agent.tags.length > 0 && (
            <>
              <span>•</span>
              <div className="flex gap-1">
                {agent.tags.slice(0, 2).map((tag) => (
                  <Badge key={tag} variant="secondary" className="text-xs px-1.5 py-0">
                    {tag}
                  </Badge>
                ))}
                {agent.tags.length > 2 && (
                  <Badge variant="secondary" className="text-xs px-1.5 py-0">
                    +{agent.tags.length - 2}
                  </Badge>
                )}
              </div>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function AgentsPage() {
  const { currentProject } = useAppStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [agents, setAgents] = useState<CustomAgent[]>(MOCK_AGENTS);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<CustomAgent | null>(null);
  const [statusFilter, setStatusFilter] = useState<CustomAgentStatus | 'all'>('all');

  // Filter agents based on search and status
  const filteredAgents = agents.filter((agent) => {
    const matchesSearch =
      !searchQuery.trim() ||
      agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      agent.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      agent.tags?.some((tag) => tag.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesStatus = statusFilter === 'all' || agent.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  const handleCreateAgent = useCallback(() => {
    setSelectedAgent(null);
    setIsCreateDialogOpen(true);
  }, []);

  const handleEditAgent = useCallback((agent: CustomAgent) => {
    setSelectedAgent(agent);
    setIsCreateDialogOpen(true);
  }, []);

  const handleDuplicateAgent = useCallback((agent: CustomAgent) => {
    const newAgent: CustomAgent = {
      ...agent,
      id: `agent-${Date.now()}`,
      name: `${agent.name} (Copy)`,
      status: 'draft',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    setAgents((prev) => [...prev, newAgent]);
  }, []);

  const handleDeleteAgent = useCallback((agentId: string) => {
    setAgents((prev) => prev.filter((a) => a.id !== agentId));
  }, []);

  const handleArchiveAgent = useCallback((agentId: string) => {
    setAgents((prev) =>
      prev.map((a) =>
        a.id === agentId
          ? { ...a, status: a.status === 'archived' ? 'active' : ('archived' as CustomAgentStatus) }
          : a
      )
    );
  }, []);

  const handleRunAgent = useCallback((agent: CustomAgent) => {
    // TODO: Navigate to agent runner with this agent selected
    console.log('Run agent:', agent.name);
  }, []);

  const handleSaveAgent = useCallback(
    (agentData: Partial<CustomAgent>) => {
      if (selectedAgent) {
        // Update existing agent
        setAgents((prev) =>
          prev.map((a) =>
            a.id === selectedAgent.id
              ? { ...a, ...agentData, updatedAt: new Date().toISOString() }
              : a
          )
        );
      } else {
        // Create new agent
        const newAgent: CustomAgent = {
          id: `agent-${Date.now()}`,
          name: agentData.name || 'New Agent',
          description: agentData.description || '',
          systemPrompt: agentData.systemPrompt || '',
          status: 'draft',
          modelConfig: agentData.modelConfig || { model: 'sonnet' },
          tools: agentData.tools || [],
          mcpServers: agentData.mcpServers || [],
          icon: agentData.icon,
          tags: agentData.tags,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };
        setAgents((prev) => [...prev, newAgent]);
      }
      setIsCreateDialogOpen(false);
      setSelectedAgent(null);
    },
    [selectedAgent]
  );

  return (
    <div className="flex flex-col h-full">
      <AgentsHeader
        agentCount={agents.length}
        onCreateAgent={handleCreateAgent}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
      />

      <div className="flex-1 overflow-auto p-6">
        {/* Search Bar */}
        <div className="mb-6">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search agents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
        </div>

        {/* Agents Grid */}
        {filteredAgents.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {filteredAgents.map((agent) => (
              <AgentCard
                key={agent.id}
                agent={agent}
                onEdit={() => handleEditAgent(agent)}
                onDuplicate={() => handleDuplicateAgent(agent)}
                onDelete={() => handleDeleteAgent(agent.id)}
                onArchive={() => handleArchiveAgent(agent.id)}
                onRun={() => handleRunAgent(agent)}
              />
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted mb-4">
              <Cpu className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold mb-2">
              {searchQuery || statusFilter !== 'all' ? 'No agents found' : 'No agents yet'}
            </h3>
            <p className="text-muted-foreground mb-4 max-w-sm">
              {searchQuery || statusFilter !== 'all'
                ? 'Try adjusting your search or filters'
                : 'Create your first custom agent to get started with AI-powered automation'}
            </p>
            {!searchQuery && statusFilter === 'all' && (
              <Button onClick={handleCreateAgent}>
                <Plus className="mr-2 h-4 w-4" />
                Create Agent
              </Button>
            )}
          </div>
        )}
      </div>

      <CreateAgentDialog
        open={isCreateDialogOpen}
        onOpenChange={setIsCreateDialogOpen}
        agent={selectedAgent}
        onSave={handleSaveAgent}
      />
    </div>
  );
}
