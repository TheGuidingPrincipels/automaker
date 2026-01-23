# Session 6 (REVISED): Import & Preview UI

## Overview

**Goal**: Implement document import (text/MD/PDF) and preview components integrated with Automaker's UI patterns.

**Prerequisites**:

- Session 5 (REVISED) completed
- Python backend running on port 8001
- Route files created

> ⚠️ **Code Organization**: All backend logic stays in `4.Speed Reading System/backend/`. Frontend components go in Automaker. See `4.Speed Reading System/README.md` for details.

---

## Deliverables

| #   | Component        | Description                           |
| --- | ---------------- | ------------------------------------- |
| 1   | ImportForm       | Tabs for paste text / upload file     |
| 2   | TextInput        | Textarea with word count validation   |
| 3   | FileUpload       | Drag-drop for .md and .pdf            |
| 4   | LanguageSelect   | EN/DE radio buttons                   |
| 5   | PreviewText      | Virtualized text with clickable words |
| 6   | ProgressScrubber | Slider to jump to % position          |
| 7   | StartControls    | WPM settings + Start Reading button   |

---

## File Structure

```
components/views/speed-reading-import/
├── index.tsx
├── components/
│   ├── import-form.tsx
│   ├── text-input.tsx
│   ├── file-upload.tsx
│   └── language-select.tsx

components/views/speed-reading-preview/
├── index.tsx
├── components/
│   ├── preview-header.tsx
│   ├── preview-text.tsx
│   ├── preview-word.tsx
│   ├── progress-scrubber.tsx
│   └── start-controls.tsx

hooks/speed-reading/
├── use-documents.ts
└── use-import-document.ts
```

---

## Implementation

### 1. Import Page (`speed-reading-import/index.tsx`)

```typescript
import { useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/components/ui/use-toast';
import { ImportForm } from './components/import-form';
import { useImportDocument } from '@/hooks/speed-reading/use-import-document';
import type { Language } from '@/lib/speed-reading/types';

export function SpeedReadingImport() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const importDocument = useImportDocument();
  const [activeTab, setActiveTab] = useState<'paste' | 'upload'>('paste');

  const handleBack = () => {
    navigate({ to: '/speed-reading' });
  };

  const handleImportText = async (text: string, language: Language, title?: string) => {
    try {
      const document = await importDocument.mutateAsync({
        type: 'text',
        text,
        language,
        title,
      });

      toast({
        title: 'Document imported',
        description: `${document.total_words.toLocaleString()} words ready to read`,
      });

      navigate({
        to: '/speed-reading/preview/$documentId',
        params: { documentId: document.id },
      });
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Import failed',
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  const handleImportFile = async (file: File, language: Language) => {
    try {
      const document = await importDocument.mutateAsync({
        type: 'file',
        file,
        language,
      });

      toast({
        title: 'Document imported',
        description: `${document.total_words.toLocaleString()} words ready to read`,
      });

      navigate({
        to: '/speed-reading/preview/$documentId',
        params: { documentId: document.id },
      });
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Import failed',
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b bg-background/95 backdrop-blur px-6 py-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={handleBack}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-xl font-semibold">Import Document</h1>
            <p className="text-sm text-muted-foreground">
              Paste text or upload a Markdown/PDF file
            </p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-2xl mx-auto">
          <Card>
            <CardHeader>
              <CardTitle>Add Content</CardTitle>
              <CardDescription>
                Choose how you want to import your document for speed reading
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as typeof activeTab)}>
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="paste">Paste Text</TabsTrigger>
                  <TabsTrigger value="upload">Upload File</TabsTrigger>
                </TabsList>

                <TabsContent value="paste" className="mt-6">
                  <ImportForm
                    mode="paste"
                    onSubmit={handleImportText}
                    isLoading={importDocument.isPending}
                  />
                </TabsContent>

                <TabsContent value="upload" className="mt-6">
                  <ImportForm
                    mode="upload"
                    onSubmitFile={handleImportFile}
                    isLoading={importDocument.isPending}
                  />
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
```

### 2. Import Form Component

