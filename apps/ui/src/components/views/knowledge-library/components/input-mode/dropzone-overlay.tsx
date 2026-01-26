/**
 * Dropzone Overlay
 *
 * Full-page drag & drop support for file uploads.
 * Shows a visual overlay when dragging files over the page.
 */

import { useState, useCallback, type ReactNode, type DragEvent } from 'react';
import { Upload, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';

interface DropzoneOverlayProps {
  children: ReactNode;
  onFileDrop: (file: File) => void;
  disabled?: boolean;
  acceptedTypes?: string[];
}

export function DropzoneOverlay({
  children,
  onFileDrop,
  disabled = false,
  acceptedTypes = ['.md', '.markdown', 'text/markdown', 'text/plain'],
}: DropzoneOverlayProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [dragError, setDragError] = useState<string | null>(null);

  const handleDragEnter = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (disabled) return;
      setIsDragging(true);
      setDragError(null);
    },
    [disabled]
  );

  const handleDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // Only hide if we're leaving the container (not entering a child)
    if (e.currentTarget === e.target) {
      setIsDragging(false);
      setDragError(null);
    }
  }, []);

  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      if (disabled) {
        setDragError('Cannot upload while a session is active');
        setTimeout(() => setDragError(null), 3000);
        return;
      }

      const files = Array.from(e.dataTransfer.files);

      if (files.length === 0) {
        setDragError('No files detected');
        setTimeout(() => setDragError(null), 3000);
        return;
      }

      if (files.length > 1) {
        setDragError('Only one file can be uploaded at a time');
        setTimeout(() => setDragError(null), 3000);
        return;
      }

      const file = files[0];

      // Validate file type
      const isValidType =
        acceptedTypes.some((type) => {
          if (type.startsWith('.')) {
            return file.name.toLowerCase().endsWith(type);
          }
          return file.type === type;
        }) || file.name.endsWith('.md');

      if (!isValidType) {
        setDragError('Only Markdown files (.md) are supported');
        setTimeout(() => setDragError(null), 3000);
        return;
      }

      onFileDrop(file);
    },
    [disabled, acceptedTypes, onFileDrop]
  );

  return (
    <div
      className="relative h-full"
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {children}

      {/* Overlay */}
      {isDragging && (
        <div
          className={cn(
            'absolute inset-0 z-50 flex items-center justify-center',
            'bg-background/80 backdrop-blur-sm',
            'border-2 border-dashed rounded-lg',
            disabled ? 'border-destructive' : 'border-primary'
          )}
        >
          <div className="text-center">
            <div
              className={cn(
                'mx-auto mb-4 p-4 rounded-full',
                disabled ? 'bg-destructive/10' : 'bg-primary/10'
              )}
            >
              {disabled ? (
                <FileText className="h-12 w-12 text-destructive" />
              ) : (
                <Upload className="h-12 w-12 text-primary animate-bounce" />
              )}
            </div>
            <p className={cn('text-lg font-medium', disabled && 'text-destructive')}>
              {disabled ? 'Session in progress' : 'Drop your file here'}
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              {disabled
                ? 'Cancel the current session to upload a new file'
                : 'Only Markdown files (.md) are supported'}
            </p>
          </div>
        </div>
      )}

      {/* Error toast */}
      {dragError && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-50">
          <div className="bg-destructive text-destructive-foreground px-4 py-2 rounded-md shadow-lg">
            {dragError}
          </div>
        </div>
      )}
    </div>
  );
}
