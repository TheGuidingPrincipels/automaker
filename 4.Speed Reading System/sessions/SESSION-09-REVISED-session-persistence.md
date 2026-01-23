# Session 9 (REVISED): Session Persistence & History

## Overview

**Goal**: Implement auto-save progress, session resume, and recent sessions list integrated with Automaker's patterns.

**Prerequisites**:

- Session 8 (REVISED) completed
- Reader with controls working
- Backend sessions API functional

> ⚠️ **Code Organization**: Session persistence **API endpoints** are in the **Python backend** (`4.Speed Reading System/backend/app/routes/sessions.py`). Frontend hooks call these APIs. See `README.md` for details.

---

## Deliverables

| #   | Component           | Description                    |
| --- | ------------------- | ------------------------------ |
| 1   | useAutoSave         | Auto-save progress every 10s   |
| 2   | useSaveOnPause      | Save immediately when paused   |
| 3   | useSaveOnUnload     | Best-effort save on page close |
| 4   | useRecentSessions   | Query hook for recent sessions |
| 5   | RecentSessions      | Session list component         |
| 6   | SessionCard         | Individual session display     |
| 7   | DeleteSessionDialog | Confirm deletion               |

---

## File Structure

```
hooks/speed-reading/
├── use-sessions.ts                # Session query/mutation hooks
├── use-auto-save.ts               # Auto-save logic
└── use-before-unload.ts           # Unload handling

components/views/speed-reading-page/
├── components/
│   ├── recent-sessions.tsx        # Session list
│   ├── session-card.tsx           # Individual card
│   └── empty-state.tsx            # No sessions state
├── dialogs/
│   └── delete-session-dialog.tsx  # Confirm delete
```

---

## Implementation

### 1. Session Query Hooks (`hooks/speed-reading/use-sessions.ts`)

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { sessionsApi } from '@/lib/speed-reading/api';
import type { CreateSessionRequest, UpdateProgressRequest } from '@/lib/speed-reading/types';

