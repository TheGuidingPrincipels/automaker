# Session 9: Session Persistence & History

## Overview

**Duration**: ~2-3 hours
**Goal**: Implement auto-save progress, session resume functionality, recent sessions list, and proper unload handling.

**Deliverable**: Users can resume reading where they left off, see recent sessions, and progress is reliably saved.

---

## Prerequisites

- Session 8 completed (reader with controls)
- Backend sessions API functional
- useReaderStore with settings

---

## Objectives & Acceptance Criteria

| #   | Objective            | Acceptance Criteria                           |
| --- | -------------------- | --------------------------------------------- |
| 1   | Auto-save progress   | Progress saved every 10s during playback      |
| 2   | Save on pause        | Progress saved immediately on pause           |
| 3   | Save on unload       | Best-effort save on page close                |
| 4   | Resume session       | "Continue Reading" resumes from last position |
| 5   | Recent sessions list | Shows last 7 days of sessions                 |
| 6   | Session card         | Shows title, progress, time since last read   |
| 7   | Delete session       | Can remove sessions from history              |

---

## File Structure

```
frontend/src/
├── components/
│   ├── sessions/
│   │   ├── RecentSessions.tsx      # Recent sessions list
│   │   ├── SessionCard.tsx         # Individual session card
│   │   └── ContinueReading.tsx     # Continue button for document
├── hooks/
│   ├── useSessions.ts              # Session query hooks
│   ├── useAutoSave.ts              # Auto-save logic
│   └── useBeforeUnload.ts          # Unload handling
└── routes/deepread/
    └── index.tsx                   # Update with sessions list
```

---

## Implementation Details

### 1. Session Query Hooks (`src/hooks/useSessions.ts`)

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { sessionsApi } from '@/lib/api/sessions';
import type { CreateSessionRequest, UpdateProgressRequest } from '@/lib/api/types';

export const sessionKeys = {
  all: ['sessions'] as const,
  recent: (days: number) => ['sessions', 'recent', days] as const,
  detail: (id: string) => ['sessions', id] as const,
  forDocument: (docId: string) => ['sessions', 'document', docId] as const,
};

export function useRecentSessions(days = 7) {
  return useQuery({
    queryKey: sessionKeys.recent(days),
    queryFn: () => sessionsApi.getRecent(days),
    staleTime: 1000 * 60, // 1 minute
  });
}

export function useSession(sessionId: string | null) {
  return useQuery({
    queryKey: sessionKeys.detail(sessionId!),
    queryFn: () => sessionsApi.getSession(sessionId!),
    enabled: !!sessionId,
  });
}

export function useLatestSessionForDocument(documentId: string | null) {
  return useQuery({
    queryKey: sessionKeys.forDocument(documentId!),
    queryFn: () => sessionsApi.getLatestForDocument(documentId!),
    enabled: !!documentId,
  });
}

export function useCreateSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateSessionRequest) => sessionsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sessionKeys.all });
    },
  });
}

export function useUpdateProgress() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionId, data }: { sessionId: string; data: UpdateProgressRequest }) =>
      sessionsApi.updateProgress(sessionId, data),
    // Optimistic update
    onMutate: async ({ sessionId, data }) => {
      await queryClient.cancelQueries({ queryKey: sessionKeys.detail(sessionId) });

      const previousSession = queryClient.getQueryData(sessionKeys.detail(sessionId));

      queryClient.setQueryData(sessionKeys.detail(sessionId), (old: any) => ({
        ...old,
        current_word_index: data.current_word_index,
        last_known_percent: data.last_known_percent,
      }));

      return { previousSession };
    },
    onError: (err, { sessionId }, context) => {
      if (context?.previousSession) {
        queryClient.setQueryData(sessionKeys.detail(sessionId), context.previousSession);
      }
    },
    onSettled: (_, __, { sessionId }) => {
      queryClient.invalidateQueries({ queryKey: sessionKeys.recent(7) });
    },
  });
}

export function useDeleteSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (sessionId: string) => sessionsApi.deleteSession(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sessionKeys.all });
    },
  });
}
```

### 2. Auto-Save Hook (`src/hooks/useAutoSave.ts`)

```typescript
import { useEffect, useRef, useCallback } from 'react';
import { useUpdateProgress } from './useSessions';

interface UseAutoSaveOptions {
  sessionId: string;
  intervalMs?: number;
  enabled?: boolean;
}

interface ProgressData {
  currentWordIndex: number;
  lastKnownPercent: number;
  targetWpm?: number;
  rampEnabled?: boolean;
}

