/**
 * File Viewer - Display file content as rendered markdown
 */

import { useEffect, useRef, type ReactNode } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Spinner } from '@/components/ui/spinner';
import { FileText, AlertCircle, Eye, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { KLLibraryFileResponse } from '@automaker/types';

interface FileViewerProps {
  filePath: string | null;
  content: string | null;
  isLoading: boolean;
  error: Error | null;
  metadata: KLLibraryFileResponse | null;
}

export function FileViewer({ filePath, content, isLoading, error, metadata }: FileViewerProps) {
  const contentRef = useRef<HTMLDivElement>(null);

  // Scroll to top when file changes
  useEffect(() => {
    if (contentRef.current) {
      contentRef.current.scrollTop = 0;
    }
  }, [filePath]);

  // Empty state - no file selected
  if (!filePath) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center text-muted-foreground">
          <Eye className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <h3 className="text-lg font-medium mb-2">Select a file</h3>
          <p className="text-sm">Choose a file from the list to view its content</p>
        </div>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <Spinner size="lg" className="mx-auto mb-4" />
          <p className="text-muted-foreground">Loading file content...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
          <h3 className="text-lg font-medium mb-2">Failed to load file</h3>
          <p className="text-sm text-muted-foreground">
            {error.message || 'Unable to load file content'}
          </p>
        </div>
      </div>
    );
  }

  // No content (shouldn't happen normally)
  if (!content) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center text-muted-foreground">
          <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p className="text-sm">File is empty</p>
        </div>
      </div>
    );
  }

  // Extract filename from path
  const fileName = filePath.split('/').pop() || filePath;
  const validationErrors = metadata?.validation_errors ?? [];

  return (
    <div className="h-full flex flex-col">
      {/* File header */}
      <div className="px-6 py-4 border-b bg-muted/30">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-muted-foreground" />
          <h2 className="font-medium">{fileName}</h2>
        </div>
        <p className="text-xs text-muted-foreground mt-1 font-mono">{filePath}</p>
      </div>

      {validationErrors.length > 0 && (
        <div className="mx-6 mt-4 rounded-md border border-amber-300/60 bg-amber-50/80 px-4 py-3 text-amber-700">
          <div className="flex items-center gap-2 text-sm font-medium">
            <AlertTriangle className="h-4 w-4" />
            Validation issues
          </div>
          <ul className="mt-2 space-y-1 text-xs">
            {validationErrors.map((errorItem) => (
              <li key={errorItem}>{errorItem}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Markdown content */}
      <ScrollArea className="flex-1" ref={contentRef}>
        <div className="p-6">
          <article
            className={cn('prose prose-sm dark:prose-invert max-w-none', 'markdown-content')}
          >
            <MarkdownRenderer content={content} />
          </article>
        </div>
      </ScrollArea>
    </div>
  );
}

/**
 * Simple markdown renderer
 * Uses basic regex transforms - for production, consider using react-markdown
 */
function MarkdownRenderer({ content }: { content: string }) {
  // Split into lines for processing
  const lines = content.split('\n');
  const elements: ReactNode[] = [];
  let currentBlock: string[] = [];
  let inCodeBlock = false;
  let codeLanguage = '';

  const flushParagraph = () => {
    if (currentBlock.length > 0) {
      const text = currentBlock.join('\n');
      if (text.trim()) {
        elements.push(
          <p key={elements.length} className="mb-4">
            {renderInlineMarkdown(text)}
          </p>
        );
      }
      currentBlock = [];
    }
  };

  const flushCodeBlock = () => {
    if (currentBlock.length > 0) {
      const code = currentBlock.join('\n');
      elements.push(
        <pre key={elements.length} className="mb-4 p-4 bg-muted rounded-lg overflow-x-auto">
          <code className={codeLanguage ? `language-${codeLanguage}` : ''}>{code}</code>
        </pre>
      );
      currentBlock = [];
      codeLanguage = '';
    }
  };

  const renderHeader = (level: number, text: string, key: number) => {
    const classes: Record<number, string> = {
      1: 'text-2xl font-bold mb-4 mt-6',
      2: 'text-xl font-semibold mb-3 mt-5',
      3: 'text-lg font-medium mb-2 mt-4',
      4: 'text-base font-medium mb-2 mt-3',
      5: 'text-sm font-medium mb-1 mt-2',
      6: 'text-sm font-medium mb-1 mt-2',
    };
    const className = classes[level] || classes[3];
    const content = renderInlineMarkdown(text);

    switch (level) {
      case 1:
        return (
          <h1 key={key} className={className}>
            {content}
          </h1>
        );
      case 2:
        return (
          <h2 key={key} className={className}>
            {content}
          </h2>
        );
      case 3:
        return (
          <h3 key={key} className={className}>
            {content}
          </h3>
        );
      case 4:
        return (
          <h4 key={key} className={className}>
            {content}
          </h4>
        );
      case 5:
        return (
          <h5 key={key} className={className}>
            {content}
          </h5>
        );
      default:
        return (
          <h6 key={key} className={className}>
            {content}
          </h6>
        );
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Code block toggle
    if (line.startsWith('```')) {
      if (inCodeBlock) {
        flushCodeBlock();
        inCodeBlock = false;
      } else {
        flushParagraph();
        inCodeBlock = true;
        codeLanguage = line.slice(3).trim();
      }
      continue;
    }

    // Inside code block
    if (inCodeBlock) {
      currentBlock.push(line);
      continue;
    }

    // Headers
    const headerMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (headerMatch) {
      flushParagraph();
      const level = headerMatch[1].length;
      const text = headerMatch[2];
      elements.push(renderHeader(level, text, elements.length));
      continue;
    }

    // Horizontal rule
    if (line.match(/^(-{3,}|\*{3,}|_{3,})$/)) {
      flushParagraph();
      elements.push(<hr key={elements.length} className="my-4 border-border" />);
      continue;
    }

    // Unordered list item
    if (line.match(/^[\s]*[-*+]\s+/)) {
      flushParagraph();
      const text = line.replace(/^[\s]*[-*+]\s+/, '');
      elements.push(
        <li key={elements.length} className="ml-4 mb-1 list-disc">
          {renderInlineMarkdown(text)}
        </li>
      );
      continue;
    }

    // Ordered list item
    const orderedMatch = line.match(/^[\s]*(\d+)\.\s+(.+)$/);
    if (orderedMatch) {
      flushParagraph();
      elements.push(
        <li key={elements.length} className="ml-4 mb-1 list-decimal">
          {renderInlineMarkdown(orderedMatch[2])}
        </li>
      );
      continue;
    }

    // Blockquote
    if (line.startsWith('>')) {
      flushParagraph();
      const text = line.replace(/^>\s*/, '');
      elements.push(
        <blockquote
          key={elements.length}
          className="border-l-4 border-muted-foreground/30 pl-4 italic text-muted-foreground mb-4"
        >
          {renderInlineMarkdown(text)}
        </blockquote>
      );
      continue;
    }

    // Empty line
    if (line.trim() === '') {
      flushParagraph();
      continue;
    }

    // Regular paragraph line
    currentBlock.push(line);
  }

  // Flush remaining content
  if (inCodeBlock) {
    flushCodeBlock();
  } else {
    flushParagraph();
  }

  return <>{elements}</>;
}

/**
 * Render inline markdown (bold, italic, code, links)
 */
function renderInlineMarkdown(text: string): ReactNode {
  // Process inline formatting
  const parts: ReactNode[] = [];
  let lastIndex = 0;

  // Combined pattern for inline elements
  const pattern = /(\*\*(.+?)\*\*|\*(.+?)\*|`([^`]+)`|\[([^\]]+)\]\(([^)]+)\))/g;
  let match;

  while ((match = pattern.exec(text)) !== null) {
    // Add text before match
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    const fullMatch = match[0];

    if (fullMatch.startsWith('**')) {
      // Bold
      parts.push(<strong key={match.index}>{match[2]}</strong>);
    } else if (fullMatch.startsWith('*')) {
      // Italic
      parts.push(<em key={match.index}>{match[3]}</em>);
    } else if (fullMatch.startsWith('`')) {
      // Inline code
      parts.push(
        <code key={match.index} className="bg-muted px-1 py-0.5 rounded text-sm">
          {match[4]}
        </code>
      );
    } else if (fullMatch.startsWith('[')) {
      // Link
      parts.push(
        <a
          key={match.index}
          href={match[6]}
          className="text-primary hover:underline"
          target="_blank"
          rel="noopener noreferrer"
        >
          {match[5]}
        </a>
      );
    }

    lastIndex = match.index + fullMatch.length;
  }

  // Add remaining text
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length > 0 ? parts : text;
}