```typescript
// components/import-form.tsx
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { FileUpload } from './file-upload';
import type { Language } from '@/lib/speed-reading/types';

const MAX_WORDS = 20000;

interface ImportFormProps {
  mode: 'paste' | 'upload';
  onSubmit?: (text: string, language: Language, title?: string) => void;
  onSubmitFile?: (file: File, language: Language) => void;
  isLoading?: boolean;
}

export function ImportForm({ mode, onSubmit, onSubmitFile, isLoading }: ImportFormProps) {
  const [text, setText] = useState('');
  const [title, setTitle] = useState('');
  const [language, setLanguage] = useState<Language>('en');
  const [file, setFile] = useState<File | null>(null);

  const wordCount = text.trim().split(/\s+/).filter(Boolean).length;
  const isOverLimit = wordCount > MAX_WORDS;
  const canSubmitText = text.trim().length > 0 && !isOverLimit;
  const canSubmitFile = file !== null;

  const handleSubmitText = () => {
    if (canSubmitText && onSubmit) {
      onSubmit(text, language, title || undefined);
    }
  };

  const handleSubmitFile = () => {
    if (canSubmitFile && onSubmitFile && file) {
      onSubmitFile(file, language);
    }
  };

  return (
    <div className="space-y-6">
      {/* Language Selection */}
      <div className="space-y-3">
        <Label>Language</Label>
        <RadioGroup
          value={language}
          onValueChange={(v) => setLanguage(v as Language)}
          className="flex gap-4"
        >
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="en" id="lang-en" />
            <Label htmlFor="lang-en" className="font-normal cursor-pointer">
              English
            </Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="de" id="lang-de" />
            <Label htmlFor="lang-de" className="font-normal cursor-pointer">
              German
            </Label>
          </div>
        </RadioGroup>
      </div>

      {mode === 'paste' ? (
        <>
          {/* Title (optional) */}
          <div className="space-y-2">
            <Label htmlFor="title">Title (optional)</Label>
            <Input
              id="title"
              placeholder="My Document"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          {/* Text Input */}
          <div className="space-y-2">
            <div className="flex justify-between">
              <Label htmlFor="text">Text Content</Label>
              <span className={`text-sm ${isOverLimit ? 'text-destructive' : 'text-muted-foreground'}`}>
                {wordCount.toLocaleString()} / {MAX_WORDS.toLocaleString()} words
              </span>
            </div>
            <Textarea
              id="text"
              placeholder="Paste your text here..."
              className="min-h-[200px] font-mono text-sm"
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
            {isOverLimit && (
              <p className="text-sm text-destructive">
                Text exceeds the maximum limit of {MAX_WORDS.toLocaleString()} words
              </p>
            )}
          </div>

          <Button
            onClick={handleSubmitText}
            disabled={!canSubmitText || isLoading}
            className="w-full"
          >
            {isLoading ? 'Processing...' : 'Continue to Preview'}
          </Button>
        </>
      ) : (
        <>
          {/* File Upload */}
          <div className="space-y-2">
            <Label>Upload File</Label>
            <FileUpload
              onFileSelect={setFile}
              selectedFile={file}
              accept=".md,.pdf"
            />
          </div>

          <Button
            onClick={handleSubmitFile}
            disabled={!canSubmitFile || isLoading}
            className="w-full"
          >
            {isLoading ? 'Processing...' : 'Upload and Continue'}
          </Button>
        </>
      )}
    </div>
  );
}
```

### 3. File Upload Component

```typescript
// components/file-upload.tsx
import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, File, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface FileUploadProps {
  onFileSelect: (file: File | null) => void;
  selectedFile: File | null;
  accept?: string;
}

export function FileUpload({ onFileSelect, selectedFile, accept = '.md,.pdf' }: FileUploadProps) {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      onFileSelect(acceptedFiles[0]);
    }
  }, [onFileSelect]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/markdown': ['.md'],
      'application/pdf': ['.pdf'],
    },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024, // 10MB
  });

  const handleRemove = () => {
    onFileSelect(null);
  };

  if (selectedFile) {
    return (
      <div className="border rounded-lg p-4 bg-muted/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <File className="h-8 w-8 text-primary" />
            <div>
              <p className="font-medium">{selectedFile.name}</p>
              <p className="text-sm text-muted-foreground">
                {(selectedFile.size / 1024).toFixed(1)} KB
              </p>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={handleRemove}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div
      {...getRootProps()}
      className={cn(
        'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
        isDragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50'
      )}
    >
      <input {...getInputProps()} />
      <Upload className="h-10 w-10 mx-auto text-muted-foreground mb-4" />
      <p className="text-sm text-muted-foreground mb-1">
        {isDragActive ? 'Drop the file here...' : 'Drag and drop a file here, or click to select'}
      </p>
      <p className="text-xs text-muted-foreground">
        Supports .md and .pdf files up to 10MB
      </p>
    </div>
  );
}
```

### 4. Preview Page (`speed-reading-preview/index.tsx`)

