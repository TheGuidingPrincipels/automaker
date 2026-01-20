/**
 * Systems Header - Header component for the Systems page
 */

import { Button } from '@/components/ui/button';
import { Plus, Workflow } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface SystemsHeaderProps {
  systemCount: number;
  onCreateSystem: () => void;
  categoryFilter: string;
  onCategoryFilterChange: (category: string) => void;
  categories: string[];
}

export function SystemsHeader({
  systemCount,
  onCreateSystem,
  categoryFilter,
  onCategoryFilterChange,
  categories,
}: SystemsHeaderProps) {
  return (
    <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
            <Workflow className="h-4 w-4 text-primary" />
          </div>
          <div>
            <h1 className="text-lg font-semibold">Systems</h1>
            <p className="text-xs text-muted-foreground">{systemCount} systems</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {categories.length > 0 && (
            <Select value={categoryFilter} onValueChange={onCategoryFilterChange}>
              <SelectTrigger className="w-[150px] h-9">
                <SelectValue placeholder="All categories" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All categories</SelectItem>
                {categories.map((category) => (
                  <SelectItem key={category} value={category}>
                    {category}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          <Button onClick={onCreateSystem} size="sm">
            <Plus className="mr-2 h-4 w-4" />
            Create System
          </Button>
        </div>
      </div>
    </div>
  );
}
