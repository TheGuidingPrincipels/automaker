/**
 * Knowledge Hub Page - Gallery view for knowledge sections
 *
 * Displays three main sections as cards:
 * - Blueprints: Guidelines and processes for agents
 * - Knowledge Server: Company knowledge storage
 * - Learning: Agent learnings from task execution
 */

import { useNavigate } from '@tanstack/react-router';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { BookOpenCheck, FileStack, Database, GraduationCap, ArrowRight } from 'lucide-react';
import type { KnowledgeSection } from '@automaker/types';
import { KnowledgeHubHeader } from './components/knowledge-hub-header';

interface SectionInfo {
  id: KnowledgeSection;
  name: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  itemCount: number;
  color: string;
  features: string[];
}

const SECTIONS: SectionInfo[] = [
  {
    id: 'blueprints',
    name: 'Blueprints',
    description:
      'Define guidelines, behaviors, and processes that agents follow. Blueprints shape how agents approach tasks and maintain consistency across your team.',
    icon: FileStack,
    itemCount: 12,
    color: 'from-blue-500/20 to-blue-600/10',
    features: [
      'Coding standards',
      'Architecture patterns',
      'Review guidelines',
      'Security practices',
    ],
  },
  {
    id: 'knowledge-server',
    name: 'Knowledge Server',
    description:
      'Store and retrieve company knowledge that agents can access during task execution. Build a searchable knowledge base for your organization.',
    icon: Database,
    itemCount: 47,
    color: 'from-green-500/20 to-green-600/10',
    features: ['Documentation', 'API references', 'Decision records', 'Runbooks'],
  },
  {
    id: 'learning',
    name: 'Learning',
    description:
      'Capture insights and learnings extracted from agent task executions. Learnings improve future agent performance and help avoid repeated mistakes.',
    icon: GraduationCap,
    itemCount: 28,
    color: 'from-purple-500/20 to-purple-600/10',
    features: ['Bug fix patterns', 'Best practices', 'Anti-patterns', 'Tool usage tips'],
  },
];

function SectionCard({ section, onClick }: { section: SectionInfo; onClick: () => void }) {
  const Icon = section.icon;

  return (
    <Card
      className="group cursor-pointer hover:border-primary/50 hover:shadow-lg transition-all overflow-hidden"
      onClick={onClick}
    >
      {/* Header gradient */}
      <div className={`h-24 bg-gradient-to-br ${section.color} flex items-center justify-center`}>
        <Icon className="h-12 w-12 text-primary/70 group-hover:text-primary group-hover:scale-110 transition-all" />
      </div>

      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-xl">{section.name}</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">{section.itemCount} items</p>
          </div>
          <ArrowRight className="h-5 w-5 text-muted-foreground opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
        </div>
      </CardHeader>

      <CardContent>
        <CardDescription className="text-sm mb-4">{section.description}</CardDescription>

        <div className="flex flex-wrap gap-2">
          {section.features.map((feature) => (
            <Badge key={feature} variant="secondary" className="text-xs">
              {feature}
            </Badge>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export function KnowledgeHubPage() {
  const navigate = useNavigate();

  const handleSectionClick = (sectionId: KnowledgeSection) => {
    navigate({ to: '/knowledge-hub/$section', params: { section: sectionId } });
  };

  const totalItems = SECTIONS.reduce((sum, s) => sum + s.itemCount, 0);

  return (
    <div className="flex flex-col h-full">
      <KnowledgeHubHeader totalItems={totalItems} />

      <div className="flex-1 overflow-auto p-6">
        {/* Introduction */}
        <div className="max-w-3xl mb-8">
          <h2 className="text-2xl font-semibold mb-2">Welcome to Knowledge Hub</h2>
          <p className="text-muted-foreground">
            Centralize your team's knowledge, guidelines, and learnings. Knowledge Hub helps your AI
            agents work smarter by providing context, standards, and insights from past experiences.
          </p>
        </div>

        {/* Section Cards */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {SECTIONS.map((section) => (
            <SectionCard
              key={section.id}
              section={section}
              onClick={() => handleSectionClick(section.id)}
            />
          ))}
        </div>

        {/* Quick Stats */}
        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10">
                  <FileStack className="h-5 w-5 text-blue-500" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{SECTIONS[0].itemCount}</p>
                  <p className="text-sm text-muted-foreground">Active Blueprints</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-500/10">
                  <Database className="h-5 w-5 text-green-500" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{SECTIONS[1].itemCount}</p>
                  <p className="text-sm text-muted-foreground">Knowledge Entries</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-500/10">
                  <GraduationCap className="h-5 w-5 text-purple-500" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{SECTIONS[2].itemCount}</p>
                  <p className="text-sm text-muted-foreground">Agent Learnings</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
