/**
 * Search Bar - Keyword and semantic search toggle
 */

import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search, Type, Brain, X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SearchBarProps {
  query: string;
  onQueryChange: (query: string) => void;
  mode: 'keyword' | 'semantic';
  onModeChange: (mode: 'keyword' | 'semantic') => void;
}

export function SearchBar({ query, onQueryChange, mode, onModeChange }: SearchBarProps) {
  return (
    <div className="flex items-center gap-3">
      {/* Search input */}
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          type="text"
          placeholder={mode === 'semantic' ? 'Search by meaning...' : 'Search by keyword...'}
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          className="pl-9 pr-9"
        />
        {query && (
          <Button
            variant="ghost"
            size="sm"
            className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7 p-0"
            onClick={() => onQueryChange('')}
          >
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* Mode toggle - using button group */}
      <div className="flex border rounded-lg overflow-hidden">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onModeChange('keyword')}
          className={cn('gap-1.5 px-3 rounded-none border-r', mode === 'keyword' && 'bg-muted')}
        >
          <Type className="h-4 w-4" />
          <span className="text-xs">Keyword</span>
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onModeChange('semantic')}
          className={cn('gap-1.5 px-3 rounded-none', mode === 'semantic' && 'bg-muted')}
        >
          <Brain className="h-4 w-4" />
          <span className="text-xs">Semantic</span>
        </Button>
      </div>
    </div>
  );
}
