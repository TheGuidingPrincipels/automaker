# Session 6: Import & Preview UI

## Overview

**Duration**: ~3-4 hours
**Goal**: Build the document import flow and preview interface where users can paste text, upload files, and select their starting position.

**Deliverable**: Complete import form and virtualized preview with word selection and progress scrubber.

---

## Prerequisites

- Session 5 completed (React app with routing, API client, stores)
- Backend running at `http://localhost:8000`

---

## Objectives & Acceptance Criteria

| #   | Objective            | Acceptance Criteria                          |
| --- | -------------------- | -------------------------------------------- |
| 1   | ImportForm component | Paste text, upload .md/.pdf, select language |
| 2   | File upload handling | Drag-drop + click to upload                  |
| 3   | Virtualized preview  | Smooth scroll for 20k words                  |
| 4   | Word click selection | Clicking a word sets start position          |
| 5   | Progress scrubber    | Jump to % position in document               |
| 6   | Start reading action | Navigates to reader with resolved position   |
| 7   | Loading states       | Skeleton during upload/processing            |
| 8   | Error handling       | Display extraction errors clearly            |

---

## File Structure

```
frontend/src/
├── routes/deepread/
│   ├── index.tsx               # Update with ImportForm
│   └── $documentId.tsx         # Document preview page
├── components/
│   ├── import/
│   │   ├── ImportForm.tsx      # Main import container
│   │   ├── TextInput.tsx       # Paste text input
│   │   ├── FileUpload.tsx      # File drag-drop upload
│   │   └── LanguageSelect.tsx  # Language selector
│   └── preview/
│       ├── PreviewContainer.tsx    # Preview page layout
│       ├── PreviewText.tsx         # Virtualized text display
│       ├── PreviewWord.tsx         # Individual clickable word
│       ├── ProgressScrubber.tsx    # Position scrubber
│       └── PreviewControls.tsx     # Start reading button etc
```

---

## Implementation Details

### 1. Language Select (`src/components/import/LanguageSelect.tsx`)

```typescript
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { Language } from '@/lib/api/types'

interface LanguageSelectProps {
  value: Language
  onChange: (value: Language) => void
}

export function LanguageSelect({ value, onChange }: LanguageSelectProps) {
  return (
    <Select value={value} onValueChange={onChange as (v: string) => void}>
      <SelectTrigger className="w-[180px]">
        <SelectValue placeholder="Select language" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="en">English</SelectItem>
        <SelectItem value="de">German (Deutsch)</SelectItem>
      </SelectContent>
    </Select>
  )
}
```

### 2. Text Input (`src/components/import/TextInput.tsx`)

```typescript
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'

interface TextInputProps {
  value: string
  onChange: (value: string) => void
  disabled?: boolean
}

export function TextInput({ value, onChange, disabled }: TextInputProps) {
  const wordCount = value.trim() ? value.trim().split(/\s+/).length : 0
  const isOverLimit = wordCount > 20000

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <Label htmlFor="text-input">Paste your text</Label>
        <span
          className={`text-sm ${isOverLimit ? 'text-destructive' : 'text-muted-foreground'}`}
        >
          {wordCount.toLocaleString()} / 20,000 words
        </span>
      </div>
      <Textarea
        id="text-input"
        placeholder="Paste your text here..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="min-h-[200px] font-mono text-sm resize-y"
      />
      {isOverLimit && (
        <p className="text-sm text-destructive">
          Text exceeds 20,000 word limit. Please shorten or split your text.
        </p>
      )}
    </div>
  )
}
```

### 3. File Upload (`src/components/import/FileUpload.tsx`)

