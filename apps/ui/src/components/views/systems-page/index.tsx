/**
 * Systems Page - Gallery view for multi-agent systems
 *
 * Displays available systems as Notion-like cards that navigate
 * to individual system detail pages.
 */

import { useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Plus, Search, Workflow, Users, Zap, FileSearch, Bug, LayoutList } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { System, SystemStatus } from '@automaker/types';
import { SystemsHeader } from './components/systems-header';

// Built-in systems that come with the application
const BUILT_IN_SYSTEMS: System[] = [
  {
    id: 'research-system',
    name: 'Research System',
    description:
      'Multi-agent research and analysis workflow. Coordinates researcher, analyzer, and summarizer agents to investigate topics and produce comprehensive reports.',
    status: 'active',
    agents: [
      { id: 'researcher', name: 'Researcher', role: 'researcher', order: 1 },
      { id: 'analyzer', name: 'Analyzer', role: 'analyzer', order: 2 },
      { id: 'summarizer', name: 'Summarizer', role: 'custom', order: 3 },
    ],
    workflow: [],
    icon: 'FileSearch',
    category: 'Research',
    tags: ['research', 'analysis', 'documentation'],
    isBuiltIn: true,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
  {
    id: 'code-review-system',
    name: 'Code Review System',
    description:
      'Comprehensive code review pipeline. Multiple specialized agents review security, performance, and code quality before generating a unified report.',
    status: 'active',
    agents: [
      { id: 'security', name: 'Security Reviewer', role: 'reviewer', order: 1 },
      { id: 'performance', name: 'Performance Analyst', role: 'analyzer', order: 2 },
      { id: 'quality', name: 'Quality Checker', role: 'validator', order: 3 },
    ],
    workflow: [],
    icon: 'FileSearch',
    category: 'Development',
    tags: ['review', 'security', 'quality'],
    isBuiltIn: true,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
  {
    id: 'feature-planning-system',
    name: 'Feature Planning System',
    description:
      'End-to-end feature planning workflow. Takes requirements and produces technical specifications, task breakdowns, and implementation plans.',
    status: 'active',
    agents: [
      { id: 'requirements', name: 'Requirements Analyzer', role: 'analyzer', order: 1 },
      { id: 'architect', name: 'Technical Architect', role: 'custom', order: 2 },
      { id: 'planner', name: 'Task Planner', role: 'orchestrator', order: 3 },
    ],
    workflow: [],
    icon: 'LayoutList',
    category: 'Planning',
    tags: ['planning', 'architecture', 'requirements'],
    isBuiltIn: true,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
  {
    id: 'bug-investigation-system',
    name: 'Bug Investigation System',
    description:
      'Automated bug investigation and diagnosis. Reproduces issues, traces root causes, and proposes fixes with test cases.',
    status: 'active',
    agents: [
      { id: 'reproducer', name: 'Bug Reproducer', role: 'custom', order: 1 },
      { id: 'investigator', name: 'Root Cause Analyst', role: 'analyzer', order: 2 },
      { id: 'fixer', name: 'Fix Proposer', role: 'implementer', order: 3 },
    ],
    workflow: [],
    icon: 'Bug',
    category: 'Development',
    tags: ['debugging', 'bugfix', 'testing'],
    isBuiltIn: true,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
];

// Mock user-created systems
const USER_SYSTEMS: System[] = [];

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  FileSearch,
  Bug,
  LayoutList,
  Users,
  Zap,
  Workflow,
};

const STATUS_COLORS: Record<SystemStatus, string> = {
  draft: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
  active: 'bg-green-500/10 text-green-500 border-green-500/20',
  archived: 'bg-gray-500/10 text-gray-500 border-gray-500/20',
};

function SystemCard({ system, onClick }: { system: System; onClick: () => void }) {
  const Icon = ICON_MAP[system.icon || 'Workflow'] || Workflow;

  return (
    <Card
      className="group cursor-pointer hover:border-primary/50 hover:shadow-md transition-all"
      onClick={onClick}
    >
      {/* Card Image/Icon Area */}
      <div className="h-32 bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center border-b">
        <Icon className="h-12 w-12 text-primary/60 group-hover:text-primary transition-colors" />
      </div>

      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-base line-clamp-1">{system.name}</CardTitle>
            <div className="flex items-center gap-2 mt-1">
              <Badge
                variant="outline"
                className={cn('text-xs capitalize', STATUS_COLORS[system.status])}
              >
                {system.status}
              </Badge>
              {system.isBuiltIn && (
                <Badge variant="secondary" className="text-xs">
                  Built-in
                </Badge>
              )}
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <CardDescription className="line-clamp-2 text-sm mb-3">
          {system.description}
        </CardDescription>

        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <Users className="h-3.5 w-3.5" />
            <span>{system.agents.length} agents</span>
          </div>
          {system.category && (
            <>
              <span>•</span>
              <span>{system.category}</span>
            </>
          )}
        </div>

        {system.tags && system.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-3">
            {system.tags.slice(0, 3).map((tag) => (
              <Badge key={tag} variant="outline" className="text-xs px-1.5 py-0">
                {tag}
              </Badge>
            ))}
            {system.tags.length > 3 && (
              <Badge variant="outline" className="text-xs px-1.5 py-0">
                +{system.tags.length - 3}
              </Badge>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function SystemsPage() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');

  const allSystems = [...BUILT_IN_SYSTEMS, ...USER_SYSTEMS];

  // Get unique categories
  const categories = Array.from(
    new Set(allSystems.map((s) => s.category).filter(Boolean))
  ) as string[];

  // Filter systems
  const filteredSystems = allSystems.filter((system) => {
    const matchesSearch =
      !searchQuery.trim() ||
      system.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      system.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      system.tags?.some((tag) => tag.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesCategory = categoryFilter === 'all' || system.category === categoryFilter;

    return matchesSearch && matchesCategory;
  });

  const builtInSystems = filteredSystems.filter((s) => s.isBuiltIn);
  const customSystems = filteredSystems.filter((s) => !s.isBuiltIn);

  const handleSystemClick = (systemId: string) => {
    navigate({ to: '/systems/$systemId', params: { systemId } });
  };

  const handleCreateSystem = () => {
    // TODO: Open create system dialog or navigate to creation page
    console.log('Create new system');
  };

  return (
    <div className="flex flex-col h-full">
      <SystemsHeader
        systemCount={allSystems.length}
        onCreateSystem={handleCreateSystem}
        categoryFilter={categoryFilter}
        onCategoryFilterChange={setCategoryFilter}
        categories={categories}
      />

      <div className="flex-1 overflow-auto p-6">
        {/* Search Bar */}
        <div className="mb-6">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search systems..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
        </div>

        {filteredSystems.length > 0 ? (
          <div className="space-y-8">
            {/* Built-in Systems Section */}
            {builtInSystems.length > 0 && (
              <div>
                <h2 className="text-lg font-semibold mb-4">Built-in Systems</h2>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {builtInSystems.map((system) => (
                    <SystemCard
                      key={system.id}
                      system={system}
                      onClick={() => handleSystemClick(system.id)}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Custom Systems Section */}
            {customSystems.length > 0 && (
              <div>
                <h2 className="text-lg font-semibold mb-4">Custom Systems</h2>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {customSystems.map((system) => (
                    <SystemCard
                      key={system.id}
                      system={system}
                      onClick={() => handleSystemClick(system.id)}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted mb-4">
              <Workflow className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold mb-2">
              {searchQuery || categoryFilter !== 'all' ? 'No systems found' : 'No systems yet'}
            </h3>
            <p className="text-muted-foreground mb-4 max-w-sm">
              {searchQuery || categoryFilter !== 'all'
                ? 'Try adjusting your search or filters'
                : 'Create your first multi-agent system to coordinate complex workflows'}
            </p>
            {!searchQuery && categoryFilter === 'all' && (
              <Button onClick={handleCreateSystem}>
                <Plus className="mr-2 h-4 w-4" />
                Create System
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
