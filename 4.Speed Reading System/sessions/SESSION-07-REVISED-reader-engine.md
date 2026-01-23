# Session 7 (REVISED): Reader Engine

## Overview

**Goal**: Implement the core RSVP playback engine with ORP alignment, token caching, ramp mode, and time-based rewind.

**Prerequisites**:

- Session 6 (REVISED) completed
- Import and preview pages working
- Python backend returning tokens

> ⚠️ **Code Organization**: The playback engine is **frontend-only** (timing loop, caching). Token generation and ORP calculation happens in the **Python backend** (`4.Speed Reading System/backend/`). See `README.md` for details.

---

## Deliverables

| #   | Component          | Description                           |
| --- | ------------------ | ------------------------------------- |
| 1   | usePlaybackEngine  | Core timing loop with play/pause/seek |
| 2   | useTokenCache      | Token chunk prefetching               |
| 3   | usePlaybackHistory | Ring buffer for rewind                |
| 4   | useRamp            | WPM ramp calculation                  |
| 5   | WordDisplay        | ORP-aligned word rendering            |
| 6   | ReaderOverlay      | Fullscreen dark reader UI             |

---

## File Structure

```
components/views/speed-reading-reader/
├── index.tsx                      # Main reader page
├── components/
│   ├── reader-overlay.tsx         # Fullscreen container
│   ├── word-display.tsx           # ORP-aligned word
│   ├── orp-text.tsx               # Text with ORP highlight
│   └── reader-progress.tsx        # Progress indicator

hooks/speed-reading/
├── use-playback-engine.ts         # Core timing loop
├── use-token-cache.ts             # Token prefetching
├── use-playback-history.ts        # Ring buffer for rewind
└── use-ramp.ts                    # WPM ramp calculation

lib/speed-reading/
├── timing.ts                      # Duration calculations
└── ramp.ts                        # Ramp formula
```

---

## Implementation

### 1. Timing Utilities (`lib/speed-reading/timing.ts`)

```typescript
import type { Token } from './types';

/**
 * Calculate base word duration from WPM
 */
export function getBaseDuration(wpm: number): number {
  return 60000 / wpm; // milliseconds per word
}

/**
 * Calculate actual word duration with delay multiplier
 */
export function getWordDuration(wpm: number, delayMultiplier: number): number {
  return getBaseDuration(wpm) * delayMultiplier;
}

/**
 * Calculate break duration before a word
 * - paragraph: 3.0x base
 * - heading: 3.5x base
 */
export function getBreakDuration(wpm: number, breakType: 'paragraph' | 'heading' | null): number {
  if (!breakType) return 0;

  const base = getBaseDuration(wpm);
  const multiplier = breakType === 'heading' ? 3.5 : 3.0;
  return base * multiplier;
}

/**
 * Calculate total display time for a token (including pre-break)
 */
export function getTotalTokenDuration(token: Token, wpm: number): number {
  const breakDuration = getBreakDuration(wpm, token.break_before);
  const wordDuration = getWordDuration(wpm, token.delay_multiplier_after);
  return breakDuration + wordDuration;
}
```

### 2. Ramp Calculation (`lib/speed-reading/ramp.ts`)

```typescript
/**
 * Calculate current WPM based on ramp progress
 *
 * Linear ramp from startWpm to targetWpm over rampSeconds
 */
export function calculateRampWpm(
  targetWpm: number,
  startWpm: number,
  rampSeconds: number,
  elapsedSeconds: number
): number {
  if (rampSeconds <= 0) return targetWpm;

  const progress = Math.min(elapsedSeconds / rampSeconds, 1);
  return Math.round(startWpm + (targetWpm - startWpm) * progress);
}

/**
 * Get start WPM for ramp mode (50% of target, minimum 100)
 */
export function getStartWpm(targetWpm: number): number {
  return Math.max(100, Math.round(targetWpm * 0.5));
}
```

### 3. Token Cache Hook (`hooks/speed-reading/use-token-cache.ts`)