```typescript
import { useCallback, useState } from 'react'
import { Upload, FileText, FileWarning } from 'lucide-react'
import { cn } from '@/lib/cn'

interface FileUploadProps {
  onFileSelect: (file: File) => void
  disabled?: boolean
  acceptedTypes?: string[]
}

export function FileUpload({
  onFileSelect,
  disabled,
  acceptedTypes = ['.md', '.pdf'],
}: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)

  const validateFile = useCallback(
    (file: File): string | null => {
      const extension = '.' + file.name.split('.').pop()?.toLowerCase()

      if (!acceptedTypes.includes(extension)) {
        return `Invalid file type. Accepted: ${acceptedTypes.join(', ')}`
      }

      // 10MB limit
      if (file.size > 10 * 1024 * 1024) {
        return 'File size exceeds 10MB limit'
      }

      return null
    },
    [acceptedTypes]
  )

  const handleFile = useCallback(
    (file: File) => {
      const validationError = validateFile(file)

      if (validationError) {
        setError(validationError)
        setSelectedFile(null)
        return
      }

      setError(null)
      setSelectedFile(file)
      onFileSelect(file)
    },
    [validateFile, onFileSelect]
  )

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)

      if (disabled) return

      const file = e.dataTransfer.files[0]
      if (file) {
        handleFile(file)
      }
    },
    [disabled, handleFile]
  )

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      if (!disabled) {
        setIsDragging(true)
      }
    },
    [disabled]
  )

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleClick = useCallback(() => {
    if (disabled) return

    const input = document.createElement('input')
    input.type = 'file'
    input.accept = acceptedTypes.join(',')
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (file) {
        handleFile(file)
      }
    }
    input.click()
  }, [disabled, acceptedTypes, handleFile])

  return (
    <div className="space-y-2">
      <div
        onClick={handleClick}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={cn(
          'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
          isDragging && 'border-primary bg-primary/5',
          !isDragging && 'border-border hover:border-primary/50',
          disabled && 'opacity-50 cursor-not-allowed',
          error && 'border-destructive'
        )}
      >
        {selectedFile ? (
          <div className="flex flex-col items-center gap-2">
            <FileText className="h-10 w-10 text-primary" />
            <p className="font-medium">{selectedFile.name}</p>
            <p className="text-sm text-muted-foreground">
              {(selectedFile.size / 1024).toFixed(1)} KB
            </p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <Upload className="h-10 w-10 text-muted-foreground" />
            <p className="font-medium">Drop a file here or click to browse</p>
            <p className="text-sm text-muted-foreground">
              Supports: {acceptedTypes.join(', ')} (max 10MB)
            </p>
          </div>
        )}
      </div>

      {error && (
        <div className="flex items-center gap-2 text-destructive text-sm">
          <FileWarning className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}
    </div>
  )
}
```

### 4. Import Form (`src/components/import/ImportForm.tsx`)

```typescript
import { useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Loader2 } from 'lucide-react'

import { TextInput } from './TextInput'
import { FileUpload } from './FileUpload'
import { LanguageSelect } from './LanguageSelect'
import { ErrorDisplay } from '@/components/common/ErrorDisplay'
import {
  useCreateDocumentFromText,
  useCreateDocumentFromFile,
} from '@/hooks/useDocuments'
import type { Language } from '@/lib/api/types'

export function ImportForm() {
  const navigate = useNavigate()

  const [activeTab, setActiveTab] = useState<'paste' | 'upload'>('paste')
  const [language, setLanguage] = useState<Language>('en')
  const [text, setText] = useState('')
  const [file, setFile] = useState<File | null>(null)

  const createFromText = useCreateDocumentFromText()
  const createFromFile = useCreateDocumentFromFile()

  const isLoading = createFromText.isPending || createFromFile.isPending
  const error = createFromText.error || createFromFile.error

  const canSubmit =
    !isLoading &&
    ((activeTab === 'paste' && text.trim().length > 0) ||
      (activeTab === 'upload' && file !== null))

  const handleSubmit = async () => {
    try {
      let documentId: string

      if (activeTab === 'paste') {
        const result = await createFromText.mutateAsync({
          language,
          text: text.trim(),
        })
        documentId = result.id
      } else {
        if (!file) return
        const result = await createFromFile.mutateAsync({ file, language })
        documentId = result.id
      }

      // Navigate to preview
      navigate({ to: '/deepread/$documentId', params: { documentId } })
    } catch (e) {
      // Error handled by mutation
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Import Document</span>
          <LanguageSelect value={language} onChange={setLanguage} />
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Tabs
          value={activeTab}
          onValueChange={(v) => setActiveTab(v as 'paste' | 'upload')}
        >
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="paste">Paste Text</TabsTrigger>
            <TabsTrigger value="upload">Upload File</TabsTrigger>
          </TabsList>

          <TabsContent value="paste" className="mt-4">
            <TextInput
              value={text}
              onChange={setText}
              disabled={isLoading}
            />
          </TabsContent>

          <TabsContent value="upload" className="mt-4">
            <FileUpload
              onFileSelect={setFile}
              disabled={isLoading}
            />
          </TabsContent>
        </Tabs>

        {error && (
          <ErrorDisplay
            message={error.message}
            onRetry={() => {
              createFromText.reset()
              createFromFile.reset()
            }}
          />
        )}

        <Button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="w-full"
          size="lg"
        >
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Processing...
            </>
          ) : (
            'Continue to Preview'
          )}
        </Button>
      </CardContent>
    </Card>
  )
}
```

