/**
 * Empty State
 *
 * Shown when no file is staged and no session is active.
 * Provides instructions and a file picker.
 */

import { useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Upload, FileText, ArrowRight } from 'lucide-react';
import { useKnowledgeLibraryStore } from '@/store/knowledge-library-store';

export function EmptyState() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const stageUpload = useKnowledgeLibraryStore((s) => s.stageUpload);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      stageUpload(file);
    }
    // Reset input so the same file can be selected again
    e.target.value = '';
  };

  return (
    <div className="h-full flex items-center justify-center p-4">
      <Card className="max-w-lg w-full">
        <CardContent className="pt-6">
          <div className="text-center">
            {/* Icon */}
            <div className="mx-auto mb-4 p-4 bg-muted rounded-full w-fit">
              <Upload className="h-12 w-12 text-muted-foreground" />
            </div>

            {/* Title */}
            <h2 className="text-xl font-semibold mb-2">Extract Knowledge</h2>

            {/* Description */}
            <p className="text-muted-foreground mb-6">
              Upload a Markdown document to extract and organize its content into your knowledge
              library.
            </p>

            {/* Upload button */}
            <input
              ref={fileInputRef}
              type="file"
              accept=".md,.markdown,text/markdown"
              className="hidden"
              onChange={handleFileSelect}
            />
            <Button size="lg" onClick={() => fileInputRef.current?.click()}>
              <FileText className="h-4 w-4 mr-2" />
              Select File
            </Button>

            <p className="text-xs text-muted-foreground mt-4">
              or drag and drop a file anywhere on this page
            </p>

            {/* Workflow steps */}
            <div className="mt-6 pt-4 border-t">
              <h3 className="text-sm font-medium mb-4">How it works</h3>
              <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                <span className="flex items-center gap-1">
                  <span className="bg-primary/10 text-primary px-2 py-0.5 rounded-full text-xs font-medium">
                    1
                  </span>
                  Upload
                </span>
                <ArrowRight className="h-4 w-4" />
                <span className="flex items-center gap-1">
                  <span className="bg-primary/10 text-primary px-2 py-0.5 rounded-full text-xs font-medium">
                    2
                  </span>
                  Review Cleanup
                </span>
                <ArrowRight className="h-4 w-4" />
                <span className="flex items-center gap-1">
                  <span className="bg-primary/10 text-primary px-2 py-0.5 rounded-full text-xs font-medium">
                    3
                  </span>
                  Route Blocks
                </span>
                <ArrowRight className="h-4 w-4" />
                <span className="flex items-center gap-1">
                  <span className="bg-primary/10 text-primary px-2 py-0.5 rounded-full text-xs font-medium">
                    4
                  </span>
                  Execute
                </span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
