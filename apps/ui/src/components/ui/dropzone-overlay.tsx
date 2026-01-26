/**
 * Dropzone Overlay
 *
 * A full-page drag & drop overlay component that provides visual feedback
 * when dragging files over the page. Supports configurable file types,
 * single or multiple file uploads, and custom messaging.
 *
 * Usage:
 * ```tsx
 * <DropzoneOverlay
 *   onFileDrop={(files) => handleFiles(files)}
 *   acceptedTypes={['.pdf', '.doc', 'application/pdf']}
 *   maxFiles={5}
 *   disabled={isProcessing}
 * >
 *   <YourPageContent />
 * </DropzoneOverlay>
 * ```
 */

import { useState, useCallback, useRef, type ReactNode, type DragEvent } from 'react';
import { Upload, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatFileSize } from '@/lib/image-utils';

export interface DropzoneOverlayProps {
  /** Content to wrap with the dropzone */
  children: ReactNode;
  /** Callback when files are dropped */
  onFileDrop: (files: File[]) => void;
  /** Whether the dropzone is disabled */
  disabled?: boolean;
  /** Message to show when disabled */
  disabledMessage?: string;
  /** Accepted file types (extensions like '.md' or MIME types like 'text/plain') */
  acceptedTypes?: string[];
  /** Maximum number of files allowed (default: 1) */
  maxFiles?: number;
  /** Maximum file size in bytes (default: 10MB) */
  maxFileSize?: number;
  /** Custom title for the drop overlay */
  dropTitle?: string;
  /** Custom subtitle/hint for the drop overlay */
  dropSubtitle?: string;
  /** Additional class name for the container */
  className?: string;
  /** Icon to show in the overlay (default: Upload) */
  icon?: ReactNode;
  /** Callback when a drag error occurs */
  onError?: (error: string) => void;
}

const DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

export function DropzoneOverlay({
  children,
  onFileDrop,
  disabled = false,
  disabledMessage = 'File upload is currently disabled',
  acceptedTypes,
  maxFiles = 1,
  maxFileSize = DEFAULT_MAX_FILE_SIZE,
  dropTitle,
  dropSubtitle,
  className,
  icon,
  onError,
}: DropzoneOverlayProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [dragError, setDragError] = useState<string | null>(null);
  const dragCounter = useRef(0);

  const showError = useCallback(
    (message: string) => {
      setDragError(message);
      onError?.(message);
      // Auto-clear error after 3 seconds
      setTimeout(() => setDragError(null), 3000);
    },
    [onError]
  );

  const validateFiles = useCallback(
    (files: File[]): { valid: File[]; errors: string[] } => {
      const valid: File[] = [];
      const errors: string[] = [];

      for (const file of files) {
        // Check file count limit
        if (valid.length >= maxFiles) {
          errors.push(`Maximum ${maxFiles} file${maxFiles > 1 ? 's' : ''} allowed`);
          break;
        }

        // Check file size
        if (file.size > maxFileSize) {
          errors.push(`${file.name}: File too large (max ${formatFileSize(maxFileSize)})`);
          continue;
        }

        // Check file type if acceptedTypes is provided
        if (acceptedTypes && acceptedTypes.length > 0) {
          const isValidType = acceptedTypes.some((type) => {
            if (type.startsWith('.')) {
              // Extension-based check
              return file.name.toLowerCase().endsWith(type.toLowerCase());
            }
            // MIME type check
            return file.type === type || file.type.startsWith(type.replace('/*', '/'));
          });

          if (!isValidType) {
            const extensions = acceptedTypes.filter((t) => t.startsWith('.')).join(', ');
            errors.push(
              `${file.name}: Unsupported file type${extensions ? ` (accepted: ${extensions})` : ''}`
            );
            continue;
          }
        }

        valid.push(file);
      }

      return { valid, errors };
    },
    [acceptedTypes, maxFiles, maxFileSize]
  );

  const handleDragEnter = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();

      dragCounter.current++;

      if (dragCounter.current === 1) {
        if (!disabled) {
          setIsDragging(true);
          setDragError(null);
        }
      }
    },
    [disabled]
  );

  const handleDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();

    dragCounter.current--;

    if (dragCounter.current === 0) {
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

      // Reset drag state
      dragCounter.current = 0;
      setIsDragging(false);

      if (disabled) {
        showError(disabledMessage);
        return;
      }

      const files = Array.from(e.dataTransfer.files);

      if (files.length === 0) {
        showError('No files detected');
        return;
      }

      // Validate files
      const { valid, errors } = validateFiles(files);

      // Show first error if any
      if (errors.length > 0) {
        showError(errors[0]);
      }

      // Call callback with valid files
      if (valid.length > 0) {
        onFileDrop(valid);
      }
    },
    [disabled, disabledMessage, validateFiles, showError, onFileDrop]
  );

  // Generate subtitle based on props if not provided
  const getSubtitle = (): string => {
    if (dropSubtitle) return dropSubtitle;

    const parts: string[] = [];

    if (acceptedTypes && acceptedTypes.length > 0) {
      const extensions = acceptedTypes.filter((t) => t.startsWith('.'));
      if (extensions.length > 0) {
        parts.push(`Accepted: ${extensions.join(', ')}`);
      }
    }

    if (maxFiles > 1) {
      parts.push(`Up to ${maxFiles} files`);
    }

    if (maxFileSize !== DEFAULT_MAX_FILE_SIZE) {
      parts.push(`Max ${formatFileSize(maxFileSize)} each`);
    }

    return parts.join(' • ') || 'Drop files to upload';
  };

  return (
    <div
      className={cn('relative h-full', className)}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {children}

      {/* Full-page overlay when dragging */}
      {isDragging && (
        <div
          className={cn(
            'absolute inset-0 z-50 flex items-center justify-center',
            'bg-background/80 backdrop-blur-sm',
            'border-2 border-dashed rounded-lg',
            'transition-all duration-200',
            disabled ? 'border-destructive' : 'border-primary'
          )}
        >
          <div className="text-center pointer-events-none">
            <div
              className={cn(
                'mx-auto mb-4 p-4 rounded-full',
                disabled ? 'bg-destructive/10' : 'bg-primary/10'
              )}
            >
              {disabled ? (
                <AlertCircle className="h-12 w-12 text-destructive" />
              ) : icon ? (
                icon
              ) : (
                <Upload className="h-12 w-12 text-primary animate-bounce" />
              )}
            </div>
            <p
              className={cn(
                'text-lg font-medium',
                disabled ? 'text-destructive' : 'text-foreground'
              )}
            >
              {disabled ? disabledMessage : dropTitle || 'Drop your files here'}
            </p>
            {!disabled && <p className="text-sm text-muted-foreground mt-1">{getSubtitle()}</p>}
          </div>
        </div>
      )}

      {/* Error toast notification */}
      {dragError && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-50 animate-in fade-in slide-in-from-bottom-2 duration-200">
          <div className="bg-destructive text-destructive-foreground px-4 py-2 rounded-md shadow-lg flex items-center gap-2">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            <span className="text-sm">{dragError}</span>
          </div>
        </div>
      )}
    </div>
  );
}
