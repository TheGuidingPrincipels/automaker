/**
 * Knowledge Section Page - Dynamic page for viewing a specific knowledge section
 *
 * Renders different content based on the section:
 * - blueprints: Blueprint list and editor
 * - knowledge-server: Knowledge entries list and search
 * - learning: Agent learnings list and details
 */

import { useState } from 'react';
import { useParams, useNavigate } from '@tanstack/react-router';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  ArrowLeft,
  Plus,
  Search,
  FileStack,
  Database,
  GraduationCap,
  MoreVertical,
  Edit,
  Trash2,
  Eye,
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';
import type {
  KnowledgeSection,
  Blueprint,
  KnowledgeEntry,
  Learning,
  BlueprintCategory,
  BlueprintStatus,
  KnowledgeEntryType,
  LearningType,
  LearningConfidence,
} from '@automaker/types';
import { KnowledgeSectionHeader } from './components/knowledge-section-header';

// Mock data for each section
const MOCK_BLUEPRINTS: Blueprint[] = [
  {
    id: 'bp-1',
    name: 'TypeScript Code Standards',
    description: 'Standards for writing TypeScript code in this project',
    content: '# TypeScript Standards\n\n- Use strict mode\n- Prefer interfaces over types\n- ...',
    category: 'coding-standards',
    status: 'active',
    tags: ['typescript', 'standards'],
    priority: 10,
    createdAt: '2024-01-15T10:00:00Z',
    updatedAt: '2024-01-15T10:00:00Z',
  },
  {
    id: 'bp-2',
    name: 'Security Review Guidelines',
    description: 'Guidelines for conducting security reviews',
    content: '# Security Review\n\n- Check for SQL injection\n- Validate all inputs\n- ...',
    category: 'security',
    status: 'active',
    tags: ['security', 'review'],
    priority: 8,
    createdAt: '2024-01-14T10:00:00Z',
    updatedAt: '2024-01-14T10:00:00Z',
  },
  {
    id: 'bp-3',
    name: 'Test Coverage Requirements',
    description: 'Minimum test coverage requirements for new code',
    content: '# Testing Standards\n\n- Minimum 80% coverage\n- Unit tests for all functions\n- ...',
    category: 'testing',
    status: 'active',
    tags: ['testing', 'coverage'],
    priority: 7,
    createdAt: '2024-01-13T10:00:00Z',
    updatedAt: '2024-01-13T10:00:00Z',
  },
];

const MOCK_KNOWLEDGE_ENTRIES: KnowledgeEntry[] = [
  {
    id: 'ke-1',
    title: 'API Authentication Flow',
    description: 'How authentication works in our API',
    content: '# API Authentication\n\nWe use JWT tokens for authentication...',
    type: 'documentation',
    tags: ['api', 'auth', 'jwt'],
    createdAt: '2024-01-15T10:00:00Z',
    updatedAt: '2024-01-15T10:00:00Z',
  },
  {
    id: 'ke-2',
    title: 'Database Schema Overview',
    description: 'Overview of the main database tables',
    content: '# Database Schema\n\nThe database consists of the following main tables...',
    type: 'api-reference',
    tags: ['database', 'schema'],
    createdAt: '2024-01-14T10:00:00Z',
    updatedAt: '2024-01-14T10:00:00Z',
  },
  {
    id: 'ke-3',
    title: 'Deployment Process',
    description: 'Step-by-step deployment guide',
    content: '# Deployment\n\n1. Run tests\n2. Build the application\n3. Deploy to staging...',
    type: 'runbook',
    tags: ['deployment', 'ops'],
    createdAt: '2024-01-13T10:00:00Z',
    updatedAt: '2024-01-13T10:00:00Z',
  },
];

