/**
 * Category Tree - Collapsible folder navigation for library categories
 */

import { ChevronRight, Folder, FolderOpen } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { KLLibraryCategoryResponse } from '@automaker/types';

interface CategoryTreeProps {
  categories: KLLibraryCategoryResponse[];
  expandedCategories: Set<string>;
  selectedCategoryPath: string | null;
  onCategorySelect: (path: string) => void;
  onCategoryToggle: (path: string) => void;
  depth?: number;
}

export function CategoryTree({
  categories,
  expandedCategories,
  selectedCategoryPath,
  onCategorySelect,
  onCategoryToggle,
  depth = 0,
}: CategoryTreeProps) {
  return (
    <div className={cn('space-y-1', depth > 0 && 'ml-4')}>
      {categories.map((category) => (
        <CategoryItem
          key={category.path}
          category={category}
          isExpanded={expandedCategories.has(category.path)}
          isSelected={selectedCategoryPath === category.path}
          onSelect={() => onCategorySelect(category.path)}
          onToggle={() => onCategoryToggle(category.path)}
          expandedCategories={expandedCategories}
          selectedCategoryPath={selectedCategoryPath}
          onCategorySelect={onCategorySelect}
          onCategoryToggle={onCategoryToggle}
        />
      ))}
    </div>
  );
}

interface CategoryItemProps {
  category: KLLibraryCategoryResponse;
  isExpanded: boolean;
  isSelected: boolean;
  onSelect: () => void;
  onToggle: () => void;
  expandedCategories: Set<string>;
  selectedCategoryPath: string | null;
  onCategorySelect: (path: string) => void;
  onCategoryToggle: (path: string) => void;
}

function CategoryItem({
  category,
  isExpanded,
  isSelected,
  onSelect,
  onToggle,
  expandedCategories,
  selectedCategoryPath,
  onCategorySelect,
  onCategoryToggle,
}: CategoryItemProps) {
  const hasSubcategories = category.subcategories && category.subcategories.length > 0;
  const fileCount = category.files.length;
  const Icon = isExpanded ? FolderOpen : Folder;

  return (
    <div>
      <div
        className={cn(
          'flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer',
          'hover:bg-muted transition-colors',
          isSelected && 'bg-primary/10 text-primary'
        )}
        onClick={onSelect}
      >
        {/* Expand/collapse button */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggle();
          }}
          className={cn(
            'p-0.5 rounded hover:bg-muted-foreground/10 transition-transform',
            !hasSubcategories && 'invisible'
          )}
        >
          <ChevronRight className={cn('h-4 w-4 transition-transform', isExpanded && 'rotate-90')} />
        </button>

        {/* Folder icon */}
        <Icon className={cn('h-4 w-4', isSelected ? 'text-primary' : 'text-muted-foreground')} />

        {/* Category name */}
        <span className="flex-1 text-sm truncate">{category.name}</span>

        {/* File count badge */}
        {fileCount > 0 && (
          <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
            {fileCount}
          </span>
        )}
      </div>

      {/* Subcategories */}
      {hasSubcategories && isExpanded && (
        <CategoryTree
          categories={category.subcategories}
          expandedCategories={expandedCategories}
          selectedCategoryPath={selectedCategoryPath}
          onCategorySelect={onCategorySelect}
          onCategoryToggle={onCategoryToggle}
          depth={1}
        />
      )}
    </div>
  );
}
