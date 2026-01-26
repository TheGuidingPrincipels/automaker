/**
 * Library Browser - Browse and search the knowledge library
 *
 * Three-column layout:
 * - Left: Category tree (collapsible folders)
 * - Center: File list for selected category
 * - Right: File content viewer (markdown)
 *
 * Search bar at top with keyword/semantic toggle.
 */

import { useState, useMemo, useEffect } from 'react';
import {
  useKLLibrary,
  useKLFileContent,
  useKLFileMetadata,
  useKLSemanticSearch,
} from '@/hooks/queries/use-knowledge-library';
import { useKnowledgeLibraryStore } from '@/store/knowledge-library-store';
import { Spinner } from '@/components/ui/spinner';
import { CategoryTree } from './category-tree';
import { FileList } from './file-list';
import { FileViewer } from './file-viewer';
import { SearchBar } from './search-bar';
import { FolderOpen, AlertCircle } from 'lucide-react';
import type {
  KLLibraryCategoryResponse,
  KLLibraryFileResponse,
  KLSemanticSearchResult,
} from '@automaker/types';

export function LibraryBrowser() {
  const { data: library, isLoading, isError, error } = useKLLibrary();
  const { selectedFilePath, setSelectedFilePath } = useKnowledgeLibraryStore();

  // Track expanded categories
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  // Track selected category for file list
  const [selectedCategoryPath, setSelectedCategoryPath] = useState<string | null>(null);
  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchMode, setSearchMode] = useState<'keyword' | 'semantic'>('keyword');
  const [semanticResults, setSemanticResults] = useState<KLSemanticSearchResult[]>([]);
  const [semanticError, setSemanticError] = useState<string | null>(null);

  // Get file content when a file is selected
  const fileContentQuery = useKLFileContent(selectedFilePath ?? undefined);
  const fileMetadataQuery = useKLFileMetadata(selectedFilePath ?? undefined);
  const semanticSearchMutation = useKLSemanticSearch();

  // Flatten files for search/display
  const allFiles = useMemo(() => {
    if (!library) return [];
    const files: KLLibraryFileResponse[] = [];
    const collectFiles = (categories: KLLibraryCategoryResponse[]) => {
      for (const cat of categories) {
        // Use loop to push files one by one (safer than spread for large arrays)
        // or just use push(...cat.files) if we assume < 100k files per category
        // but `for ... of` is safer across browsers/engines limits
        for (const file of cat.files) {
          files.push(file);
        }
        if (cat.subcategories) {
          collectFiles(cat.subcategories);
        }
      }
    };
    collectFiles(library.categories);
    return files;
  }, [library]);

  // Get files for selected category
  const categoryFiles = useMemo(() => {
    if (!library || !selectedCategoryPath) return [];
    const findCategory = (
      categories: KLLibraryCategoryResponse[],
      path: string
    ): KLLibraryCategoryResponse | null => {
      for (const cat of categories) {
        if (cat.path === path) return cat;
        if (cat.subcategories) {
          const found = findCategory(cat.subcategories, path);
          if (found) return found;
        }
      }
      return null;
    };
    const category = findCategory(library.categories, selectedCategoryPath);
    return category?.files ?? [];
  }, [library, selectedCategoryPath]);

  useEffect(() => {
    if (searchMode !== 'semantic') {
      setSemanticResults([]);
      setSemanticError(null);
      return;
    }

    const query = searchQuery.trim();
    if (!query) {
      setSemanticResults([]);
      setSemanticError(null);
      return;
    }

    let isActive = true;

    const runSearch = async () => {
      setSemanticError(null);
      try {
        const response = await semanticSearchMutation.mutateAsync({
          query,
          n_results: 20,
        });
        if (isActive) {
          setSemanticResults(response.results);
        }
      } catch (error) {
        if (isActive) {
          setSemanticResults([]);
          setSemanticError(error instanceof Error ? error.message : 'Semantic search failed');
        }
      }
    };

    runSearch();

    return () => {
      isActive = false;
    };
  }, [searchMode, searchQuery, semanticSearchMutation]);

  const fileByPath = useMemo(() => {
    const map = new Map<string, KLLibraryFileResponse>();
    for (const file of allFiles) {
      map.set(file.path, file);
    }
    return map;
  }, [allFiles]);

  const semanticMatches = useMemo(() => {
    const map = new Map<string, { filePath: string; similarity: number }>();
    for (const result of semanticResults) {
      const existing = map.get(result.file_path);
      if (!existing || result.similarity > existing.similarity) {
        map.set(result.file_path, { filePath: result.file_path, similarity: result.similarity });
      }
    }
    return Array.from(map.values()).sort((a, b) => b.similarity - a.similarity);
  }, [semanticResults]);

  const semanticFiles = useMemo(() => {
    return semanticMatches.map((match) => {
      const file = fileByPath.get(match.filePath);
      if (file) return file;
      console.warn(`Missing library metadata for ${match.filePath}`);
      return {
        path: match.filePath,
        category: 'Unknown',
        title: match.filePath.split('/').pop() ?? match.filePath,
        sections: [],
        last_modified: '',
        block_count: 0,
        overview: null,
        is_valid: true,
        validation_errors: [],
      } satisfies KLLibraryFileResponse;
    });
  }, [fileByPath, semanticMatches]);

  const semanticSimilarityByPath = useMemo(() => {
    if (searchMode !== 'semantic') return undefined;
    const entries: Record<string, number> = {};
    for (const match of semanticMatches) {
      entries[match.filePath] = match.similarity;
    }
    return entries;
  }, [searchMode, semanticMatches]);

  // Filter files by search query
  const displayedFiles = useMemo(() => {
    if (searchMode === 'semantic') {
      if (!searchQuery.trim()) {
        return selectedCategoryPath ? categoryFiles : allFiles;
      }
      return semanticFiles;
    }
    const filesToFilter = selectedCategoryPath ? categoryFiles : allFiles;
    if (!searchQuery.trim()) return filesToFilter;

    const query = searchQuery.toLowerCase();
    return filesToFilter.filter(
      (f) =>
        f.title.toLowerCase().includes(query) ||
        f.path.toLowerCase().includes(query) ||
        f.sections.some((s) => s.toLowerCase().includes(query))
    );
  }, [searchMode, searchQuery, selectedCategoryPath, categoryFiles, allFiles, semanticFiles]);

  // Handle category selection
  const handleCategorySelect = (categoryPath: string) => {
    setSelectedCategoryPath(categoryPath);
    // Auto-expand the category
    setExpandedCategories((prev) => new Set([...prev, categoryPath]));
  };

  // Toggle category expansion
  const handleCategoryToggle = (categoryPath: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(categoryPath)) {
        next.delete(categoryPath);
      } else {
        next.add(categoryPath);
      }
      return next;
    });
  };

  // Handle file selection
  const handleFileSelect = (filePath: string) => {
    setSelectedFilePath(filePath);
  };

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <Spinner size="lg" className="mx-auto mb-4" />
          <p className="text-muted-foreground">Loading library...</p>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
          <h3 className="text-lg font-medium mb-2">Failed to load library</h3>
          <p className="text-sm text-muted-foreground">
            {error instanceof Error ? error.message : 'Unable to connect to Knowledge Library API'}
          </p>
        </div>
      </div>
    );
  }

  if (!library || library.categories.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <FolderOpen className="h-12 w-12 text-muted-foreground/50 mx-auto mb-4" />
          <h3 className="text-lg font-medium mb-2">Library is empty</h3>
          <p className="text-sm text-muted-foreground">
            Upload documents in Input Mode to populate your knowledge library.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Search bar */}
      <div className="p-4 border-b">
        <SearchBar
          query={searchQuery}
          onQueryChange={setSearchQuery}
          mode={searchMode}
          onModeChange={setSearchMode}
        />
      </div>

      {/* Three-column layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Category tree */}
        <div className="w-64 border-r overflow-y-auto p-4">
          <h3 className="text-sm font-medium text-muted-foreground mb-3">Categories</h3>
          <CategoryTree
            categories={library.categories}
            expandedCategories={expandedCategories}
            selectedCategoryPath={selectedCategoryPath}
            onCategorySelect={handleCategorySelect}
            onCategoryToggle={handleCategoryToggle}
          />
        </div>

        {/* Center: File list */}
        <div className="w-80 border-r overflow-y-auto">
          <FileList
            files={displayedFiles}
            selectedFilePath={selectedFilePath}
            onFileSelect={handleFileSelect}
            categoryName={selectedCategoryPath?.split('/').pop() ?? 'All Files'}
            mode={searchMode}
            query={searchQuery}
            similarityByPath={semanticSimilarityByPath}
            isSearching={searchMode === 'semantic' ? semanticSearchMutation.isPending : false}
            searchError={semanticError}
          />
        </div>

        {/* Right: File viewer */}
        <div className="flex-1 overflow-hidden">
          <FileViewer
            filePath={selectedFilePath}
            content={fileContentQuery.data?.content ?? null}
            isLoading={fileContentQuery.isLoading}
            error={fileContentQuery.error}
            metadata={fileMetadataQuery.data ?? null}
          />
        </div>
      </div>
    </div>
  );
}