### 5. Preview Word (`src/components/preview/PreviewWord.tsx`)

```typescript
import { memo } from 'react'
import { cn } from '@/lib/cn'

interface PreviewWordProps {
  word: string
  index: number
  isSelected: boolean
  isSentenceStart: boolean
  isParagraphStart: boolean
  onClick: (index: number) => void
}

export const PreviewWord = memo(function PreviewWord({
  word,
  index,
  isSelected,
  isSentenceStart,
  isParagraphStart,
  onClick,
}: PreviewWordProps) {
  return (
    <span
      onClick={() => onClick(index)}
      className={cn(
        'cursor-pointer hover:bg-primary/20 px-0.5 rounded transition-colors',
        isSelected && 'bg-primary text-primary-foreground',
        isParagraphStart && 'ml-0',  // Reset margin for paragraph starts
      )}
      data-index={index}
    >
      {word}
    </span>
  )
})
```

### 6. Virtualized Preview Text (`src/components/preview/PreviewText.tsx`)

```typescript
import { useCallback, useMemo, useRef, useEffect, useState } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { PreviewWord } from './PreviewWord'
import type { Token } from '@/lib/api/types'

interface PreviewTextProps {
  text: string
  tokens: Token[]
  selectedWordIndex: number | null
  onWordClick: (index: number) => void
  scrollToIndex?: number | null
}

// Group tokens into lines for virtualization
function groupIntoLines(tokens: Token[], text: string): Token[][] {
  const lines: Token[][] = []
  let currentLine: Token[] = []

  for (const token of tokens) {
    // Start new line on paragraph break
    if (token.is_paragraph_start && currentLine.length > 0) {
      lines.push(currentLine)
      lines.push([])  // Empty line for paragraph break
      currentLine = []
    }

    currentLine.push(token)

    // Rough line breaking at ~80 chars
    const lineLength = currentLine.reduce(
      (sum, t) => sum + t.display_text.length + 1,
      0
    )
    if (lineLength > 80 && !token.is_sentence_start) {
      // Find a good break point
      lines.push(currentLine)
      currentLine = []
    }
  }

  if (currentLine.length > 0) {
    lines.push(currentLine)
  }

  return lines
}

export function PreviewText({
  text,
  tokens,
  selectedWordIndex,
  onWordClick,
  scrollToIndex,
}: PreviewTextProps) {
  const parentRef = useRef<HTMLDivElement>(null)
  const [lines, setLines] = useState<Token[][]>([])

  // Group tokens into lines
  useEffect(() => {
    if (tokens.length > 0) {
      setLines(groupIntoLines(tokens, text))
    }
  }, [tokens, text])

  const virtualizer = useVirtualizer({
    count: lines.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 28,  // Estimated line height
    overscan: 20,
  })

  // Scroll to selected word's line
  useEffect(() => {
    if (scrollToIndex !== null && scrollToIndex !== undefined) {
      // Find which line contains this word
      let lineIndex = 0
      let wordCount = 0

      for (let i = 0; i < lines.length; i++) {
        wordCount += lines[i].length
        if (wordCount > scrollToIndex) {
          lineIndex = i
          break
        }
      }

      virtualizer.scrollToIndex(lineIndex, { align: 'center' })
    }
  }, [scrollToIndex, lines, virtualizer])

  const handleWordClick = useCallback(
    (index: number) => {
      onWordClick(index)
    },
    [onWordClick]
  )

  if (tokens.length === 0) {
    return (
      <div className="text-center text-muted-foreground py-8">
        Loading preview...
      </div>
    )
  }

  return (
    <div
      ref={parentRef}
      className="h-[400px] overflow-auto border border-border rounded-lg bg-card p-4 font-mono text-sm"
    >
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((virtualRow) => {
          const lineTokens = lines[virtualRow.index]

          // Empty line (paragraph break)
          if (!lineTokens || lineTokens.length === 0) {
            return (
              <div
                key={virtualRow.key}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: `${virtualRow.size}px`,
                  transform: `translateY(${virtualRow.start}px)`,
                }}
              />
            )
          }

          return (
            <div
              key={virtualRow.key}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                transform: `translateY(${virtualRow.start}px)`,
              }}
              className="leading-7"
            >
              {lineTokens.map((token) => (
                <PreviewWord
                  key={token.word_index}
                  word={token.display_text}
                  index={token.word_index}
                  isSelected={token.word_index === selectedWordIndex}
                  isSentenceStart={token.is_sentence_start}
                  isParagraphStart={token.is_paragraph_start}
                  onClick={handleWordClick}
                />
              ))}
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

### 7. Progress Scrubber (`src/components/preview/ProgressScrubber.tsx`)

```typescript
import { Slider } from '@/components/ui/slider'