```typescript
import { useState, useCallback, useEffect, useRef } from 'react';
import { documentsApi } from '@/lib/speed-reading/api';
import type { Token, TokenChunk } from '@/lib/speed-reading/types';

const CHUNK_SIZE = 500;
const PREFETCH_THRESHOLD = 100; // Prefetch when this close to chunk boundary

interface TokenCacheState {
  chunks: Map<number, Token[]>; // Map of startIndex -> tokens
  totalWords: number;
}

interface UseTokenCacheOptions {
  documentId: string;
  totalWords: number;
}

export function useTokenCache({ documentId, totalWords }: UseTokenCacheOptions) {
  const [state, setState] = useState<TokenCacheState>({
    chunks: new Map(),
    totalWords,
  });
  const [isLoading, setIsLoading] = useState(false);
  const fetchingRef = useRef<Set<number>>(new Set());

  /**
   * Get the chunk start index for a given word index
   */
  const getChunkStart = useCallback((wordIndex: number): number => {
    return Math.floor(wordIndex / CHUNK_SIZE) * CHUNK_SIZE;
  }, []);

  /**
   * Fetch a chunk of tokens
   */
  const fetchChunk = useCallback(
    async (startIndex: number) => {
      // Don't fetch if already fetching or cached
      if (fetchingRef.current.has(startIndex) || state.chunks.has(startIndex)) {
        return;
      }

      fetchingRef.current.add(startIndex);
      setIsLoading(true);

      try {
        const chunk = await documentsApi.getTokens(documentId, startIndex, CHUNK_SIZE);

        setState((prev) => {
          const newChunks = new Map(prev.chunks);
          newChunks.set(startIndex, chunk.tokens);
          return { ...prev, chunks: newChunks };
        });
      } catch (error) {
        console.error('Failed to fetch token chunk:', error);
      } finally {
        fetchingRef.current.delete(startIndex);
        setIsLoading(false);
      }
    },
    [documentId, state.chunks]
  );

  /**
   * Ensure tokens are loaded around a given index
   */
  const ensureTokensLoaded = useCallback(
    async (wordIndex: number) => {
      const currentChunk = getChunkStart(wordIndex);
      const prevChunk = currentChunk - CHUNK_SIZE;
      const nextChunk = currentChunk + CHUNK_SIZE;

      // Fetch current chunk if needed
      if (!state.chunks.has(currentChunk) && currentChunk >= 0) {
        await fetchChunk(currentChunk);
      }

      // Prefetch next chunk
      if (!state.chunks.has(nextChunk) && nextChunk < totalWords) {
        fetchChunk(nextChunk);
      }

      // Fetch previous chunk for rewind
      if (!state.chunks.has(prevChunk) && prevChunk >= 0) {
        fetchChunk(prevChunk);
      }
    },
    [getChunkStart, state.chunks, fetchChunk, totalWords]
  );

  /**
   * Get a token by index (returns null if not loaded)
   */
  const getToken = useCallback(
    (wordIndex: number): Token | null => {
      const chunkStart = getChunkStart(wordIndex);
      const chunk = state.chunks.get(chunkStart);

      if (!chunk) return null;

      const localIndex = wordIndex - chunkStart;
      return chunk[localIndex] ?? null;
    },
    [getChunkStart, state.chunks]
  );

  /**
   * Get multiple tokens as array
   */
  const getTokenRange = useCallback(
    (startIndex: number, count: number): Token[] => {
      const tokens: Token[] = [];

      for (let i = 0; i < count; i++) {
        const token = getToken(startIndex + i);
        if (token) tokens.push(token);
      }

      return tokens;
    },
    [getToken]
  );

  return {
    getToken,
    getTokenRange,
    ensureTokensLoaded,
    isLoading,
    cachedChunks: state.chunks.size,
  };
}
```

### 4. Playback History Hook (`hooks/speed-reading/use-playback-history.ts`)

```typescript
import { useRef, useCallback } from 'react';

interface HistoryEntry {
  wordIndex: number;
  elapsedMs: number;
}

const MAX_HISTORY_ENTRIES = 1000; // About 3-5 minutes at 200-300 WPM

export function usePlaybackHistory() {
  const historyRef = useRef<HistoryEntry[]>([]);

  /**
   * Record a word display in history
   */
  const recordWord = useCallback((wordIndex: number, elapsedMs: number) => {
    historyRef.current.push({ wordIndex, elapsedMs });

    // Trim old entries
    if (historyRef.current.length > MAX_HISTORY_ENTRIES) {
      historyRef.current = historyRef.current.slice(-MAX_HISTORY_ENTRIES);
    }
  }, []);

  /**
   * Find the word index to rewind to (N seconds back)
   */
  const getRewindIndex = useCallback((seconds: number): number | null => {
    const history = historyRef.current;
    if (history.length === 0) return null;

    const currentElapsed = history[history.length - 1].elapsedMs;
    const targetElapsed = currentElapsed - seconds * 1000;

    // Binary search for closest entry
    let left = 0;
    let right = history.length - 1;
    let result = 0;

    while (left <= right) {
      const mid = Math.floor((left + right) / 2);

      if (history[mid].elapsedMs <= targetElapsed) {
        result = mid;
        left = mid + 1;
      } else {
        right = mid - 1;
      }
    }

    return history[result]?.wordIndex ?? 0;
  }, []);

  /**
   * Clear history (on session reset)
   */
  const clearHistory = useCallback(() => {
    historyRef.current = [];
  }, []);

  /**
   * Get current elapsed time
   */
  const getCurrentElapsed = useCallback((): number => {
    const history = historyRef.current;
    if (history.length === 0) return 0;
    return history[history.length - 1].elapsedMs;
  }, []);

  return {
    recordWord,
    getRewindIndex,
    clearHistory,
    getCurrentElapsed,
    historyLength: historyRef.current.length,
  };
}
```

