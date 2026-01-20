/**
 * System Detail Page - Detailed view and configuration for a single system
 *
 * Shows system overview, agent configuration, workflow editor, and
 * ability to run the system.
 */

import { useState } from 'react';
import { useParams, useNavigate } from '@tanstack/react-router';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  ArrowLeft,
  Play,
  Settings,
  Users,
  Workflow,
  Zap,
  FileSearch,
  Bug,
  LayoutList,
  ChevronRight,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { System, SystemAgent, SystemAgentRole, SystemExecutionStatus } from '@automaker/types';
import { SystemDetailHeader } from './components/system-detail-header';

// Same mock data as systems page - in real implementation, fetch from API
const MOCK_SYSTEMS: Record<string, System> = {
  'research-system': {
    id: 'research-system',
    name: 'Research System',
    description:
      'Multi-agent research and analysis workflow. Coordinates researcher, analyzer, and summarizer agents to investigate topics and produce comprehensive reports.',
    status: 'active',
    agents: [
      {
        id: 'researcher',
        name: 'Researcher',
        role: 'researcher',
        description: 'Gathers information from various sources',
        order: 1,
      },
      {
        id: 'analyzer',
        name: 'Analyzer',
        role: 'analyzer',
        description: 'Analyzes gathered information for insights',
        order: 2,
      },
      {
        id: 'summarizer',
        name: 'Summarizer',
        role: 'custom',
        description: 'Creates comprehensive summary reports',
        order: 3,
      },
    ],
    workflow: [],
    icon: 'FileSearch',
    category: 'Research',
    tags: ['research', 'analysis', 'documentation'],
    isBuiltIn: true,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
  'code-review-system': {
    id: 'code-review-system',
    name: 'Code Review System',
    description:
      'Comprehensive code review pipeline. Multiple specialized agents review security, performance, and code quality before generating a unified report.',
    status: 'active',
    agents: [
      {
        id: 'security',
        name: 'Security Reviewer',
        role: 'reviewer',
        description: 'Reviews code for security vulnerabilities',
        order: 1,
      },
      {
        id: 'performance',
        name: 'Performance Analyst',
        role: 'analyzer',
        description: 'Analyzes code for performance issues',
        order: 2,
      },
      {
        id: 'quality',
        name: 'Quality Checker',
        role: 'validator',
        description: 'Validates code quality and standards',
        order: 3,
      },
    ],
    workflow: [],
    icon: 'FileSearch',
    category: 'Development',
    tags: ['review', 'security', 'quality'],
    isBuiltIn: true,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
  'feature-planning-system': {
    id: 'feature-planning-system',
    name: 'Feature Planning System',
    description:
      'End-to-end feature planning workflow. Takes requirements and produces technical specifications, task breakdowns, and implementation plans.',
    status: 'active',
    agents: [
      {
        id: 'requirements',
        name: 'Requirements Analyzer',
        role: 'analyzer',
        description: 'Analyzes and clarifies requirements',
        order: 1,
      },
      {
        id: 'architect',
        name: 'Technical Architect',
        role: 'custom',
        description: 'Designs technical architecture',
        order: 2,
      },
      {
        id: 'planner',
        name: 'Task Planner',
        role: 'orchestrator',
        description: 'Breaks down into actionable tasks',
        order: 3,
      },
    ],
    workflow: [],
    icon: 'LayoutList',
    category: 'Planning',
    tags: ['planning', 'architecture', 'requirements'],
    isBuiltIn: true,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
  'bug-investigation-system': {
    id: 'bug-investigation-system',
    name: 'Bug Investigation System',
    description:
      'Automated bug investigation and diagnosis. Reproduces issues, traces root causes, and proposes fixes with test cases.',
    status: 'active',
    agents: [
      {
        id: 'reproducer',
        name: 'Bug Reproducer',
        role: 'custom',
        description: 'Attempts to reproduce the reported bug',
        order: 1,
      },
      {
        id: 'investigator',
        name: 'Root Cause Analyst',
        role: 'analyzer',
        description: 'Investigates the root cause',
        order: 2,
      },
      {
        id: 'fixer',
        name: 'Fix Proposer',
        role: 'implementer',
        description: 'Proposes and implements fixes',
        order: 3,
      },
    ],
    workflow: [],
    icon: 'Bug',
    category: 'Development',
    tags: ['debugging', 'bugfix', 'testing'],
    isBuiltIn: true,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
};

const ROLE_COLORS: Record<SystemAgentRole, string> = {
  orchestrator: 'bg-purple-500/10 text-purple-500 border-purple-500/20',
  researcher: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  analyzer: 'bg-cyan-500/10 text-cyan-500 border-cyan-500/20',
  implementer: 'bg-green-500/10 text-green-500 border-green-500/20',
  reviewer: 'bg-orange-500/10 text-orange-500 border-orange-500/20',
  validator: 'bg-pink-500/10 text-pink-500 border-pink-500/20',
  custom: 'bg-gray-500/10 text-gray-500 border-gray-500/20',
};

function AgentCard({ agent }: { agent: SystemAgent }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{agent.name}</CardTitle>
          <Badge variant="outline" className={cn('text-xs capitalize', ROLE_COLORS[agent.role])}>
            {agent.role}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <CardDescription className="text-sm">
          {agent.description || 'No description'}
        </CardDescription>
      </CardContent>
    </Card>
  );
}

function WorkflowVisualization({ agents }: { agents: SystemAgent[] }) {
  const sortedAgents = [...agents].sort((a, b) => (a.order || 0) - (b.order || 0));

  return (
    <div className="flex items-center gap-4 p-4 bg-muted/50 rounded-lg overflow-x-auto">
      {sortedAgents.map((agent, index) => (
        <div key={agent.id} className="flex items-center gap-4">
          <div className="flex flex-col items-center gap-2 min-w-[120px]">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 border-2 border-primary/30">
              <Users className="h-6 w-6 text-primary" />
            </div>
            <div className="text-center">
              <p className="text-sm font-medium">{agent.name}</p>
              <Badge
                variant="outline"
                className={cn('text-xs capitalize mt-1', ROLE_COLORS[agent.role])}
              >
                {agent.role}
              </Badge>
            </div>
          </div>
          {index < sortedAgents.length - 1 && (
            <ChevronRight className="h-6 w-6 text-muted-foreground flex-shrink-0" />
          )}
        </div>
      ))}
    </div>
  );
}

export function SystemDetailPage() {
  const { systemId } = useParams({ from: '/systems/$systemId' });
  const navigate = useNavigate();
  const [input, setInput] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [executionStatus, setExecutionStatus] = useState<SystemExecutionStatus | null>(null);
  const [output, setOutput] = useState<string | null>(null);

  const system = MOCK_SYSTEMS[systemId];

  const handleBack = () => {
    navigate({ to: '/systems' });
  };

  const handleRun = async () => {
    if (!input.trim()) return;

    setIsRunning(true);
    setExecutionStatus('running');
    setOutput(null);

    // Simulate execution
    setTimeout(() => {
      setIsRunning(false);
      setExecutionStatus('completed');
      setOutput(
        `# Research Report\n\nBased on the query: "${input}"\n\n## Summary\n\nThis is a simulated output from the ${system?.name}. In a real implementation, this would contain the actual results from the multi-agent workflow.\n\n## Key Findings\n\n1. Finding 1\n2. Finding 2\n3. Finding 3\n\n## Recommendations\n\n- Recommendation 1\n- Recommendation 2`
      );
    }, 3000);
  };

  if (!system) {
    return (
      <div className="flex flex-col h-full">
        <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="flex h-14 items-center px-6">
            <Button variant="ghost" size="sm" onClick={handleBack}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Systems
            </Button>
          </div>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <h2 className="text-lg font-semibold mb-2">System Not Found</h2>
            <p className="text-muted-foreground">The requested system could not be found.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <SystemDetailHeader
        system={system}
        onBack={handleBack}
        onRun={() => {}}
        isRunning={isRunning}
      />

      <div className="flex-1 overflow-auto">
        <Tabs defaultValue="overview" className="h-full">
          <div className="border-b px-6">
            <TabsList className="h-12">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="agents">Agents</TabsTrigger>
              <TabsTrigger value="workflow">Workflow</TabsTrigger>
              <TabsTrigger value="run">Run System</TabsTrigger>
            </TabsList>
          </div>

          <div className="p-6">
            <TabsContent value="overview" className="m-0 space-y-6">
              <div>
                <h2 className="text-lg font-semibold mb-2">About</h2>
                <p className="text-muted-foreground">{system.description}</p>
              </div>

              <div>
                <h2 className="text-lg font-semibold mb-4">Workflow Pipeline</h2>
                <WorkflowVisualization agents={system.agents} />
              </div>

              <div className="grid gap-6 md:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Details</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Category</span>
                      <span>{system.category || 'Uncategorized'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Agents</span>
                      <span>{system.agents.length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Type</span>
                      <span>{system.isBuiltIn ? 'Built-in' : 'Custom'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Status</span>
                      <Badge variant="outline" className="capitalize">
                        {system.status}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Tags</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {system.tags?.map((tag) => (
                        <Badge key={tag} variant="secondary">
                          {tag}
                        </Badge>
                      )) || <span className="text-muted-foreground text-sm">No tags</span>}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="agents" className="m-0">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {system.agents.map((agent) => (
                  <AgentCard key={agent.id} agent={agent} />
                ))}
              </div>
            </TabsContent>

            <TabsContent value="workflow" className="m-0">
              <Card>
                <CardHeader>
                  <CardTitle>Workflow Editor</CardTitle>
                  <CardDescription>
                    Configure the workflow steps and agent coordination
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <WorkflowVisualization agents={system.agents} />
                  <p className="text-sm text-muted-foreground mt-4">
                    Visual workflow editor coming soon. Currently using default sequential
                    execution.
                  </p>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="run" className="m-0">
              <div className="max-w-3xl space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Run {system.name}</CardTitle>
                    <CardDescription>Provide input for the system to process</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="input">Input</Label>
                      <Textarea
                        id="input"
                        placeholder="Enter your query or task description..."
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        rows={4}
                        disabled={isRunning}
                      />
                    </div>
                    <Button onClick={handleRun} disabled={!input.trim() || isRunning}>
                      {isRunning ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Running...
                        </>
                      ) : (
                        <>
                          <Play className="mr-2 h-4 w-4" />
                          Run System
                        </>
                      )}
                    </Button>
                  </CardContent>
                </Card>

                {executionStatus && (
                  <Card>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle>Execution Result</CardTitle>
                        <Badge
                          variant="outline"
                          className={cn(
                            'capitalize',
                            executionStatus === 'completed' && 'bg-green-500/10 text-green-500',
                            executionStatus === 'running' && 'bg-blue-500/10 text-blue-500',
                            executionStatus === 'failed' && 'bg-red-500/10 text-red-500'
                          )}
                        >
                          {executionStatus}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent>
                      {isRunning ? (
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          <span>Processing through {system.agents.length} agents...</span>
                        </div>
                      ) : output ? (
                        <div className="prose prose-sm dark:prose-invert max-w-none">
                          <pre className="whitespace-pre-wrap text-sm bg-muted p-4 rounded-lg">
                            {output}
                          </pre>
                        </div>
                      ) : null}
                    </CardContent>
                  </Card>
                )}
              </div>
            </TabsContent>
          </div>
        </Tabs>
      </div>
    </div>
  );
}
