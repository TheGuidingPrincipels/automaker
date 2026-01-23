# Sub-Plan F-3: UI Components (Replace Blueprints)

> **Prerequisites**: Sub-Plan F-2 (API Client & Types) complete
> **Execution Location**: Automaker repository (`/Users/ruben/Documents/GitHub/automaker/`)
> **Effort**: Large (8-16 hours)
> **Result**: Blueprints section replaced with Knowledge Library

---

## Goal

Replace the "Blueprints" section in Knowledge Hub with the AI-Library "Knowledge Library" UI, providing three views:

1. **Input Mode** - Extract content from documents
2. **Library Browser** - Browse and search the library
3. **Query Mode** - Ask questions with RAG

---

## Architecture Overview

```
Knowledge Hub (Main Page)
├── Knowledge Library (was: Blueprints)  ← REPLACE
│   ├── Input Mode (extraction workflow)
│   ├── Library Browser (browse/search)
│   └── Query Mode (RAG Q&A)
├── Knowledge Server (keep as-is)
└── Learning (keep as-is)
```

---

## Step 1: Update Knowledge Hub Landing Page

### 1.1 Update Section Card

Modify `apps/ui/src/components/views/knowledge-hub-page/index.tsx`:

**Before:**

```typescript
{
  id: 'blueprints',
  label: 'Blueprints',
  icon: FileCode2,
  description: 'Guidelines and processes for agents',
  count: 12,
  // ...
}
```

**After:**

```typescript
{
  id: 'knowledge-library',
  label: 'Knowledge Library',
  icon: Library, // from lucide-react
  description: 'Your personal knowledge base with AI-powered search',
  count: library.data?.total_files ?? 0, // from useKLLibrary()
  gradient: 'from-emerald-500 to-teal-500',
  features: ['Extract content', 'Semantic search', 'RAG Q&A'],
}
```

### 1.2 Update Route

The route `/knowledge-hub/blueprints` becomes `/knowledge-hub/knowledge-library`.

Update navigation and any links to use the new route.

---

## Step 2: Create Component Structure

```
apps/ui/src/components/views/knowledge-library/
├── index.tsx                        # Main container with tab navigation
├── components/
│   ├── view-tabs.tsx                # Input | Library | Query tabs
│   ├── connection-status.tsx        # API health indicator
│   │
│   ├── input-mode/
│   │   ├── index.tsx                # Input mode container
│   │   ├── session-list.tsx         # List of extraction sessions
│   │   ├── new-session-dialog.tsx   # Create session + upload
│   │   ├── plan-review/
│   │   │   ├── index.tsx            # Plan review screen
│   │   │   ├── cleanup-phase.tsx    # Keep/discard decisions
│   │   │   ├── routing-phase.tsx    # Destination selection
│   │   │   ├── block-card.tsx       # Single block with options
│   │   │   ├── mode-toggle.tsx      # Strict/Refinement toggle
│   │   │   └── execution-status.tsx # Execute + verification results
│   │   └── merge-dialog.tsx         # Triple-view merge preview
│   │
│   ├── library-browser/
│   │   ├── index.tsx                # Library browser container
│   │   ├── category-tree.tsx        # Folder/category navigation
│   │   ├── file-list.tsx            # Files in current category
│   │   ├── file-viewer.tsx          # Markdown file preview
│   │   └── search-bar.tsx           # Keyword search
│   │
│   └── query-mode/
│       ├── index.tsx                # Query mode container
│       ├── chat-interface.tsx       # Question input + answer display
│       ├── answer-card.tsx          # Single answer with citations
│       ├── source-citation.tsx      # Clickable source reference
│       └── conversation-history.tsx # Previous conversations
│
└── hooks/
    └── use-session-workflow.ts      # Orchestrates session phases
```

---

## Step 3: Main Container

Create `apps/ui/src/components/views/knowledge-library/index.tsx`:

```typescript
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useKnowledgeLibraryStore } from '@/store/knowledge-library-store';
import { useKLHealth } from '@/hooks/queries/use-knowledge-library';
import { ConnectionStatus } from './components/connection-status';
import { InputMode } from './components/input-mode';
import { LibraryBrowser } from './components/library-browser';
import { QueryMode } from './components/query-mode';
import { Upload, FolderOpen, MessageSquare } from 'lucide-react';

export function KnowledgeLibrary() {
  const { activeView, setActiveView } = useKnowledgeLibraryStore();
  const health = useKLHealth();

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <h1 className="text-2xl font-bold">Knowledge Library</h1>
        <ConnectionStatus status={health.data?.status} isLoading={health.isLoading} />
      </div>

      {/* Tab Navigation */}
      <Tabs value={activeView} onValueChange={(v) => setActiveView(v as any)} className="flex-1 flex flex-col">
        <TabsList className="mx-4 mt-4">
          <TabsTrigger value="input" className="gap-2">
            <Upload className="h-4 w-4" />
            Input
          </TabsTrigger>
          <TabsTrigger value="library" className="gap-2">
            <FolderOpen className="h-4 w-4" />
            Library
          </TabsTrigger>
          <TabsTrigger value="query" className="gap-2">
            <MessageSquare className="h-4 w-4" />
            Query
          </TabsTrigger>
        </TabsList>

        <div className="flex-1 overflow-hidden">
          <TabsContent value="input" className="h-full m-0 p-4">
            <InputMode />
          </TabsContent>
          <TabsContent value="library" className="h-full m-0 p-4">
            <LibraryBrowser />
          </TabsContent>
          <TabsContent value="query" className="h-full m-0 p-4">
            <QueryMode />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
```

---

## Step 4: Input Mode Components

### 4.1 Session List

Shows existing sessions and allows creating new ones:

```typescript
// input-mode/index.tsx
export function InputMode() {
  const { currentSessionId, setCurrentSession } = useKnowledgeLibraryStore();
  const sessions = useKLSessions();

  if (currentSessionId) {
    return <PlanReview sessionId={currentSessionId} onBack={() => setCurrentSession(null)} />;
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">Extraction Sessions</h2>
        <NewSessionDialog />
      </div>
      <SessionList sessions={sessions.data?.sessions ?? []} />
    </div>
  );
}
```

### 4.2 Plan Review (Core UI)

The plan review screen shows all blocks at once with cleanup → routing → execute workflow:

```typescript
// input-mode/plan-review/index.tsx
export function PlanReview({ sessionId, onBack }) {
  const session = useKLSession(sessionId);
  const cleanup = useKLCleanupPlan(sessionId);
  const routing = useKLRoutingPlan(sessionId);

  // Determine current phase
  const phase = session.data?.phase;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={onBack}>← Back</Button>
        <h2 className="text-lg font-semibold">Session: {sessionId}</h2>
        <ModeToggle sessionId={sessionId} mode={session.data?.content_mode} />
      </div>

      {/* Phase-based content */}
      {phase === 'cleanup_plan_ready' && (
        <CleanupPhase sessionId={sessionId} cleanup={cleanup.data} />
      )}

      {phase === 'routing_plan_ready' && (
        <RoutingPhase sessionId={sessionId} routing={routing.data} />
      )}

      {phase === 'completed' && (
        <ExecutionStatus sessionId={sessionId} />
      )}
    </div>
  );
}
```

### 4.3 Block Card

Each block shows content preview and destination options:

```typescript
// input-mode/plan-review/block-card.tsx
export function BlockCard({ block, sessionId, hasMerge, onViewMerge }) {
  const selectDestination = useKLSelectDestination(sessionId);
  const rejectBlock = useKLRejectBlock(sessionId);

  const isResolved = block.status !== 'pending';

  return (
    <Card className={isResolved ? 'border-green-500 bg-green-50/50' : ''}>
      <CardHeader>
        <div className="flex justify-between">
          <Badge variant="outline">{block.heading_path.join(' › ')}</Badge>
          <Badge>{block.status}</Badge>
        </div>
      </CardHeader>

      <CardContent>
        <p className="text-sm bg-muted p-2 rounded line-clamp-3">
          {block.content_preview}
        </p>

        {/* Top-3 destination options */}
        <div className="mt-4 space-y-2">
          {block.options.map((opt, idx) => (
            <button
              key={idx}
              className="w-full text-left border rounded p-3 hover:bg-muted"
              onClick={() => selectDestination.mutate({ blockId: block.block_id, option_index: idx })}
            >
              <div className="flex justify-between">
                <span className="font-medium">{opt.destination_file}</span>
                <span className="text-sm text-muted-foreground">
                  {Math.round(opt.confidence * 100)}%
                </span>
              </div>
              <p className="text-sm text-muted-foreground">{opt.reasoning}</p>
            </button>
          ))}
        </div>
      </CardContent>

      <CardFooter className="gap-2">
        {hasMerge && <Button variant="outline" size="sm" onClick={onViewMerge}>View Merge</Button>}
        <Button variant="destructive" size="sm" onClick={() => rejectBlock.mutate(block.block_id)}>
          Reject
        </Button>
      </CardFooter>
    </Card>
  );
}
```

---

## Step 5: Library Browser Components

### 5.1 Category Tree

Shows folder structure for navigation:

```typescript
// library-browser/index.tsx
export function LibraryBrowser() {
  const library = useKLLibrary();
  const { selectedFilePath, setSelectedFile } = useKnowledgeLibraryStore();

  return (
    <div className="flex h-full gap-4">
      {/* Sidebar: Category tree */}
      <div className="w-64 border-r overflow-auto">
        <SearchBar />
        <CategoryTree
          categories={library.data?.categories ?? []}
          onSelectFile={setSelectedFile}
        />
      </div>

      {/* Main: File viewer */}
      <div className="flex-1 overflow-auto">
        {selectedFilePath ? (
          <FileViewer path={selectedFilePath} />
        ) : (
          <div className="flex items-center justify-center h-full text-muted-foreground">
            Select a file to view
          </div>
        )}
      </div>
    </div>
  );
}
```

### 5.2 File Viewer

Renders markdown content with syntax highlighting:

```typescript
// library-browser/file-viewer.tsx
export function FileViewer({ path }) {
  const file = useKLFile(path);

  if (file.isLoading) return <Skeleton />;
  if (file.error) return <Alert variant="destructive">Failed to load file</Alert>;

  return (
    <div className="prose prose-sm max-w-none dark:prose-invert">
      <div className="flex justify-between items-center mb-4">
        <h2>{path}</h2>
        <Badge variant="outline">{file.data?.metadata?.block_count} blocks</Badge>
      </div>
      <ReactMarkdown>{file.data?.content}</ReactMarkdown>
    </div>
  );
}
```

---

## Step 6: Query Mode Components

### 6.1 Chat Interface

Conversational Q&A with your library:

```typescript
// query-mode/index.tsx
export function QueryMode() {
  const { queryHistory, currentConversationId, addQueryResult, clearQueryHistory } =
    useKnowledgeLibraryStore();
  const queryMutation = useKLQueryLibrary();
  const [question, setQuestion] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    const result = await queryMutation.mutateAsync({
      question,
      conversation_id: currentConversationId ?? undefined,
    });
    addQueryResult(result);
    setQuestion('');
  };

  return (
    <div className="flex flex-col h-full">
      {/* Conversation history */}
      <div className="flex-1 overflow-auto space-y-4 p-4">
        {queryHistory.length === 0 && (
          <div className="text-center text-muted-foreground py-8">
            Ask a question about your knowledge library
          </div>
        )}
        {queryHistory.map((result, idx) => (
          <AnswerCard key={idx} result={result} />
        ))}
        {queryMutation.isPending && (
          <div className="text-center text-muted-foreground">Searching...</div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t flex gap-2">
        <Input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question..."
          className="flex-1"
        />
        <Button type="submit" disabled={queryMutation.isPending}>Ask</Button>
      </form>
    </div>
  );
}
```

### 6.2 Answer Card

Displays answer with sources and confidence:

```typescript
// query-mode/answer-card.tsx
export function AnswerCard({ result }: { result: KLQueryResponse }) {
  return (
    <Card>
      <CardContent className="pt-4">
        {/* Confidence badge */}
        <div className="flex justify-end mb-2">
          <Badge variant="outline">
            {Math.round(result.confidence * 100)}% confident
          </Badge>
        </div>

        {/* Answer */}
        <div className="prose prose-sm max-w-none">
          <ReactMarkdown>{result.answer}</ReactMarkdown>
        </div>

        {/* Sources */}
        {result.sources.length > 0 && (
          <div className="mt-4 pt-4 border-t">
            <h4 className="text-sm font-medium mb-2">Sources</h4>
            <ul className="text-sm space-y-1">
              {result.sources.map((source, i) => (
                <SourceCitation key={i} source={source} />
              ))}
            </ul>
          </div>
        )}

        {/* Related topics */}
        {result.related_topics.length > 0 && (
          <div className="mt-2 flex gap-1 flex-wrap">
            {result.related_topics.map((topic, i) => (
              <Badge key={i} variant="secondary" className="text-xs">{topic}</Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

---

## Step 7: Update Section Route

Update `apps/ui/src/routes/knowledge-hub.$section.tsx`:

```typescript
import { KnowledgeLibrary } from '@/components/views/knowledge-library';
import { KnowledgeSectionPage } from '@/components/views/knowledge-section-page';

export function KnowledgeHubSection() {
  const { section } = useParams({ from: '/knowledge-hub/$section' });

  // Route to Knowledge Library for the new section
  if (section === 'knowledge-library') {
    return <KnowledgeLibrary />;
  }

  // Keep existing behavior for other sections
  return <KnowledgeSectionPage sectionId={section} />;
}
```

---

## Step 8: Update Navigation

Update `apps/ui/src/components/views/knowledge-hub-page/index.tsx` to link to the new section:

```typescript
const sections = [
  {
    id: 'knowledge-library',
    label: 'Knowledge Library',
    icon: Library,
    description: 'Your personal knowledge base with AI-powered search',
    gradient: 'from-emerald-500 to-teal-500',
    features: ['Extract content', 'Semantic search', 'RAG Q&A'],
  },
  // ... keep knowledge-server and learning
];

// Navigation handler
const handleSectionClick = (sectionId: string) => {
  navigate({ to: '/knowledge-hub/$section', params: { section: sectionId } });
};
```

---

## Acceptance Criteria

### Navigation

- [ ] Knowledge Hub shows "Knowledge Library" instead of "Blueprints"
- [ ] Clicking navigates to `/knowledge-hub/knowledge-library`
- [ ] Tab navigation between Input / Library / Query works

### Input Mode

- [ ] Session list displays existing sessions
- [ ] Can create new session and upload file
- [ ] Cleanup phase shows keep/discard decisions
- [ ] Routing phase shows destination options per block
- [ ] Can select destination from top-3 options
- [ ] Mode toggle switches between Strict/Refinement
- [ ] Execute button disabled until all blocks resolved
- [ ] Execution results display with verification status

### Library Browser

- [ ] Category tree shows library structure
- [ ] Can navigate folders and select files
- [ ] File content renders as markdown
- [ ] Search filters files

### Query Mode

- [ ] Can type and submit questions
- [ ] Answers display with markdown formatting
- [ ] Sources shown with links to files
- [ ] Confidence score displayed
- [ ] Conversation history persists

### Integration

- [ ] Connection status shows API health
- [ ] Graceful error handling when API unavailable
- [ ] Loading states for all async operations

---

## Component Library Notes

Use existing Automaker UI components:

- `Button`, `Card`, `Badge` from `@/components/ui`
- `Dialog` for modals
- `Tabs` for view switching
- Follow existing styling patterns

---

## Testing Checklist

1. Start AI-Library backend: `./start-api.sh`
2. Start Automaker: `npm run dev`
3. Navigate to Knowledge Hub
4. Verify "Knowledge Library" section appears
5. Test each view (Input, Library, Query)
6. Test with API down (graceful degradation)

---

_End of Sub-Plan F-3_