export function useAutoSave({ sessionId, intervalMs = 10000, enabled = true }: UseAutoSaveOptions) {
  const updateProgress = useUpdateProgress();
  const lastSavedRef = useRef<ProgressData | null>(null);
  const pendingRef = useRef<ProgressData | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Save progress immediately.
   */
  const saveNow = useCallback(
    async (data: ProgressData) => {
      // Skip if same as last save
      if (
        lastSavedRef.current &&
        lastSavedRef.current.currentWordIndex === data.currentWordIndex &&
        lastSavedRef.current.lastKnownPercent === data.lastKnownPercent
      ) {
        return;
      }

      try {
        await updateProgress.mutateAsync({
          sessionId,
          data: {
            current_word_index: data.currentWordIndex,
            last_known_percent: data.lastKnownPercent,
            target_wpm: data.targetWpm,
            ramp_enabled: data.rampEnabled,
          },
        });
        lastSavedRef.current = data;
        pendingRef.current = null;
      } catch (e) {
        console.error('Failed to save progress:', e);
        // Keep pending for retry
        pendingRef.current = data;
      }
    },
    [sessionId, updateProgress]
  );

  /**
   * Queue progress for periodic save.
   */
  const queueSave = useCallback((data: ProgressData) => {
    pendingRef.current = data;
  }, []);

  /**
   * Flush any pending saves immediately.
   */
  const flush = useCallback(async () => {
    if (pendingRef.current) {
      await saveNow(pendingRef.current);
    }
  }, [saveNow]);

  // Set up periodic save timer
  useEffect(() => {
    if (!enabled) {
      return;
    }

    timerRef.current = setInterval(() => {
      if (pendingRef.current) {
        saveNow(pendingRef.current);
      }
    }, intervalMs);

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [enabled, intervalMs, saveNow]);

  return {
    saveNow,
    queueSave,
    flush,
    isSaving: updateProgress.isPending,
  };
}
```

### 3. Before Unload Hook (`src/hooks/useBeforeUnload.ts`)

```typescript
import { useEffect, useRef, useCallback } from 'react';

interface UseBeforeUnloadOptions {
  onUnload: () => void | Promise<void>;
  enabled?: boolean;
  message?: string;
}

export function useBeforeUnload({
  onUnload,
  enabled = true,
  message = 'You have unsaved progress. Are you sure you want to leave?',
}: UseBeforeUnloadOptions) {
  const onUnloadRef = useRef(onUnload);

  // Keep ref updated
  useEffect(() => {
    onUnloadRef.current = onUnload;
  }, [onUnload]);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      // Try to save
      onUnloadRef.current();

      // Show confirmation dialog
      e.preventDefault();
      e.returnValue = message;
      return message;
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'hidden') {
        // Page is being hidden, try to save
        onUnloadRef.current();
      }
    };

    const handlePageHide = () => {
      onUnloadRef.current();
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('pagehide', handlePageHide);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('pagehide', handlePageHide);
    };
  }, [enabled, message]);
}
```

### 4. Session Card (`src/components/sessions/SessionCard.tsx`)

```typescript
import { formatDistanceToNow } from 'date-fns'
import { Book, Trash2, Play } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import type { SessionListItem } from '@/lib/api/types'

interface SessionCardProps {
  session: SessionListItem
  onContinue: (session: SessionListItem) => void
  onDelete: (sessionId: string) => void
}