```typescript
import { useState, useEffect } from 'react';
import { useNavigate, useParams } from '@tanstack/react-router';
import { ArrowLeft, Play, RotateCcw, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useDocument, useDocumentPreview } from '@/hooks/speed-reading/use-documents';
import { useLatestSessionForDocument, useCreateSession } from '@/hooks/speed-reading/use-sessions';
import { useSpeedReadingStore } from '@/store/speed-reading-store';
import { PreviewText } from './components/preview-text';
import { ProgressScrubber } from './components/progress-scrubber';
import { StartControls } from './components/start-controls';

export function SpeedReadingPreview() {
  const navigate = useNavigate();
  const { documentId } = useParams({ from: '/speed-reading/preview/$documentId' });

  const { data: document, isLoading: docLoading } = useDocument(documentId);
  const { data: preview, isLoading: previewLoading } = useDocumentPreview(documentId);
  const { data: existingSession } = useLatestSessionForDocument(documentId);
  const createSession = useCreateSession();

  const { settings } = useSpeedReadingStore();

  const [selectedWordIndex, setSelectedWordIndex] = useState<number | null>(null);
  const [scrubPosition, setScrubPosition] = useState(0);

  // If resuming, set initial position from existing session
  useEffect(() => {
    if (existingSession && selectedWordIndex === null) {
      setSelectedWordIndex(existingSession.current_word_index);
      setScrubPosition(existingSession.last_known_percent);
    }
  }, [existingSession, selectedWordIndex]);

  const handleBack = () => {
    navigate({ to: '/speed-reading' });
  };

  const handleWordClick = (wordIndex: number) => {
    setSelectedWordIndex(wordIndex);
    if (document) {
      setScrubPosition((wordIndex / document.total_words) * 100);
    }
  };

  const handleScrubChange = (percent: number) => {
    setScrubPosition(percent);
    if (document) {
      const approxIndex = Math.floor((percent / 100) * document.total_words);
      setSelectedWordIndex(approxIndex);
    }
  };

  const handleStartReading = async () => {
    try {
      const session = await createSession.mutateAsync({
        document_id: documentId,
        start_word_index: selectedWordIndex ?? 0,
        target_wpm: settings.targetWpm,
        ramp_enabled: settings.rampEnabled,
        ramp_seconds: settings.rampSeconds,
      });

      navigate({
        to: '/speed-reading/reader/$sessionId',
        params: { sessionId: session.id },
      });
    } catch (error) {
      console.error('Failed to create session:', error);
    }
  };

  const handleContinue = () => {
    if (existingSession) {
      navigate({
        to: '/speed-reading/reader/$sessionId',
        params: { sessionId: existingSession.id },
      });
    }
  };

  const isLoading = docLoading || previewLoading;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b bg-background/95 backdrop-blur px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={handleBack}>
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              {isLoading ? (
                <Skeleton className="h-6 w-48" />
              ) : (
                <>
                  <h1 className="text-xl font-semibold">{document?.title || 'Preview'}</h1>
                  <p className="text-sm text-muted-foreground">
                    {document?.total_words.toLocaleString()} words •{' '}
                    Click a word to set your starting position
                  </p>
                </>
              )}
            </div>
          </div>

          {/* Start Controls */}
          <div className="flex items-center gap-2">
            {existingSession && (
              <Button variant="outline" onClick={handleContinue}>
                <Play className="h-4 w-4 mr-2" />
                Continue ({existingSession.last_known_percent.toFixed(0)}%)
              </Button>
            )}
            <StartControls
              onStart={handleStartReading}
              isLoading={createSession.isPending}
            />
          </div>
        </div>
      </div>

      {/* Progress Scrubber */}
      <div className="px-6 py-3 border-b bg-muted/30">
        <ProgressScrubber
          value={scrubPosition}
          onChange={handleScrubChange}
          totalWords={document?.total_words ?? 0}
          selectedIndex={selectedWordIndex}
        />
      </div>

      {/* Preview Content */}
      <div className="flex-1 overflow-hidden">
        {isLoading ? (
          <div className="p-6 space-y-4">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-5/6" />
          </div>
        ) : preview ? (
          <PreviewText
            text={preview.preview_text}
            totalWords={document?.total_words ?? 0}
            selectedWordIndex={selectedWordIndex}
            onWordClick={handleWordClick}
          />
        ) : null}
      </div>
    </div>
  );
}
```

### 5. Preview Text with Virtualization