interface ProgressScrubberProps {
  totalWords: number
  currentIndex: number
  onChange: (index: number) => void
}

export function ProgressScrubber({
  totalWords,
  currentIndex,
  onChange,
}: ProgressScrubberProps) {
  const percentage = totalWords > 0 ? (currentIndex / totalWords) * 100 : 0

  const handleChange = (value: number[]) => {
    const newIndex = Math.floor((value[0] / 100) * totalWords)
    onChange(newIndex)
  }

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm text-muted-foreground">
        <span>Position: {currentIndex.toLocaleString()} / {totalWords.toLocaleString()}</span>
        <span>{percentage.toFixed(1)}%</span>
      </div>
      <Slider
        value={[percentage]}
        onValueChange={handleChange}
        max={100}
        step={0.1}
        className="w-full"
      />
    </div>
  )
}
```

### 8. Preview Controls (`src/components/preview/PreviewControls.tsx`)

```typescript
import { Button } from '@/components/ui/button'
import { Play, ArrowLeft } from 'lucide-react'
import { useReaderStore } from '@/stores/readerStore'

interface PreviewControlsProps {
  documentTitle: string
  selectedWordIndex: number | null
  resolvedIndex: number | null
  resolveReason: string | null
  onStartReading: () => void
  onBack: () => void
  isResolving?: boolean
}

export function PreviewControls({
  documentTitle,
  selectedWordIndex,
  resolvedIndex,
  resolveReason,
  onStartReading,
  onBack,
  isResolving,
}: PreviewControlsProps) {
  const { settings } = useReaderStore()

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={onBack}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
        <h1 className="text-lg font-semibold truncate max-w-md">{documentTitle}</h1>
        <div className="w-20" /> {/* Spacer for centering */}
      </div>

      <div className="flex items-center justify-between p-4 bg-card rounded-lg border border-border">
        <div className="space-y-1">
          <p className="text-sm text-muted-foreground">
            Starting position:
            {selectedWordIndex !== null ? (
              <span className="ml-2 font-medium text-foreground">
                Word {selectedWordIndex.toLocaleString()}
                {resolvedIndex !== null && resolvedIndex !== selectedWordIndex && (
                  <span className="text-primary ml-1">
                    → {resolvedIndex.toLocaleString()} ({resolveReason})
                  </span>
                )}
              </span>
            ) : (
              <span className="ml-2">Beginning of document</span>
            )}
          </p>
          <p className="text-sm text-muted-foreground">
            Target speed: <span className="font-medium text-foreground">{settings.targetWpm} WPM</span>
            {settings.rampEnabled && (
              <span className="text-muted-foreground">
                {' '}(ramp from {Math.round(settings.targetWpm * 0.5)} over {settings.rampSeconds}s)
              </span>
            )}
          </p>
        </div>

        <Button onClick={onStartReading} size="lg" disabled={isResolving}>
          <Play className="h-5 w-5 mr-2" />
          Start Reading
        </Button>
      </div>
    </div>
  )
}
```

### 9. Preview Container (`src/components/preview/PreviewContainer.tsx`)

```typescript
import { useState, useCallback, useEffect } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { PreviewText } from './PreviewText'
import { ProgressScrubber } from './ProgressScrubber'
import { PreviewControls } from './PreviewControls'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { ErrorDisplay } from '@/components/common/ErrorDisplay'
import { useDocumentPreview, useTokenChunk, useResolveStart } from '@/hooks/useDocuments'
import { sessionsApi } from '@/lib/api/sessions'
import { useAppStore } from '@/stores/appStore'
import { useReaderStore } from '@/stores/readerStore'