export function SessionCard({ session, onContinue, onDelete }: SessionCardProps) {
  const timeAgo = formatDistanceToNow(new Date(session.updated_at), {
    addSuffix: true,
  })

  return (
    <Card className="hover:bg-card/80 transition-colors">
      <CardContent className="p-4">
        <div className="flex items-start gap-4">
          {/* Icon */}
          <div className="p-2 bg-primary/10 rounded-lg">
            <Book className="h-5 w-5 text-primary" />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <h3 className="font-medium truncate">{session.document_title}</h3>

            <div className="mt-2 space-y-1">
              <Progress value={session.last_known_percent} className="h-2" />
              <div className="flex justify-between text-sm text-muted-foreground">
                <span>{session.last_known_percent.toFixed(1)}% complete</span>
                <span>{timeAgo}</span>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onDelete(session.id)}
              className="h-8 w-8 text-muted-foreground hover:text-destructive"
            >
              <Trash2 className="h-4 w-4" />
            </Button>

            <Button onClick={() => onContinue(session)} size="sm">
              <Play className="h-4 w-4 mr-1" />
              Continue
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
```

### 5. Recent Sessions List (`src/components/sessions/RecentSessions.tsx`)

```typescript
import { useNavigate } from '@tanstack/react-router'
import { Clock, BookOpen } from 'lucide-react'
import { SessionCard } from './SessionCard'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { useRecentSessions, useDeleteSession } from '@/hooks/useSessions'
import { useAppStore } from '@/stores/appStore'
import type { SessionListItem } from '@/lib/api/types'

export function RecentSessions() {
  const navigate = useNavigate()
  const { data: sessions, isLoading, error } = useRecentSessions(7)
  const deleteSession = useDeleteSession()
  const { setCurrentDocument, setCurrentSession, enterReaderMode } = useAppStore()

  const handleContinue = (session: SessionListItem) => {
    setCurrentDocument(session.document_id)
    setCurrentSession(session.id)
    enterReaderMode()

    navigate({
      to: '/deepread/$documentId',
      params: { documentId: session.document_id },
      search: {
        reading: true,
        sessionId: session.id,
      },
    })
  }

  const handleDelete = async (sessionId: string) => {
    if (confirm('Remove this session from history?')) {
      await deleteSession.mutateAsync(sessionId)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <LoadingSpinner />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Failed to load recent sessions
      </div>
    )
  }

  if (!sessions || sessions.length === 0) {
    return (
      <div className="text-center py-8 space-y-2">
        <BookOpen className="h-12 w-12 mx-auto text-muted-foreground/50" />
        <p className="text-muted-foreground">No recent reading sessions</p>
        <p className="text-sm text-muted-foreground/70">
          Import a document above to start speed reading
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-muted-foreground">
        <Clock className="h-4 w-4" />
        <h2 className="font-medium">Recent Sessions</h2>
        <span className="text-sm">({sessions.length})</span>
      </div>

      <div className="space-y-3">
        {sessions.map((session) => (
          <SessionCard
            key={session.id}
            session={session}
            onContinue={handleContinue}
            onDelete={handleDelete}
          />
        ))}
      </div>
    </div>
  )
}
```

### 6. Continue Reading Button (`src/components/sessions/ContinueReading.tsx`)

```typescript
import { useNavigate } from '@tanstack/react-router'
import { Play, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useLatestSessionForDocument } from '@/hooks/useSessions'
import { useAppStore } from '@/stores/appStore'

interface ContinueReadingProps {
  documentId: string
  onStartNew: () => void
}

export function ContinueReading({ documentId, onStartNew }: ContinueReadingProps) {
  const navigate = useNavigate()
  const { data: session, isLoading } = useLatestSessionForDocument(documentId)
  const { setCurrentDocument, setCurrentSession, enterReaderMode } = useAppStore()

  const handleContinue = () => {
    if (!session) return

    setCurrentDocument(documentId)
    setCurrentSession(session.id)
    enterReaderMode()

    navigate({
      to: '/deepread/$documentId',
      params: { documentId },
      search: {
        reading: true,
        sessionId: session.id,
      },
    })
  }

  if (isLoading) {
    return null
  }

  if (!session) {
    return (
      <Button onClick={onStartNew} size="lg">
        <Play className="h-5 w-5 mr-2" />
        Start Reading
      </Button>
    )
  }

  return (
    <div className="flex items-center gap-3">
      <Button onClick={handleContinue} size="lg">
        <Play className="h-5 w-5 mr-2" />
        Continue ({session.last_known_percent.toFixed(0)}%)
      </Button>

      <Button onClick={onStartNew} variant="outline" size="lg">
        <RotateCcw className="h-4 w-4 mr-2" />
        Start Over
      </Button>
    </div>
  )
}
```

### 7. Update DeepRead Index (`src/routes/deepread/index.tsx`)

```typescript
import { createFileRoute } from '@tanstack/react-router'
import { Container } from '@/components/layout/Container'
import { ImportForm } from '@/components/import/ImportForm'
import { RecentSessions } from '@/components/sessions/RecentSessions'

export const Route = createFileRoute('/deepread/')({
  component: DeepReadPage,
})

function DeepReadPage() {
  return (
    <Container className="max-w-3xl">
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl font-bold">DeepRead</h1>
          <p className="text-muted-foreground">
            Speed reading with RSVP technology. Paste text or upload a document to get started.
          </p>
        </div>

        <ImportForm />

        <RecentSessions />
      </div>
    </Container>
  )
}
```

### 8. Update Preview Controls with Continue Button

```typescript
// Update src/components/preview/PreviewControls.tsx

import { ContinueReading } from '@/components/sessions/ContinueReading'

interface PreviewControlsProps {
  documentId: string
  documentTitle: string
  selectedWordIndex: number | null
  resolvedIndex: number | null
  resolveReason: string | null
  onStartReading: () => void
  onBack: () => void
  isResolving?: boolean
}

export function PreviewControls({
  documentId,
  documentTitle,
  selectedWordIndex,
  resolvedIndex,
  resolveReason,
  onStartReading,
  onBack,
  isResolving,
}: PreviewControlsProps) {
  // ... existing code ...

  return (
    <div className="space-y-4">
      {/* ... header ... */}

      <div className="flex items-center justify-between p-4 bg-card rounded-lg border border-border">
        <div className="space-y-1">
          {/* ... position info ... */}
        </div>

        <ContinueReading
          documentId={documentId}
          onStartNew={onStartReading}
        />
      </div>
    </div>
  )
}
```

### 9. Integrate Auto-Save into Reader

```typescript
// Update src/components/reader/ReaderOverlay.tsx

import { useAutoSave } from '@/hooks/useAutoSave'
import { useBeforeUnload } from '@/hooks/useBeforeUnload'

export function ReaderOverlay({ ... }) {
  // ... existing code ...

  // Auto-save setup
  const autoSave = useAutoSave({
    sessionId,
    intervalMs: 10000,
    enabled: true,
  })

  // Queue progress updates during playback
  useEffect(() => {
    if (engine.isPlaying) {
      autoSave.queueSave({
        currentWordIndex: engine.currentWordIndex,
        lastKnownPercent: (engine.currentWordIndex / totalWords) * 100,
        targetWpm: settings.targetWpm,
        rampEnabled: settings.rampEnabled,
      })
    }
  }, [engine.currentWordIndex, engine.isPlaying])

  // Save immediately on pause
  useEffect(() => {
    if (!engine.isPlaying && engine.currentWordIndex > 0) {
      autoSave.saveNow({
        currentWordIndex: engine.currentWordIndex,
        lastKnownPercent: (engine.currentWordIndex / totalWords) * 100,
        targetWpm: settings.targetWpm,
        rampEnabled: settings.rampEnabled,
      })
    }
  }, [engine.isPlaying])

  // Handle page unload
  useBeforeUnload({
    onUnload: () => {
      autoSave.flush()
    },
    enabled: engine.currentWordIndex > 0,
  })

  // ... rest of component ...
}
```

### 10. Add date-fns Dependency

```bash
pnpm add date-fns
```

---

## Testing Requirements

### Manual Testing Checklist

- [ ] Progress auto-saves every 10 seconds
- [ ] Progress saves immediately on pause
- [ ] Progress saves when closing/refreshing page
- [ ] Recent sessions list shows on home page
- [ ] Session cards show correct title and progress
- [ ] "Continue" button resumes from saved position
- [ ] "Start Over" creates new session at beginning
- [ ] Delete button removes session from history
- [ ] Empty state shows when no sessions
- [ ] Time ago display is correct
- [ ] Progress bar on session card is accurate

### Integration Test

```typescript
// tests/e2e/session-persistence.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Session Persistence', () => {
  test('saves and resumes progress', async ({ page }) => {
    // Create and start reading
    await page.goto('/deepread');
    await page.fill('textarea', 'Word '.repeat(100));
    await page.click('text=Continue to Preview');
    await page.click('text=Start Reading');

    // Read for a bit
    await page.waitForTimeout(5000);

    // Pause and exit
    await page.keyboard.press('Escape');

    // Should see session in recent list
    await page.goto('/deepread');
    await expect(page.locator('text=Recent Sessions')).toBeVisible();

    // Click continue
    await page.click('text=Continue');

    // Should resume (not at beginning)
    // Check progress indicator is > 0
    await expect(page.locator('[data-testid="progress"]')).not.toContainText('0 /');
  });

  test('delete session removes from history', async ({ page }) => {
    // Setup: create a session first
    await page.goto('/deepread');
    await page.fill('textarea', 'Test document');
    await page.click('text=Continue to Preview');
    await page.click('text=Start Reading');
    await page.keyboard.press('Escape');

    // Go to home and find session
    await page.goto('/deepread');
    const sessionCard = page.locator('[data-testid="session-card"]').first();
    await expect(sessionCard).toBeVisible();

    // Delete
    await sessionCard.locator('button[aria-label="Delete"]').click();
    await page.click('text=OK'); // Confirm dialog

    // Session should be gone
    await expect(sessionCard).not.toBeVisible();
  });
});
```

---

## Verification Checklist

- [ ] useAutoSave saves progress at configured interval
- [ ] useAutoSave saves immediately when called
- [ ] useAutoSave skips duplicate saves
- [ ] useBeforeUnload triggers on page close
- [ ] useBeforeUnload triggers on tab switch
- [ ] RecentSessions shows sessions from last 7 days
- [ ] SessionCard displays all info correctly
- [ ] Continue button resumes from saved position
- [ ] Delete button removes session
- [ ] Empty state displays when no sessions
- [ ] Progress saves on pause
- [ ] Progress saves on exit

---

## Context for Next Session

**What exists after Session 9:**

- Auto-save progress every 10 seconds
- Save on pause and page close
- Recent sessions list on home page
- Continue reading from saved position
- Session deletion

**Session 10 will need:**

- Complete frontend and backend
- Docker configuration
- Environment variables