const MOCK_LEARNINGS: Learning[] = [
  {
    id: 'learn-1',
    title: 'Race Condition in User Creation',
    description: 'Fixed a race condition when creating users concurrently',
    content: 'The race condition occurred because we were not using transactions...',
    type: 'bug-fix',
    confidence: 'verified',
    problem: 'Duplicate users created when registration called concurrently',
    solution: 'Wrapped user creation in a database transaction with unique constraint',
    prevention: 'Always use transactions for operations that require atomicity',
    tags: ['database', 'transactions', 'race-condition'],
    applicationCount: 5,
    successRate: 1.0,
    createdAt: '2024-01-15T10:00:00Z',
    updatedAt: '2024-01-15T10:00:00Z',
  },
  {
    id: 'learn-2',
    title: 'Caching Strategy for API Responses',
    description: 'Implemented effective caching for frequently accessed endpoints',
    content: 'Added Redis caching layer for API responses...',
    type: 'optimization',
    confidence: 'high',
    problem: 'Slow API responses under heavy load',
    solution: 'Added Redis caching with 5-minute TTL for read-heavy endpoints',
    prevention: 'Consider caching early for read-heavy endpoints',
    tags: ['performance', 'caching', 'redis'],
    applicationCount: 3,
    successRate: 0.95,
    createdAt: '2024-01-14T10:00:00Z',
    updatedAt: '2024-01-14T10:00:00Z',
  },
];

const SECTION_CONFIG: Record<
  KnowledgeSection,
  {
    name: string;
    singularName: string;
    icon: React.ComponentType<{ className?: string }>;
    description: string;
  }
> = {
  blueprints: {
    name: 'Blueprints',
    singularName: 'Blueprint',
    icon: FileStack,
    description: 'Guidelines and processes for agents',
  },
  'knowledge-server': {
    name: 'Knowledge Server',
    singularName: 'Knowledge Entry',
    icon: Database,
    description: 'Company knowledge storage',
  },
  learning: {
    name: 'Learning',
    singularName: 'Learning',
    icon: GraduationCap,
    description: 'Agent learnings from task execution',
  },
};

const CATEGORY_COLORS: Record<BlueprintCategory, string> = {
  'coding-standards': 'bg-blue-500/10 text-blue-500',
  architecture: 'bg-purple-500/10 text-purple-500',
  testing: 'bg-green-500/10 text-green-500',
  security: 'bg-red-500/10 text-red-500',
  documentation: 'bg-orange-500/10 text-orange-500',
  workflow: 'bg-cyan-500/10 text-cyan-500',
  review: 'bg-yellow-500/10 text-yellow-500',
  deployment: 'bg-pink-500/10 text-pink-500',
  custom: 'bg-gray-500/10 text-gray-500',
};

const CONFIDENCE_COLORS: Record<LearningConfidence, string> = {
  low: 'bg-gray-500/10 text-gray-500',
  medium: 'bg-yellow-500/10 text-yellow-500',
  high: 'bg-green-500/10 text-green-500',
  verified: 'bg-blue-500/10 text-blue-500',
};

