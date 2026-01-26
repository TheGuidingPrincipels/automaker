/**
 * Knowledge Hub Page - Gallery view for knowledge sections
 *
 * Displays three main sections as cards:
 * - Knowledge Library: Personal knowledge with AI-powered organization
 * - Knowledge Server: Company knowledge storage
 * - Learning: Agent learnings from task execution
 */

import { useNavigate } from '@tanstack/react-router';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Library, Database, GraduationCap, ArrowRight, Wifi, WifiOff } from 'lucide-react';
import type { KnowledgeSection } from '@automaker/types';
import { KnowledgeHubHeader } from './components/knowledge-hub-header';
import { useKLHealth } from '@/hooks/queries/use-knowledge-library';

interface SectionInfo {
  id: KnowledgeSection;
  name: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  itemCount: number | string;
  color: string;
  features: string[];
  status?: 'connected' | 'offline';
}

const createSections = (
  apiConnected: boolean,
  libraryStats?: { files: number; categories: number }
): SectionInfo[] => [
  {
    id: 'knowledge-library',
    name: 'Knowledge Library',
    description:
      'Extract, organize, and query your knowledge base using AI-powered pipelines. Upload documents that are cleaned, routed, and stored intelligently.',
    icon: Library,
    itemCount: libraryStats?.files ?? (apiConnected ? 0 : '-'),
    color: apiConnected ? 'from-emerald-500/20 to-teal-600/10' : 'from-gray-500/20 to-gray-600/10',
    features: ['AI extraction', 'Smart routing', 'RAG queries', 'Document upload'],
    status: apiConnected ? 'connected' : 'offline',
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
      <div
        className={`h-24 bg-gradient-to-br ${section.color} flex items-center justify-center relative`}
      >
        <Icon className="h-12 w-12 text-primary/70 group-hover:text-primary group-hover:scale-110 transition-all" />
        {section.status && (
          <div className="absolute top-2 right-2">
            {section.status === 'connected' ? (
              <div className="flex items-center gap-1 bg-emerald-500/20 text-emerald-600 px-2 py-0.5 rounded-full text-xs">
                <Wifi className="h-3 w-3" />
                <span>Connected</span>
              </div>
            ) : (
              <div className="flex items-center gap-1 bg-gray-500/20 text-gray-500 px-2 py-0.5 rounded-full text-xs">
                <WifiOff className="h-3 w-3" />
                <span>Offline</span>
              </div>
            )}
          </div>
        )}
      </div>

      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-xl">{section.name}</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              {typeof section.itemCount === 'number'
                ? `${section.itemCount} items`
                : section.itemCount}
            </p>
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
  const { data: klHealth, isLoading: isHealthLoading, isError: isKLError } = useKLHealth();

  // Knowledge Library API uses status: 'healthy' | 'ok'
  const apiConnected = !isKLError && (klHealth?.status === 'healthy' || klHealth?.status === 'ok');
  // KL health doesn't provide stats, use undefined
  const libraryStats: { files: number; categories: number } | undefined = undefined;

  const sections = createSections(apiConnected, libraryStats);

  const handleSectionClick = (sectionId: KnowledgeSection) => {
    navigate({ to: '/knowledge-hub/$section', params: { section: sectionId } });
  };

  const totalItems = sections.reduce(
    (sum, s) => (typeof s.itemCount === 'number' ? sum + s.itemCount : sum),
    0
  );

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
          {sections.map((section) => (
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
                <div
                  className={`flex h-10 w-10 items-center justify-center rounded-lg ${apiConnected ? 'bg-emerald-500/10' : 'bg-gray-500/10'}`}
                >
                  <Library
                    className={`h-5 w-5 ${apiConnected ? 'text-emerald-500' : 'text-gray-500'}`}
                  />
                </div>
                <div>
                  <p className="text-2xl font-bold">
                    {isHealthLoading ? '...' : apiConnected ? 'Ready' : 'Offline'}
                  </p>
                  <p className="text-sm text-muted-foreground">Knowledge Library</p>
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
                  <p className="text-2xl font-bold">{sections[1].itemCount}</p>
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
                  <p className="text-2xl font-bold">{sections[2].itemCount}</p>
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