export const sessionKeys = {
  all: ['deepread-sessions'] as const,
  recent: (days: number) => ['deepread-sessions', 'recent', days] as const,
  detail: (id: string) => ['deepread-sessions', id] as const,
  forDocument: (docId: string) => ['deepread-sessions', 'document', docId] as const,
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
    onError: (_err, { sessionId }, context) => {
      if (context?.previousSession) {
        queryClient.setQueryData(sessionKeys.detail(sessionId), context.previousSession);
      }
    },
    onSettled: () => {
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

### 2. Auto-Save Hook (`hooks/speed-reading/use-auto-save.ts`)

```typescript
import { useEffect, useRef, useCallback } from 'react';
import { useUpdateProgress } from './use-sessions';
import { useSpeedReadingStore } from '@/store/speed-reading-store';

interface UseAutoSaveOptions {
  sessionId: string;
  currentWordIndex: number;
  progress: number;
  intervalMs?: number;
  enabled?: boolean;
}

interface SaveData {
  currentWordIndex: number;
  progress: number;
}

export function useAutoSave({
  sessionId,
  currentWordIndex,
  progress,
  intervalMs = 10000,
  enabled = true,
}: UseAutoSaveOptions) {
  const updateProgress = useUpdateProgress();
  const { settings } = useSpeedReadingStore();

  const lastSavedRef = useRef<SaveData | null>(null);
  const pendingRef = useRef<SaveData | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Save progress immediately
   */
  const saveNow = useCallback(
    async (data?: SaveData) => {
      const saveData = data ?? { currentWordIndex, progress };

      // Skip if same as last save
      if (
        lastSavedRef.current &&
        lastSavedRef.current.currentWordIndex === saveData.currentWordIndex &&
        Math.abs(lastSavedRef.current.progress - saveData.progress) < 0.1
      ) {
        return;
      }

      try {
        await updateProgress.mutateAsync({
          sessionId,
          data: {
            current_word_index: saveData.currentWordIndex,
            last_known_percent: saveData.progress,
            target_wpm: settings.targetWpm,
            ramp_enabled: settings.rampEnabled,
          },
        });
        lastSavedRef.current = saveData;
        pendingRef.current = null;
      } catch (e) {
        console.error('Failed to save progress:', e);
        pendingRef.current = saveData;
      }
    },
    [sessionId, currentWordIndex, progress, settings, updateProgress]
  );

  /**
   * Queue progress for periodic save
   */
  const queueSave = useCallback(() => {
    pendingRef.current = { currentWordIndex, progress };
  }, [currentWordIndex, progress]);

  /**
   * Flush any pending saves immediately
   */
  const flush = useCallback(async () => {
    if (pendingRef.current) {
      await saveNow(pendingRef.current);
    }
  }, [saveNow]);

  // Set up periodic save timer
  useEffect(() => {
    if (!enabled) return;

    timerRef.current = setInterval(() => {
      queueSave();
      if (pendingRef.current) {
        saveNow(pendingRef.current);
      }
    }, intervalMs);

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [enabled, intervalMs, queueSave, saveNow]);

  return {
    saveNow: () => saveNow(),
    queueSave,
    flush,
    isSaving: updateProgress.isPending,
  };
}
```

### 3. Before Unload Hook (`hooks/speed-reading/use-before-unload.ts`)

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
    if (!enabled) return;

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

### 4. Recent Sessions Component (`components/recent-sessions.tsx`)

```typescript
import { useNavigate } from '@tanstack/react-router';
import { Clock, BookOpen } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { SessionCard } from './session-card';
import { useDeleteSession } from '@/hooks/speed-reading/use-sessions';
import { DeleteSessionDialog } from '../dialogs/delete-session-dialog';
import { useState } from 'react';
import type { SessionListItem } from '@/lib/speed-reading/types';

interface RecentSessionsProps {
  sessions: SessionListItem[];
  isLoading: boolean;
  onContinue: (sessionId: string, documentId: string) => void;
}

export function RecentSessions({
  sessions,
  isLoading,
  onContinue,
}: RecentSessionsProps) {
  const deleteSession = useDeleteSession();
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null);

  const handleDelete = async () => {
    if (sessionToDelete) {
      await deleteSession.mutateAsync(sessionToDelete);
      setSessionToDelete(null);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Clock className="h-4 w-4" />
          <h2 className="font-medium">Recent Sessions</h2>
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="text-center py-12 space-y-3">
        <BookOpen className="h-12 w-12 mx-auto text-muted-foreground/50" />
        <p className="text-muted-foreground">No recent reading sessions</p>
        <p className="text-sm text-muted-foreground/70">
          Import a document above to start speed reading
        </p>
      </div>
    );
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
            onContinue={() => onContinue(session.id, session.document_id)}
            onDelete={() => setSessionToDelete(session.id)}
          />
        ))}
      </div>

      <DeleteSessionDialog
        open={sessionToDelete !== null}
        onOpenChange={(open) => !open && setSessionToDelete(null)}
        onConfirm={handleDelete}
        isDeleting={deleteSession.isPending}
      />
    </div>
  );
}
```

### 5. Session Card Component (`components/session-card.tsx`)

```typescript
import { formatDistanceToNow } from 'date-fns';
import { Book, Trash2, Play } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import type { SessionListItem } from '@/lib/speed-reading/types';

interface SessionCardProps {
  session: SessionListItem;
  onContinue: () => void;
  onDelete: () => void;
}

export function SessionCard({ session, onContinue, onDelete }: SessionCardProps) {
  const timeAgo = formatDistanceToNow(new Date(session.updated_at), {
    addSuffix: true,
  });

  const wordsRead = Math.floor((session.last_known_percent / 100) * session.total_words);
  const wordsRemaining = session.total_words - wordsRead;

  return (
    <Card className="group hover:border-primary/50 hover:shadow-md transition-all">
      <CardContent className="p-4">
        <div className="flex items-start gap-4">
          {/* Icon */}
          <div className="p-2 bg-primary/10 rounded-lg group-hover:bg-primary/20 transition-colors">
            <Book className="h-5 w-5 text-primary" />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <h3 className="font-medium truncate">{session.document_title}</h3>

            <div className="mt-2 space-y-1">
              <Progress
                value={session.last_known_percent}
                className="h-2"
              />
              <div className="flex justify-between text-sm text-muted-foreground">
                <span>{session.last_known_percent.toFixed(1)}% complete</span>
                <span>{wordsRemaining.toLocaleString()} words left</span>
              </div>
            </div>

            <p className="mt-1 text-xs text-muted-foreground">{timeAgo}</p>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button
              variant="ghost"
              size="icon"
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              className="h-8 w-8 text-muted-foreground hover:text-destructive"
            >
              <Trash2 className="h-4 w-4" />
            </Button>

            <Button onClick={onContinue} size="sm">
              <Play className="h-4 w-4 mr-1" />
              Continue
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

### 6. Delete Session Dialog (`dialogs/delete-session-dialog.tsx`)

```typescript
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

interface DeleteSessionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  isDeleting?: boolean;
}

export function DeleteSessionDialog({
  open,
  onOpenChange,
  onConfirm,
  isDeleting,
}: DeleteSessionDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Remove from history?</AlertDialogTitle>
          <AlertDialogDescription>
            This will remove the reading session from your history. The document
            will still be available to read again.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            disabled={isDeleting}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {isDeleting ? 'Removing...' : 'Remove'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
```

### 7. Integrate Auto-Save into Reader

Update the reader page to use the hooks:

```typescript
// In speed-reading-reader/index.tsx

import { useAutoSave } from '@/hooks/speed-reading/use-auto-save';
import { useBeforeUnload } from '@/hooks/speed-reading/use-before-unload';

export function SpeedReadingReader() {
  // ... existing code ...

  const autoSave = useAutoSave({
    sessionId,
    currentWordIndex: engine.currentWordIndex,
    progress: engine.progress,
    intervalMs: 10000,
    enabled: !!session,
  });

  // Save on pause
  useEffect(() => {
    if (!engine.isPlaying && engine.currentWordIndex > 0) {
      autoSave.saveNow();
    }
  }, [engine.isPlaying, engine.currentWordIndex, autoSave]);

  // Save on unload
  useBeforeUnload({
    onUnload: () => autoSave.flush(),
    enabled: engine.currentWordIndex > 0,
  });

  const handleExit = useCallback(async () => {
    engine.pause();
    await autoSave.flush();
    navigate({ to: '/speed-reading' });
  }, [engine, autoSave, navigate]);

  // ... rest of component ...
}
```

### 8. Update Main Page with Navigation

```typescript
// In speed-reading-page/index.tsx

const handleContinue = (sessionId: string, documentId: string) => {
  navigate({
    to: '/speed-reading/reader/$sessionId',
    params: { sessionId },
  });
};

const handlePreview = (documentId: string) => {
  navigate({
    to: '/speed-reading/preview/$documentId',
    params: { documentId },
  });
};

// In return:
<RecentSessions
  sessions={sessions ?? []}
  isLoading={isLoading}
  onContinue={handleContinue}
/>
```

---

## Dependencies

```bash
# In 1.apps/ui/
pnpm add date-fns
```

---

## Verification Checklist

### Auto-Save

- [ ] Progress saves every 10 seconds during playback
- [ ] Progress saves immediately on pause
- [ ] Progress saves on page close/refresh (best-effort)
- [ ] Progress saves on tab switch/hide
- [ ] Duplicate saves are skipped
- [ ] Save errors are handled gracefully

### Recent Sessions

- [ ] Sessions list shows on main page
- [ ] Sessions sorted by most recent
- [ ] Session card shows correct title
- [ ] Session card shows progress bar
- [ ] Session card shows time ago
- [ ] Session card shows words remaining
- [ ] Empty state displays when no sessions

### Continue Reading

- [ ] Continue button resumes from saved position
- [ ] Delete button removes session from history
- [ ] Delete confirmation dialog works
- [ ] Navigation to reader works

---

## E2E Test Scenario

```typescript
// tests/e2e/speed-reading-session.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Speed Reading Session Persistence', () => {
  test('saves and resumes progress', async ({ page }) => {
    // 1. Navigate and import
    await page.goto('/speed-reading');
    await page.click('text=Import New Document');
    await page.fill('textarea', 'Word '.repeat(100));
    await page.click('text=Continue to Preview');

    // 2. Start reading
    await page.click('text=Start Reading');

    // 3. Read for a bit
    await page.waitForTimeout(5000);

    // 4. Pause and exit
    await page.keyboard.press('Escape');

    // 5. Should see session in recent list
    await page.goto('/speed-reading');
    await expect(page.locator('text=Recent Sessions')).toBeVisible();

    // 6. Click continue
    await page.click('text=Continue');

    // 7. Should resume (not at beginning)
    const progress = await page.locator('[data-testid="progress"]');
    await expect(progress).not.toContainText('0 /');
  });

  test('delete session removes from history', async ({ page }) => {
    // Setup: create a session first
    await page.goto('/speed-reading');
    await page.click('text=Import New Document');
    await page.fill('textarea', 'Test document');
    await page.click('text=Continue to Preview');
    await page.click('text=Start Reading');
    await page.keyboard.press('Escape');

    // Go to home and find session
    await page.goto('/speed-reading');
    const sessionCard = page.locator('[data-testid="session-card"]').first();
    await expect(sessionCard).toBeVisible();

    // Hover and click delete
    await sessionCard.hover();
    await sessionCard.locator('button[aria-label="Delete"]').click();

    // Confirm
    await page.click('text=Remove');

    // Session should be gone
    await expect(sessionCard).not.toBeVisible();
  });
});
```

---

## Summary: What's Complete After Session 9

After completing Sessions 5-9 (REVISED), you have:

1. ✅ **Integrated Speed Reading page** in Automaker sidebar
2. ✅ **Keyboard shortcut** (Shift+R) for navigation
3. ✅ **Import page** with text paste and file upload
4. ✅ **Preview page** with clickable words
5. ✅ **Reader engine** with ORP display
6. ✅ **Ramp mode** for gradual speed increase
7. ✅ **Time-based rewind** (10/15/30s)
8. ✅ **Auto-hiding controls** overlay
9. ✅ **Full keyboard shortcuts**
10. ✅ **Auto-save progress** every 10s
11. ✅ **Save on pause/unload**
12. ✅ **Recent sessions list**
13. ✅ **Continue reading** from saved position

---

## Session 10 (Deferred): Deployment

Session 10 covers deployment to Hetzner with:

- Docker configuration
- Docker Compose for production
- SSL/TLS setup
- Environment configuration
- Database backups

This is deferred until local testing is complete.
