/**
 * Source Citation - Clickable source reference
 */

import { FileText, ExternalLink } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { useKnowledgeLibraryStore } from '@/store/knowledge-library-store';
import { cn } from '@/lib/utils';
import type { KLAskSourceInfo } from '@automaker/types';

interface SourceCitationProps {
  source: KLAskSourceInfo;
  showSimilarity?: boolean;
}

export function SourceCitation({ source, showSimilarity = true }: SourceCitationProps) {
  const { setSelectedFilePath, setActiveView } = useKnowledgeLibraryStore();

  // Extract filename from path
  const fileName = source.file_path.split('/').pop() || source.file_path;

  const handleClick = () => {
    // Navigate to the file in Library Browser
    setSelectedFilePath(source.file_path);
    setActiveView('library');
  };

  return (
    <button
      onClick={handleClick}
      className={cn(
        'w-full text-left flex items-start gap-3 p-3 rounded-lg',
        'bg-muted/50 hover:bg-muted transition-colors',
        'border border-transparent hover:border-border'
      )}
    >
      {/* File icon */}
      <div className="p-1.5 bg-background rounded shrink-0">
        <FileText className="h-4 w-4 text-muted-foreground" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium truncate">{fileName}</span>
          {source.similarity !== undefined && source.similarity !== null && showSimilarity && (
            <Badge variant="secondary" className="text-xs shrink-0">
              {Math.round(source.similarity * 100)}%
            </Badge>
          )}
        </div>
        {source.section && (
          <p className="text-xs text-muted-foreground mt-0.5 truncate">Section: {source.section}</p>
        )}
        <p className="text-xs text-muted-foreground mt-0.5 font-mono truncate opacity-60">
          {source.file_path}
        </p>
      </div>

      {/* Link icon */}
      <ExternalLink className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
    </button>
  );
}