function BlueprintCard({ blueprint }: { blueprint: Blueprint }) {
  return (
    <Card className="group hover:border-primary/50 transition-colors">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-base">{blueprint.name}</CardTitle>
            <Badge
              variant="outline"
              className={cn('mt-1 text-xs capitalize', CATEGORY_COLORS[blueprint.category])}
            >
              {blueprint.category.replace('-', ' ')}
            </Badge>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 opacity-0 group-hover:opacity-100"
              >
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem>
                <Eye className="mr-2 h-4 w-4" />
                View
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Edit className="mr-2 h-4 w-4" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem className="text-destructive">
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent>
        <CardDescription className="line-clamp-2 text-sm">{blueprint.description}</CardDescription>
        {blueprint.tags && (
          <div className="flex flex-wrap gap-1 mt-3">
            {blueprint.tags.slice(0, 3).map((tag) => (
              <Badge key={tag} variant="secondary" className="text-xs">
                {tag}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function KnowledgeEntryCard({ entry }: { entry: KnowledgeEntry }) {
  return (
    <Card className="group hover:border-primary/50 transition-colors">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-base">{entry.title}</CardTitle>
            <Badge variant="outline" className="mt-1 text-xs capitalize">
              {entry.type.replace('-', ' ')}
            </Badge>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 opacity-0 group-hover:opacity-100"
              >
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem>
                <Eye className="mr-2 h-4 w-4" />
                View
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Edit className="mr-2 h-4 w-4" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem className="text-destructive">
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent>
        <CardDescription className="line-clamp-2 text-sm">{entry.description}</CardDescription>
        {entry.tags && (
          <div className="flex flex-wrap gap-1 mt-3">
            {entry.tags.slice(0, 3).map((tag) => (
              <Badge key={tag} variant="secondary" className="text-xs">
                {tag}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function LearningCard({ learning }: { learning: Learning }) {
  return (
    <Card className="group hover:border-primary/50 transition-colors">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-base">{learning.title}</CardTitle>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="outline" className="text-xs capitalize">
                {learning.type.replace('-', ' ')}
              </Badge>
              <Badge
                variant="outline"
                className={cn('text-xs capitalize', CONFIDENCE_COLORS[learning.confidence])}
              >
                {learning.confidence}
              </Badge>
            </div>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 opacity-0 group-hover:opacity-100"
              >
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem>
                <Eye className="mr-2 h-4 w-4" />
                View
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Edit className="mr-2 h-4 w-4" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem className="text-destructive">
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent>
        <CardDescription className="line-clamp-2 text-sm">{learning.description}</CardDescription>
        {learning.applicationCount !== undefined && (
          <p className="text-xs text-muted-foreground mt-2">
            Applied {learning.applicationCount} times
            {learning.successRate !== undefined &&
              ` • ${Math.round(learning.successRate * 100)}% success`}
          </p>
        )}
        {learning.tags && (
          <div className="flex flex-wrap gap-1 mt-3">
            {learning.tags.slice(0, 3).map((tag) => (
              <Badge key={tag} variant="secondary" className="text-xs">
                {tag}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function KnowledgeSectionPage() {
  const { section } = useParams({ from: '/knowledge-hub/$section' });
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');

  const sectionId = section as KnowledgeSection;
  const config = SECTION_CONFIG[sectionId];

  const handleBack = () => {
    navigate({ to: '/knowledge-hub' });
  };

  const handleCreate = () => {
    // TODO: Open create dialog based on section
    console.log('Create new item in', sectionId);
  };

  if (!config) {
    return (
      <div className="flex flex-col h-full">
        <div className="border-b bg-background/95 backdrop-blur">
          <div className="flex h-14 items-center px-6">
            <Button variant="ghost" size="sm" onClick={handleBack}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Knowledge Hub
            </Button>
          </div>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <h2 className="text-lg font-semibold mb-2">Section Not Found</h2>
            <p className="text-muted-foreground">The requested section does not exist.</p>
          </div>
        </div>
      </div>
    );
  }

  const Icon = config.icon;

  // Get items based on section
  let items: (Blueprint | KnowledgeEntry | Learning)[] = [];
  if (sectionId === 'blueprints') {
    items = MOCK_BLUEPRINTS;
  } else if (sectionId === 'knowledge-server') {
    items = MOCK_KNOWLEDGE_ENTRIES;
  } else if (sectionId === 'learning') {
    items = MOCK_LEARNINGS;
  }

  return (
    <div className="flex flex-col h-full">
      <KnowledgeSectionHeader
        section={sectionId}
        config={config}
        itemCount={items.length}
        onBack={handleBack}
        onCreate={handleCreate}
      />

      <div className="flex-1 overflow-auto p-6">
        {/* Search Bar */}
        <div className="mb-6">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder={`Search ${config.name.toLowerCase()}...`}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
        </div>

        {/* Items Grid */}
        {items.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {sectionId === 'blueprints' &&
              (items as Blueprint[]).map((item) => (
                <BlueprintCard key={item.id} blueprint={item} />
              ))}
            {sectionId === 'knowledge-server' &&
              (items as KnowledgeEntry[]).map((item) => (
                <KnowledgeEntryCard key={item.id} entry={item} />
              ))}
            {sectionId === 'learning' &&
              (items as Learning[]).map((item) => <LearningCard key={item.id} learning={item} />)}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted mb-4">
              <Icon className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold mb-2">No {config.name.toLowerCase()} yet</h3>
            <p className="text-muted-foreground mb-4 max-w-sm">
              Get started by creating your first {config.singularName.toLowerCase()}
            </p>
            <Button onClick={handleCreate}>
              <Plus className="mr-2 h-4 w-4" />
              Add {config.singularName}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
