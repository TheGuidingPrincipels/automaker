/**
 * File List - Display files in the selected category
 */

import { FileText, AlertTriangle, ChevronRight } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { KLLibraryFileResponse } from '@automaker/types';

interface FileListProps {
  files: KLLibraryFileResponse[];
  selectedFilePath: string | null;
  onFileSelect: (path: string) => void;
  categoryName: string;
  mode: 'keyword' | 'semantic';
  query: string;
  similarityByPath?: Record<string, number>;
  isSearching?: boolean;
  searchError?: string | null;
}

export function FileList({
  files,
  selectedFilePath,
  onFileSelect,
  categoryName,
  mode,
  query,
  similarityByPath,
  isSearching,
  searchError,
}: FileListProps) {
  if (files.length === 0) {
    if (mode === 'semantic' && query.trim()) {
      return (
        <div className="h-full flex items-center justify-center p-4">
          <div className="text-center text-muted-foreground">
            <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No semantic matches found</p>
          </div>
        </div>
      );
    }
    return (
      <div className="h-full flex items-center justify-center p-4">
        <div className="text-center text-muted-foreground">
          <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No files in this category</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b bg-muted/30">
        <h3 className="text-sm font-medium">{categoryName}</h3>
        <p className="text-xs text-muted-foreground">{files.length} files</p>
        {mode === 'semantic' && query.trim() && (
          <p className="text-xs text-muted-foreground mt-1">Semantic results for "{query}"</p>
        )}
        {searchError && <p className="text-xs text-destructive mt-1">{searchError}</p>}
        {isSearching && <p className="text-xs text-muted-foreground mt-1">Searching...</p>}
      </div>

      {/* File list */}
      <ScrollArea className="flex-1">
        <div className="p-2">
          {files.map((file) => (
            <FileItem
              key={file.path}
              file={file}
              isSelected={selectedFilePath === file.path}
              onSelect={() => onFileSelect(file.path)}
              similarity={similarityByPath?.[file.path]}
            />
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}

interface FileItemProps {
  file: KLLibraryFileResponse;
  isSelected: boolean;
  onSelect: () => void;
  similarity?: number;
}

function FileItem({ file, isSelected, onSelect, similarity }: FileItemProps) {
  const hasValidationErrors = file.validation_errors && file.validation_errors.length > 0;
  const validationPreview = file.validation_errors?.slice(0, 2) ?? [];

  return (
    <div
      className={cn(
        'flex items-start gap-3 p-3 rounded-lg cursor-pointer',
        'hover:bg-muted transition-colors',
        isSelected && 'bg-primary/10 border border-primary/20'
      )}
      onClick={onSelect}
    >
      {/* File icon */}
      <div className={cn('mt-0.5 p-1.5 rounded', isSelected ? 'bg-primary/10' : 'bg-muted')}>
        <FileText
          className={cn('h-4 w-4', isSelected ? 'text-primary' : 'text-muted-foreground')}
        />
      </div>

      {/* File info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium truncate">{file.title}</span>
          {!file.is_valid && <AlertTriangle className="h-3.5 w-3.5 text-amber-500 shrink-0" />}
          {typeof similarity === 'number' && (
            <Badge variant="secondary" className="text-[10px]">
              {Math.round(similarity * 100)}% match
            </Badge>
          )}
        </div>

        {/* Overview or path */}
        <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
          {file.overview ?? file.path}
        </p>

        {/* Metadata */}
        <div className="flex items-center gap-2 mt-2">
          {file.block_count > 0 && (
            <Badge variant="secondary" className="text-xs h-5">
              {file.block_count} blocks
            </Badge>
          )}
          {file.sections.length > 0 && (
            <Badge variant="outline" className="text-xs h-5">
              {file.sections.length} sections
            </Badge>
          )}
          {hasValidationErrors && (
            <Badge variant="destructive" className="text-xs h-5">
              Invalid
            </Badge>
          )}
        </div>

        {hasValidationErrors && validationPreview.length > 0 && (
          <ul className="mt-2 space-y-1 text-xs text-amber-600">
            {validationPreview.map((error) => (
              <li key={error}>{error}</li>
            ))}
          </ul>
        )}
      </div>

      {/* Chevron */}
      <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0 mt-1" />
    </div>
  );
}