### 5. Playback Engine Hook (`hooks/speed-reading/use-playback-engine.ts`)

```typescript
import { useState, useRef, useCallback, useEffect } from 'react';
import { useTokenCache } from './use-token-cache';
import { usePlaybackHistory } from './use-playback-history';
import { useRamp } from './use-ramp';
import { getWordDuration, getBreakDuration } from '@/lib/speed-reading/timing';
import type { Token } from '@/lib/speed-reading/types';

interface PlaybackState {
  isPlaying: boolean;
  currentWordIndex: number;
  currentToken: Token | null;
  effectiveWpm: number;
  isInBreak: boolean;
}

interface UsePlaybackEngineOptions {
  documentId: string;
  totalWords: number;
  initialWordIndex: number;
  targetWpm: number;
  rampEnabled: boolean;
  rampSeconds: number;
}

export function usePlaybackEngine({
  documentId,
  totalWords,
  initialWordIndex,
  targetWpm,
  rampEnabled,
  rampSeconds,
}: UsePlaybackEngineOptions) {
  const [state, setState] = useState<PlaybackState>({
    isPlaying: false,
    currentWordIndex: initialWordIndex,
    currentToken: null,
    effectiveWpm: targetWpm,
    isInBreak: false,
  });

  const tokenCache = useTokenCache({ documentId, totalWords });
  const history = usePlaybackHistory();
  const { getCurrentWpm, resetRamp } = useRamp({
    targetWpm,
    rampEnabled,
    rampSeconds,
    isPlaying: state.isPlaying,
  });

  // Refs for timing loop
  const frameRef = useRef<number | null>(null);
  const lastFrameTimeRef = useRef<number>(0);
  const elapsedRef = useRef<number>(0);
  const wordStartTimeRef = useRef<number>(0);
  const breakEndTimeRef = useRef<number>(0);

  /**
   * Load token for current index
   */
  const loadCurrentToken = useCallback(async () => {
    await tokenCache.ensureTokensLoaded(state.currentWordIndex);
    const token = tokenCache.getToken(state.currentWordIndex);

    setState((prev) => ({
      ...prev,
      currentToken: token,
    }));
  }, [state.currentWordIndex, tokenCache]);

  // Load token when index changes
  useEffect(() => {
    loadCurrentToken();
  }, [loadCurrentToken]);

  /**
   * Main timing loop
   */
  const tick = useCallback(
    (timestamp: number) => {
      if (!state.isPlaying || !state.currentToken) {
        frameRef.current = requestAnimationFrame(tick);
        return;
      }

      // Calculate delta
      const deltaMs = timestamp - lastFrameTimeRef.current;
      lastFrameTimeRef.current = timestamp;
      elapsedRef.current += deltaMs;

      // Get current WPM (may be ramping)
      const currentWpm = getCurrentWpm();
      setState((prev) => ({ ...prev, effectiveWpm: currentWpm }));

      // Handle break before word
      if (state.isInBreak) {
        const breakDuration = getBreakDuration(currentWpm, state.currentToken.break_before);

        if (timestamp >= breakEndTimeRef.current) {
          // Break finished, start word display
          setState((prev) => ({ ...prev, isInBreak: false }));
          wordStartTimeRef.current = timestamp;
        }
      } else {
        // Display word
        const wordDuration = getWordDuration(currentWpm, state.currentToken.delay_multiplier_after);
        const wordElapsed = timestamp - wordStartTimeRef.current;

        if (wordElapsed >= wordDuration) {
          // Record word in history
          history.recordWord(state.currentWordIndex, elapsedRef.current);

          // Move to next word
          const nextIndex = state.currentWordIndex + 1;

          if (nextIndex >= totalWords) {
            // End of document
            setState((prev) => ({ ...prev, isPlaying: false }));
            return;
          }

          // Load next token
          const nextToken = tokenCache.getToken(nextIndex);

          if (nextToken) {
            // Check for break before next word
            if (nextToken.break_before) {
              const breakDuration = getBreakDuration(currentWpm, nextToken.break_before);
              breakEndTimeRef.current = timestamp + breakDuration;

              setState((prev) => ({
                ...prev,
                currentWordIndex: nextIndex,
                currentToken: nextToken,
                isInBreak: true,
              }));
            } else {
              wordStartTimeRef.current = timestamp;

              setState((prev) => ({
                ...prev,
                currentWordIndex: nextIndex,
                currentToken: nextToken,
              }));
            }

            // Prefetch ahead
            tokenCache.ensureTokensLoaded(nextIndex + 50);
          }
        }
      }

      frameRef.current = requestAnimationFrame(tick);
    },
    [state, getCurrentWpm, history, tokenCache, totalWords]
  );

  /**
   * Start playback
   */
  const play = useCallback(() => {
    if (state.isPlaying) return;

    lastFrameTimeRef.current = performance.now();
    wordStartTimeRef.current = performance.now();

    setState((prev) => ({ ...prev, isPlaying: true }));
    frameRef.current = requestAnimationFrame(tick);
  }, [state.isPlaying, tick]);

  /**
   * Pause playback
   */
  const pause = useCallback(() => {
    if (!state.isPlaying) return;

    if (frameRef.current) {
      cancelAnimationFrame(frameRef.current);
      frameRef.current = null;
    }

    setState((prev) => ({ ...prev, isPlaying: false }));
  }, [state.isPlaying]);

  /**
   * Toggle play/pause
   */
  const toggle = useCallback(() => {
    if (state.isPlaying) {
      pause();
    } else {
      play();
    }
  }, [state.isPlaying, play, pause]);

  /**
   * Seek to specific word index
   */
  const seekTo = useCallback(
    async (wordIndex: number) => {
      const clampedIndex = Math.max(0, Math.min(wordIndex, totalWords - 1));

      await tokenCache.ensureTokensLoaded(clampedIndex);
      const token = tokenCache.getToken(clampedIndex);

      wordStartTimeRef.current = performance.now();

      setState((prev) => ({
        ...prev,
        currentWordIndex: clampedIndex,
        currentToken: token,
        isInBreak: false,
      }));
    },
    [totalWords, tokenCache]
  );

  /**
   * Rewind by N seconds
   */
  const rewind = useCallback(
    async (seconds: number) => {
      const targetIndex = history.getRewindIndex(seconds);

      if (targetIndex !== null) {
        await seekTo(targetIndex);
      }
    },
    [history, seekTo]
  );

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
      }
    };
  }, []);

  return {
    // State
    isPlaying: state.isPlaying,
    currentWordIndex: state.currentWordIndex,
    currentToken: state.currentToken,
    effectiveWpm: state.effectiveWpm,
    isInBreak: state.isInBreak,
    progress: (state.currentWordIndex / totalWords) * 100,

    // Actions
    play,
    pause,
    toggle,
    seekTo,
    rewind,

    // Cache info
    isLoadingTokens: tokenCache.isLoading,
  };
}
```

