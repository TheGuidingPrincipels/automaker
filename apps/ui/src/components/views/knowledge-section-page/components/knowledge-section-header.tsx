/**
 * Knowledge Section Header - Header for knowledge section pages
 */

import { Button } from '@/components/ui/button';
import { ArrowLeft, Plus } from 'lucide-react';
import type { KnowledgeSection } from '@automaker/types';

interface KnowledgeSectionHeaderProps {
  section: KnowledgeSection;
  config: {
    name: string;
    singularName: string;
    icon: React.ComponentType<{ className?: string }>;
    description: string;
  };
  itemCount: number;
  onBack: () => void;
  onCreate: () => void;
}

export function KnowledgeSectionHeader({
  section,
  config,
  itemCount,
  onBack,
  onCreate,
}: KnowledgeSectionHeaderProps) {
  const Icon = config.icon;

  return (
    <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center justify-between px-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={onBack}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>

          <div className="h-6 w-px bg-border" />

          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
              <Icon className="h-4 w-4 text-primary" />
            </div>
            <div>
              <h1 className="text-lg font-semibold">{config.name}</h1>
              <p className="text-xs text-muted-foreground">{itemCount} items</p>
            </div>
          </div>
        </div>

        <Button size="sm" onClick={onCreate}>
          <Plus className="mr-2 h-4 w-4" />
          Add {config.singularName}
        </Button>
      </div>
    </div>
  );
}
