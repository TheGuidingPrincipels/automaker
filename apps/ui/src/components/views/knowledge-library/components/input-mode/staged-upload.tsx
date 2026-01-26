/**
 * Staged Upload
 *
 * Shows the selected file ready for upload.
 * Allows clearing the selection or starting the session.
 */

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { FileText, X, Upload, Loader2 } from 'lucide-react';

interface StagedUploadProps {
  fileName: string;
  onClear: () => void;
  onStart: () => void;
  isLoading?: boolean;
}

export function StagedUpload({ fileName, onClear, onStart, isLoading = false }: StagedUploadProps) {
  return (
    <Card className="max-w-md w-full">
      <CardContent className="pt-6">
        <div className="text-center">
          {/* File icon */}
          <div className="mx-auto mb-4 p-4 bg-primary/10 rounded-full w-fit">
            <FileText className="h-12 w-12 text-primary" />
          </div>

          {/* File name */}
          <div className="flex items-center justify-center gap-2 mb-4">
            <span className="font-medium truncate max-w-[200px]" title={fileName}>
              {fileName}
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClear}
              className="h-6 w-6 p-0 text-muted-foreground hover:text-destructive"
              disabled={isLoading}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          {/* Description */}
          <p className="text-sm text-muted-foreground mb-6">
            Ready to extract and organize content from this document
          </p>

          {/* Start button */}
          <Button onClick={onStart} disabled={isLoading} className="w-full">
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Starting...
              </>
            ) : (
              <>
                <Upload className="h-4 w-4 mr-2" />
                Start Session
              </>
            )}
          </Button>

          <p className="text-xs text-muted-foreground mt-4">
            This will upload the file and begin content analysis
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