### 6. Word Display Component

```typescript
// components/word-display.tsx
import { useMemo } from 'react';
import type { Token } from '@/lib/speed-reading/types';

interface WordDisplayProps {
  token: Token | null;
  isInBreak: boolean;
}

export function WordDisplay({ token, isInBreak }: WordDisplayProps) {
  if (isInBreak || !token) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="w-2 h-2 rounded-full bg-muted-foreground/30" />
      </div>
    );
  }

  const { before, orp, after } = useMemo(() => {
    const text = token.display_text;
    const orpIndex = token.orp_index_display;

    return {
      before: text.slice(0, orpIndex),
      orp: text[orpIndex] || '',
      after: text.slice(orpIndex + 1),
    };
  }, [token]);

  return (
    <div className="flex items-center justify-center h-full">
      <div className="relative font-mono text-5xl md:text-7xl tracking-tight">
        {/* ORP alignment marker */}
        <div className="absolute left-1/2 -translate-x-1/2 -top-4 w-0 h-0 border-l-8 border-r-8 border-t-8 border-transparent border-t-primary/50" />

        {/* Word with ORP highlight */}
        <span className="text-muted-foreground/70">{before}</span>
        <span className="text-primary font-bold">{orp}</span>
        <span className="text-foreground">{after}</span>

        {/* Bottom alignment marker */}
        <div className="absolute left-1/2 -translate-x-1/2 -bottom-4 w-0 h-0 border-l-8 border-r-8 border-b-8 border-transparent border-b-primary/50" />
      </div>
    </div>
  );
}
```