interface PreviewContainerProps {
  documentId: string
}

export function PreviewContainer({ documentId }: PreviewContainerProps) {
  const navigate = useNavigate()

  const { data: preview, isLoading, error } = useDocumentPreview(documentId)
  const { data: tokenChunk } = useTokenChunk(documentId, 0)

  const [selectedWordIndex, setSelectedWordIndex] = useState<number | null>(null)
  const [resolvedIndex, setResolvedIndex] = useState<number | null>(null)
  const [resolveReason, setResolveReason] = useState<string | null>(null)

  const resolveStart = useResolveStart(documentId)
  const { settings } = useReaderStore()
  const { setCurrentDocument, setCurrentSession, enterReaderMode } = useAppStore()

  // Resolve start position when selection changes
  useEffect(() => {
    if (selectedWordIndex === null) {
      setResolvedIndex(null)
      setResolveReason(null)
      return
    }

    resolveStart.mutate(
      {
        approx_word_index: selectedWordIndex,
        prefer: 'sentence',
        direction: 'backward',
      },
      {
        onSuccess: (result) => {
          setResolvedIndex(result.resolved_word_index)
          setResolveReason(result.reason)
        },
      }
    )
  }, [selectedWordIndex])

  const handleWordClick = useCallback((index: number) => {
    setSelectedWordIndex(index)
  }, [])

  const handleScrubberChange = useCallback((index: number) => {
    setSelectedWordIndex(index)
  }, [])

  const handleStartReading = useCallback(async () => {
    const startIndex = resolvedIndex ?? selectedWordIndex ?? 0

    // Create session
    const session = await sessionsApi.create({
      document_id: documentId,
      start_word_index: startIndex,
      target_wpm: settings.targetWpm,
      ramp_enabled: settings.rampEnabled,
      ramp_seconds: settings.rampSeconds,
    })

    // Update app state
    setCurrentDocument(documentId)
    setCurrentSession(session.id)
    enterReaderMode()

    // Navigate to reader (same page, different mode)
    navigate({
      to: '/deepread/$documentId',
      params: { documentId },
      search: { reading: true, sessionId: session.id },
    })
  }, [documentId, resolvedIndex, selectedWordIndex, settings, navigate])

  const handleBack = useCallback(() => {
    navigate({ to: '/deepread' })
  }, [navigate])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (error || !preview) {
    return (
      <ErrorDisplay
        message={error?.message || 'Failed to load document'}
        onRetry={() => window.location.reload()}
      />
    )
  }

  return (
    <div className="space-y-6">
      <PreviewControls
        documentTitle={preview.title}
        selectedWordIndex={selectedWordIndex}
        resolvedIndex={resolvedIndex}
        resolveReason={resolveReason}
        onStartReading={handleStartReading}
        onBack={handleBack}
        isResolving={resolveStart.isPending}
      />

      <ProgressScrubber
        totalWords={preview.total_words}
        currentIndex={selectedWordIndex ?? 0}
        onChange={handleScrubberChange}
      />

      <PreviewText
        text={preview.preview_text}
        tokens={tokenChunk?.tokens ?? []}
        selectedWordIndex={selectedWordIndex}
        onWordClick={handleWordClick}
        scrollToIndex={selectedWordIndex}
      />

      <p className="text-sm text-muted-foreground text-center">
        Click any word to set your starting position, or use the scrubber above.
      </p>
    </div>
  )
}
```

### 10. Update DeepRead Index (`src/routes/deepread/index.tsx`)

```typescript
import { createFileRoute } from '@tanstack/react-router'
import { Container } from '@/components/layout/Container'
import { ImportForm } from '@/components/import/ImportForm'

export const Route = createFileRoute('/deepread/')({
  component: DeepReadPage,
})