```typescript
// components/preview-text.tsx
import { useRef, useCallback } from 'react';
import { FixedSizeList as List } from 'react-window';
import { cn } from '@/lib/utils';

interface PreviewTextProps {
  text: string;
  totalWords: number;
  selectedWordIndex: number | null;
  onWordClick: (wordIndex: number) => void;
}

export function PreviewText({ text, totalWords, selectedWordIndex, onWordClick }: PreviewTextProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<List>(null);

  // Split into paragraphs
  const paragraphs = text.split(/\n\n+/).filter(Boolean);

  // Calculate word indices per paragraph
  let wordOffset = 0;
  const paragraphData = paragraphs.map((para) => {
    const words = para.split(/\s+/).filter(Boolean);
    const data = {
      text: para,
      words,
      startIndex: wordOffset,
    };
    wordOffset += words.length;
    return data;
  });

  const Row = useCallback(
    ({ index, style }: { index: number; style: React.CSSProperties }) => {
      const para = paragraphData[index];

      return (
        <div style={style} className="px-6 py-2">
          <p className="leading-relaxed">
            {para.words.map((word, i) => {
              const globalIndex = para.startIndex + i;
              const isSelected = globalIndex === selectedWordIndex;

              return (
                <span
                  key={globalIndex}
                  onClick={() => onWordClick(globalIndex)}
                  className={cn(
                    'cursor-pointer hover:bg-primary/20 px-0.5 rounded transition-colors',
                    isSelected && 'bg-primary text-primary-foreground'
                  )}
                >
                  {word}{' '}
                </span>
              );
            })}
          </p>
        </div>
      );
    },
    [paragraphData, selectedWordIndex, onWordClick]
  );

  return (
    <div ref={containerRef} className="h-full w-full">
      <List
        ref={listRef}
        height={600}
        width="100%"
        itemCount={paragraphData.length}
        itemSize={80}
        className="scrollbar-thin"
      >
        {Row}
      </List>
    </div>
  );
}
```

### 6. Query Hooks

```typescript
// hooks/speed-reading/use-documents.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { documentsApi } from '@/lib/speed-reading/api';
import type { Language } from '@/lib/speed-reading/types';

export const documentKeys = {
  all: ['deepread-documents'] as const,
  detail: (id: string) => ['deepread-documents', id] as const,
  preview: (id: string) => ['deepread-documents', id, 'preview'] as const,
  tokens: (id: string, start: number) => ['deepread-documents', id, 'tokens', start] as const,
};

export function useDocument(documentId: string) {
  return useQuery({
    queryKey: documentKeys.detail(documentId),
    queryFn: () => documentsApi.getDocument(documentId),
    enabled: !!documentId,
  });
}

export function useDocumentPreview(documentId: string) {
  return useQuery({
    queryKey: documentKeys.preview(documentId),
    queryFn: () => documentsApi.getPreview(documentId),
    enabled: !!documentId,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useDocumentTokens(documentId: string, start: number, limit = 500) {
  return useQuery({
    queryKey: documentKeys.tokens(documentId, start),
    queryFn: () => documentsApi.getTokens(documentId, start, limit),
    enabled: !!documentId,
  });
}

export function useImportDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: {
      type: 'text' | 'file';
      text?: string;
      language: Language;
      title?: string;
      file?: File;
    }) => {
      if (input.type === 'text' && input.text) {
        return documentsApi.createFromText({
          text: input.text,
          language: input.language,
          title: input.title,
        });
      } else if (input.type === 'file' && input.file) {
        return documentsApi.createFromFile(input.file, input.language);
      }
      throw new Error('Invalid import input');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: documentKeys.all });
    },
  });
}
```

---

## Verification Checklist

### Import Page

- [ ] Tab switching between paste/upload works
- [ ] Language selection persists
- [ ] Word count displays and validates
- [ ] File drag-drop works
- [ ] File removal works
- [ ] Processing shows loading state
- [ ] Success navigates to preview
- [ ] Errors show toast message

### Preview Page

- [ ] Document metadata loads
- [ ] Preview text displays
- [ ] Words are clickable
- [ ] Selected word highlights
- [ ] Progress scrubber updates on click
- [ ] Progress scrubber changes selection
- [ ] Continue button shows if existing session
- [ ] Start Reading creates new session
- [ ] Navigation to reader works

---

## Dependencies to Install

```bash
# In 1.apps/ui/
pnpm add react-window @types/react-window react-dropzone
```

---

## Next: Session 7 - Reader Engine

Session 7 implements the core RSVP reader with:

- Playback timing loop
- ORP-aligned word display
- Token caching and prefetching
- Ramp (build-up) mode
- Time-based rewind