### 7. Reader Page (`speed-reading-reader/index.tsx`)

```typescript
import { useEffect, useCallback } from 'react';
import { useNavigate, useParams } from '@tanstack/react-router';
import { useSession } from '@/hooks/speed-reading/use-sessions';
import { usePlaybackEngine } from '@/hooks/speed-reading/use-playback-engine';
import { useAutoSave } from '@/hooks/speed-reading/use-auto-save';
import { WordDisplay } from './components/word-display';
import { ReaderControls } from './components/reader-controls';
import { ReaderProgress } from './components/reader-progress';

export function SpeedReadingReader() {
  const navigate = useNavigate();
  const { sessionId } = useParams({ from: '/speed-reading/reader/$sessionId' });

  const { data: session, isLoading: sessionLoading } = useSession(sessionId);

  const engine = usePlaybackEngine({
    documentId: session?.document_id ?? '',
    totalWords: session?.total_words ?? 0,
    initialWordIndex: session?.current_word_index ?? 0,
    targetWpm: session?.target_wpm ?? 300,
    rampEnabled: session?.ramp_enabled ?? true,
    rampSeconds: session?.ramp_seconds ?? 30,
  });

  const autoSave = useAutoSave({
    sessionId,
    currentWordIndex: engine.currentWordIndex,
    progress: engine.progress,
    enabled: !!session,
  });

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't capture if in input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      switch (e.key) {
        case ' ':
          e.preventDefault();
          engine.toggle();
          break;
        case 'ArrowLeft':
          e.preventDefault();
          engine.rewind(e.shiftKey ? 30 : 10);
          break;
        case 'Escape':
          e.preventDefault();
          handleExit();
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [engine]);

  const handleExit = useCallback(async () => {
    engine.pause();
    await autoSave.saveNow();
    navigate({ to: '/speed-reading' });
  }, [engine, autoSave, navigate]);

  if (sessionLoading || !session) {
    return (
      <div className="fixed inset-0 bg-black flex items-center justify-center">
        <div className="text-white">Loading...</div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black text-white flex flex-col">
      {/* Word Display Area */}
      <div className="flex-1 flex items-center justify-center p-8">
        <WordDisplay token={engine.currentToken} isInBreak={engine.isInBreak} />
      </div>

      {/* Progress Bar */}
      <ReaderProgress
        progress={engine.progress}
        currentIndex={engine.currentWordIndex}
        totalWords={session.total_words}
      />

      {/* Controls Overlay (auto-hides) */}
      <ReaderControls
        isPlaying={engine.isPlaying}
        effectiveWpm={engine.effectiveWpm}
        onPlayPause={engine.toggle}
        onRewind={(seconds) => engine.rewind(seconds)}
        onExit={handleExit}
      />
    </div>
  );
}
```

---

## Verification Checklist

### Playback Engine

- [ ] Play starts word display loop
- [ ] Pause stops immediately
- [ ] Toggle works correctly
- [ ] Word timing matches WPM setting
- [ ] Delay multipliers work (longer pause after periods)
- [ ] Break pauses work (paragraph, heading)
- [ ] End of document stops playback

### Token Cache

- [ ] Initial chunk loads on start
- [ ] Prefetch loads next chunk before needed
- [ ] Previous chunk loads for rewind
- [ ] No duplicate fetches
- [ ] Loading indicator shows during fetch

### Ramp Mode

- [ ] Start WPM is 50% of target
- [ ] WPM increases linearly over ramp duration
- [ ] WPM indicator shows current value
- [ ] Ramp completes at target WPM

### Rewind

- [ ] 10s rewind jumps back correctly
- [ ] 30s rewind jumps back correctly
- [ ] Rewind respects history (not just word count)
- [ ] Rewind near start goes to beginning

### ORP Display

- [ ] ORP character is highlighted
- [ ] Alignment markers visible
- [ ] Break shows blank indicator
- [ ] Font is readable at large size

---

## Next: Session 8 - Reader Controls

Session 8 adds:

- Auto-hiding control overlay
- WPM adjustment (+/- 25)
- Ramp toggle and settings
- Full keyboard shortcut support
- Progress scrubber/seeking