function DeepReadPage() {
  return (
    <Container className="max-w-3xl">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">DeepRead</h1>
          <p className="text-muted-foreground">
            Speed reading with RSVP technology. Paste text or upload a document to get started.
          </p>
        </div>

        <ImportForm />

        {/* Recent sessions - coming in Session 9 */}
      </div>
    </Container>
  )
}
```

### 11. Document Preview Route (`src/routes/deepread/$documentId.tsx`)

```typescript
import { createFileRoute } from '@tanstack/react-router'
import { Container } from '@/components/layout/Container'
import { PreviewContainer } from '@/components/preview/PreviewContainer'
import { useAppStore } from '@/stores/appStore'

interface SearchParams {
  reading?: boolean
  sessionId?: string
}

export const Route = createFileRoute('/deepread/$documentId')({
  component: DocumentPage,
  validateSearch: (search: Record<string, unknown>): SearchParams => ({
    reading: search.reading === true || search.reading === 'true',
    sessionId: typeof search.sessionId === 'string' ? search.sessionId : undefined,
  }),
})

function DocumentPage() {
  const { documentId } = Route.useParams()
  const { reading, sessionId } = Route.useSearch()
  const isReaderMode = useAppStore((s) => s.isReaderMode)

  // If in reader mode, render reader (Session 7)
  if (reading && sessionId) {
    return (
      <div className="fixed inset-0 bg-black flex items-center justify-center">
        <p className="text-white">Reader mode - Coming in Session 7</p>
      </div>
    )
  }

  // Otherwise render preview
  return (
    <Container className="max-w-4xl">
      <PreviewContainer documentId={documentId} />
    </Container>
  )
}
```

### 12. Add Virtual List Dependency

```bash
pnpm add @tanstack/react-virtual
```

---

## Additional shadcn/ui Components

```bash
pnpm dlx shadcn@latest add textarea
pnpm dlx shadcn@latest add label
pnpm dlx shadcn@latest add tabs
```

---

## Testing Requirements

### Manual Testing Checklist

- [ ] Paste text into textarea, word count updates
- [ ] Word count turns red when >20,000 words
- [ ] File upload accepts .md and .pdf files
- [ ] File upload rejects other file types
- [ ] Drag-and-drop works for file upload
- [ ] Language selector changes language
- [ ] "Continue to Preview" creates document and navigates
- [ ] Preview shows full document text
- [ ] Clicking a word highlights it
- [ ] Progress scrubber updates selected position
- [ ] Selected position resolves to sentence start
- [ ] "Start Reading" creates session and enters reader mode
- [ ] Back button returns to import page
- [ ] Large documents (10k+ words) scroll smoothly

### Integration Test

```typescript
// tests/e2e/import-preview.spec.ts
import { test, expect } from '@playwright/test';

test('import and preview flow', async ({ page }) => {
  await page.goto('/deepread');

  // Paste text
  await page.fill('textarea', 'This is a test. It has multiple sentences. Testing the preview.');

  // Select English
  await page.click('text=English');

  // Submit
  await page.click('text=Continue to Preview');

  // Wait for preview
  await expect(page.locator('text=This is a test')).toBeVisible();

  // Click a word
  await page.click('text=multiple');

  // Verify selection shows
  await expect(page.locator('text=Starting position')).toContainText('multiple');

  // Start reading
  await page.click('text=Start Reading');

  // Verify reader mode (placeholder for now)
  await expect(page.locator('text=Reader mode')).toBeVisible();
});
```

---

## Verification Checklist

- [ ] ImportForm renders with paste and upload tabs
- [ ] TextInput shows word count and enforces limit
- [ ] FileUpload handles drag-drop and click
- [ ] Language selector works
- [ ] Document creation navigates to preview
- [ ] PreviewText renders with virtualization
- [ ] Word clicking sets selection
- [ ] Progress scrubber changes position
- [ ] resolve-start API is called on selection
- [ ] Start Reading creates session
- [ ] Navigation to reader mode works
- [ ] Error states display correctly
- [ ] Loading states show spinners

---

## Context for Next Session

**What exists after Session 6:**

- Complete import flow (paste/upload/language)
- Document preview with virtualized text
- Word selection and position resolution
- Progress scrubber for navigation
- Session creation on "Start Reading"

**Session 7 will need:**

- Session ID from URL params
- Token chunk fetching hooks
- useReaderStore for playback settings
- Selected start position
