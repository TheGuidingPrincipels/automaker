# Session 7: Reader Engine

## Overview

**Duration**: ~4 hours
**Goal**: Build the core RSVP reader with ORP-aligned word display, playback timing loop, token caching, ramp function, and playback history buffer.

**Deliverable**: Functional reader that displays words one at a time with correct timing and ORP alignment.

---

## Prerequisites

- Session 6 completed (preview and session creation)
- Backend running with token endpoints
- Session created with start position

---

## Objectives & Acceptance Criteria

| #   | Objective               | Acceptance Criteria                               |
| --- | ----------------------- | ------------------------------------------------- |
| 1   | ReaderOverlay component | Full-screen black background                      |
| 2   | ORP word display        | Words aligned at optimal recognition point        |
| 3   | Timing loop             | requestAnimationFrame-based scheduling            |
| 4   | Token cache             | Prefetch chunks around current position           |
| 5   | Ramp function           | WPM increases from 50% to target over ramp period |
| 6   | Delay multipliers       | Punctuation and long words pause longer           |
| 7   | Paragraph breaks        | Blank frame before paragraph/heading starts       |
| 8   | History buffer          | Records playback for time-based rewind            |

---

## File Structure

```
frontend/src/
├── components/
│   └── reader/
│       ├── ReaderOverlay.tsx       # Main reader container
│       ├── WordDisplay.tsx         # ORP-aligned word rendering
│       ├── ORPText.tsx             # Text with ORP highlight
│       └── BlankFrame.tsx          # Blank frame for breaks
├── hooks/
│   ├── usePlaybackEngine.ts        # Main timing loop
│   ├── useTokenCache.ts            # Token prefetching
│   ├── usePlaybackHistory.ts       # History ring buffer
│   └── useRamp.ts                  # WPM ramp calculation
└── lib/
    └── playback/
        ├── timing.ts               # Duration calculations
        ├── ramp.ts                 # Ramp formula
        └── types.ts                # Playback types
```

---

## Implementation Details

### 1. Playback Types (`src/lib/playback/types.ts`)

```typescript
import type { Token } from '@/lib/api/types';

export interface PlaybackState {
  isPlaying: boolean;
  isPaused: boolean;
  currentToken: Token | null;
  currentWordIndex: number;
  elapsedReadingTime: number; // ms, excludes paused time
  totalWords: number;
}

export interface PlaybackHistoryEntry {
  wordIndex: number;
  elapsedTimeAtStart: number; // When this word started displaying
  timestamp: number; // Real timestamp for debugging
}

export interface TimingConfig {
  targetWpm: number;
  rampEnabled: boolean;
  rampSeconds: number;
  rampStartWpm: number;
}

export interface BreakConfig {
  paragraphMultiplier: number; // 3.0x base duration
  headingMultiplier: number; // 3.5x base duration
}

export const DEFAULT_BREAK_CONFIG: BreakConfig = {
  paragraphMultiplier: 3.0,
  headingMultiplier: 3.5,
};
```

### 2. Timing Calculations (`src/lib/playback/timing.ts`)

```typescript
import type { Token } from '@/lib/api/types';
import type { TimingConfig, BreakConfig } from './types';

/**
 * Calculate base word duration at a given WPM.
 */
export function getBaseDuration(wpm: number): number {
  return 60_000 / wpm; // ms per word
}

/**
 * Calculate actual duration for a token.
 */
export function getTokenDuration(token: Token, currentWpm: number): number {
  const baseDuration = getBaseDuration(currentWpm);
  return baseDuration * token.delay_multiplier_after;
}

/**
 * Calculate blank frame duration for breaks.
 */
export function getBreakDuration(
  breakType: 'paragraph' | 'heading' | null,
  currentWpm: number,
  config: BreakConfig
): number {
  if (!breakType) return 0;

  const baseDuration = getBaseDuration(currentWpm);

  if (breakType === 'heading') {
    return baseDuration * config.headingMultiplier;
  }

  return baseDuration * config.paragraphMultiplier;
}

/**
 * Calculate total duration for displaying a token.
 * Includes break duration before + word duration.
 */
export function getTotalTokenDuration(
  token: Token,
  currentWpm: number,
  breakConfig: BreakConfig
): { breakDuration: number; wordDuration: number; total: number } {
  const breakDuration = getBreakDuration(token.break_before, currentWpm, breakConfig);
  const wordDuration = getTokenDuration(token, currentWpm);

  return {
    breakDuration,
    wordDuration,
    total: breakDuration + wordDuration,
  };
}
```

### 3. Ramp Function (`src/lib/playback/ramp.ts`)

```typescript
import type { TimingConfig } from './types';

/**
 * Calculate current WPM based on elapsed reading time.
 *
 * Linear ramp from startWpm to targetWpm over rampSeconds.
 */
export function getCurrentWpm(elapsedMs: number, config: TimingConfig): number {
  if (!config.rampEnabled || config.rampSeconds === 0) {
    return config.targetWpm;
  }

  const elapsedSeconds = elapsedMs / 1000;
  const progress = Math.min(1, elapsedSeconds / config.rampSeconds);

  // Linear interpolation
  const currentWpm = config.rampStartWpm + (config.targetWpm - config.rampStartWpm) * progress;

  return Math.round(currentWpm);
}

/**
 * Calculate ramp start WPM (50% of target, minimum 100).
 */
export function calculateRampStartWpm(targetWpm: number): number {
  return Math.max(100, Math.round(targetWpm * 0.5));
}

/**
 * Check if still in ramp period.
 */
export function isInRampPeriod(elapsedMs: number, rampSeconds: number): boolean {
  return elapsedMs < rampSeconds * 1000;
}
```

### 4. Playback History Hook (`src/hooks/usePlaybackHistory.ts`)

```typescript
import { useRef, useCallback } from 'react';
import type { PlaybackHistoryEntry } from '@/lib/playback/types';

const MAX_HISTORY_SIZE = 10000; // ~16 minutes at 600 WPM
const MIN_HISTORY_SIZE = 1000; // ~1.5 minutes at 600 WPM

export function usePlaybackHistory() {
  const historyRef = useRef<PlaybackHistoryEntry[]>([]);

  /**
   * Record a word being displayed.
   */
  const recordEntry = useCallback((wordIndex: number, elapsedTime: number) => {
    const entry: PlaybackHistoryEntry = {
      wordIndex,
      elapsedTimeAtStart: elapsedTime,
      timestamp: Date.now(),
    };

    historyRef.current.push(entry);

    // Trim history if too large
    if (historyRef.current.length > MAX_HISTORY_SIZE) {
      historyRef.current = historyRef.current.slice(-MIN_HISTORY_SIZE);
    }
  }, []);

  /**
   * Find word index at a given elapsed time.
   * Used for time-based rewind.
   */
  const findIndexAtTime = useCallback((targetElapsedMs: number): number => {
    const history = historyRef.current;

    if (history.length === 0) {
      return 0;
    }

    // Binary search for efficiency
    let left = 0;
    let right = history.length - 1;

    while (left < right) {
      const mid = Math.floor((left + right + 1) / 2);

      if (history[mid].elapsedTimeAtStart <= targetElapsedMs) {
        left = mid;
      } else {
        right = mid - 1;
      }
    }

    return history[left].wordIndex;
  }, []);

  /**
   * Rewind by a number of seconds.
   * Returns the word index to jump to.
   */
  const rewindBySeconds = useCallback(
    (currentElapsedMs: number, rewindSeconds: number): number => {
      const targetElapsed = Math.max(0, currentElapsedMs - rewindSeconds * 1000);
      return findIndexAtTime(targetElapsed);
    },
    [findIndexAtTime]
  );

  /**
   * Get the elapsed time for a word index.
   */
  const getElapsedTimeForIndex = useCallback((wordIndex: number): number => {
    const history = historyRef.current;

    // Find the entry for this word
    for (let i = history.length - 1; i >= 0; i--) {
      if (history[i].wordIndex === wordIndex) {
        return history[i].elapsedTimeAtStart;
      }
    }

    // Not found, estimate based on nearest
    if (history.length > 0) {
      const lastEntry = history[history.length - 1];
      // Rough estimate: assume constant WPM
      const avgMsPerWord = lastEntry.elapsedTimeAtStart / lastEntry.wordIndex;
      return wordIndex * avgMsPerWord;
    }

    return 0;
  }, []);

  /**
   * Clear history (on session reset).
   */
  const clearHistory = useCallback(() => {
    historyRef.current = [];
  }, []);

  /**
   * Get current history length (for debugging).
   */
  const getHistoryLength = useCallback(() => {
    return historyRef.current.length;
  }, []);

  return {
    recordEntry,
    findIndexAtTime,
    rewindBySeconds,
    getElapsedTimeForIndex,
    clearHistory,
    getHistoryLength,
  };
}
```

### 5. Token Cache Hook (`src/hooks/useTokenCache.ts`)

```typescript
import { useRef, useCallback, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { documentsApi } from '@/lib/api/documents';
import { documentKeys } from '@/hooks/useDocuments';
import type { Token, TokenChunk } from '@/lib/api/types';

const CHUNK_SIZE = 500;
const PREFETCH_THRESHOLD = 100; // Prefetch when this close to chunk boundary

interface TokenCacheState {
  documentId: string;
  totalWords: number;
  loadedChunks: Map<number, Token[]>; // chunkStart -> tokens
  loadingChunks: Set<number>;
}

export function useTokenCache(documentId: string, totalWords: number) {
  const queryClient = useQueryClient();
  const cacheRef = useRef<TokenCacheState>({
    documentId,
    totalWords,
    loadedChunks: new Map(),
    loadingChunks: new Set(),
  });

  // Reset cache if document changes
  useEffect(() => {
    if (cacheRef.current.documentId !== documentId) {
      cacheRef.current = {
        documentId,
        totalWords,
        loadedChunks: new Map(),
        loadingChunks: new Set(),
      };
    }
  }, [documentId, totalWords]);

  /**
   * Get chunk start index for a word index.
   */
  const getChunkStart = useCallback((wordIndex: number): number => {
    return Math.floor(wordIndex / CHUNK_SIZE) * CHUNK_SIZE;
  }, []);

  /**
   * Load a chunk of tokens.
   */
  const loadChunk = useCallback(
    async (chunkStart: number): Promise<Token[]> => {
      const cache = cacheRef.current;

      // Already loaded
      if (cache.loadedChunks.has(chunkStart)) {
        return cache.loadedChunks.get(chunkStart)!;
      }

      // Already loading
      if (cache.loadingChunks.has(chunkStart)) {
        // Wait for it to load
        while (cache.loadingChunks.has(chunkStart)) {
          await new Promise((r) => setTimeout(r, 50));
        }
        return cache.loadedChunks.get(chunkStart) || [];
      }

      // Start loading
      cache.loadingChunks.add(chunkStart);

      try {
        const response = await queryClient.fetchQuery({
          queryKey: documentKeys.tokens(documentId, chunkStart),
          queryFn: () => documentsApi.getTokens(documentId, chunkStart, CHUNK_SIZE),
          staleTime: Infinity,
        });

        cache.loadedChunks.set(chunkStart, response.tokens);
        return response.tokens;
      } finally {
        cache.loadingChunks.delete(chunkStart);
      }
    },
    [documentId, queryClient]
  );

  /**
   * Get a token by index, loading chunk if needed.
   */
  const getToken = useCallback(
    async (wordIndex: number): Promise<Token | null> => {
      if (wordIndex < 0 || wordIndex >= totalWords) {
        return null;
      }

      const chunkStart = getChunkStart(wordIndex);
      const tokens = await loadChunk(chunkStart);

      const localIndex = wordIndex - chunkStart;
      return tokens[localIndex] || null;
    },
    [totalWords, getChunkStart, loadChunk]
  );

  /**
   * Prefetch chunks around current position.
   */
  const prefetchAround = useCallback(
    (currentIndex: number) => {
      const currentChunkStart = getChunkStart(currentIndex);

      // Prefetch current chunk
      loadChunk(currentChunkStart);

      // Prefetch next chunk if close to boundary
      const positionInChunk = currentIndex - currentChunkStart;
      if (positionInChunk > CHUNK_SIZE - PREFETCH_THRESHOLD) {
        const nextChunkStart = currentChunkStart + CHUNK_SIZE;
        if (nextChunkStart < totalWords) {
          loadChunk(nextChunkStart);
        }
      }

      // Keep previous chunk for rewind
      const prevChunkStart = currentChunkStart - CHUNK_SIZE;
      if (prevChunkStart >= 0) {
        loadChunk(prevChunkStart);
      }
    },
    [getChunkStart, loadChunk, totalWords]
  );

  /**
   * Get multiple tokens in range (for rewind scenarios).
   */
  const getTokenRange = useCallback(
    async (startIndex: number, count: number): Promise<Token[]> => {
      const tokens: Token[] = [];
      const endIndex = Math.min(startIndex + count, totalWords);

      for (let i = startIndex; i < endIndex; i++) {
        const token = await getToken(i);
        if (token) {
          tokens.push(token);
        }
      }

      return tokens;
    },
    [getToken, totalWords]
  );

  /**
   * Check if a token is cached (for sync access in tight loops).
   */
  const isTokenCached = useCallback(
    (wordIndex: number): boolean => {
      const chunkStart = getChunkStart(wordIndex);
      return cacheRef.current.loadedChunks.has(chunkStart);
    },
    [getChunkStart]
  );

  /**
   * Get cached token synchronously (returns null if not cached).
   */
  const getCachedToken = useCallback(
    (wordIndex: number): Token | null => {
      const chunkStart = getChunkStart(wordIndex);
      const tokens = cacheRef.current.loadedChunks.get(chunkStart);

      if (!tokens) return null;

      const localIndex = wordIndex - chunkStart;
      return tokens[localIndex] || null;
    },
    [getChunkStart]
  );

  return {
    getToken,
    getTokenRange,
    prefetchAround,
    isTokenCached,
    getCachedToken,
  };
}
```

### 6. Playback Engine Hook (`src/hooks/usePlaybackEngine.ts`)

```typescript
import { useRef, useCallback, useEffect, useState } from 'react';
import type { Token } from '@/lib/api/types';
import type { TimingConfig, BreakConfig, PlaybackState } from '@/lib/playback/types';
import { getCurrentWpm } from '@/lib/playback/ramp';
import { getTotalTokenDuration, DEFAULT_BREAK_CONFIG } from '@/lib/playback/timing';
import { useTokenCache } from './useTokenCache';
import { usePlaybackHistory } from './usePlaybackHistory';

interface UsePlaybackEngineProps {
  documentId: string;
  totalWords: number;
  startIndex: number;
  timingConfig: TimingConfig;
  breakConfig?: BreakConfig;
  onWordChange?: (token: Token, index: number) => void;
  onComplete?: () => void;
  onProgress?: (index: number, percent: number) => void;
}

interface PlaybackEngineState {
  isPlaying: boolean;
  currentWordIndex: number;
  currentToken: Token | null;
  currentWpm: number;
  elapsedReadingTime: number;
  showingBreak: boolean;
}

export function usePlaybackEngine({
  documentId,
  totalWords,
  startIndex,
  timingConfig,
  breakConfig = DEFAULT_BREAK_CONFIG,
  onWordChange,
  onComplete,
  onProgress,
}: UsePlaybackEngineProps) {
  const [state, setState] = useState<PlaybackEngineState>({
    isPlaying: false,
    currentWordIndex: startIndex,
    currentToken: null,
    currentWpm: timingConfig.rampStartWpm,
    elapsedReadingTime: 0,
    showingBreak: false,
  });

  const tokenCache = useTokenCache(documentId, totalWords);
  const history = usePlaybackHistory();

  // Refs for animation loop
  const rafRef = useRef<number | null>(null);
  const lastFrameTimeRef = useRef<number>(0);
  const wordStartTimeRef = useRef<number>(0);
  const currentDurationRef = useRef<{ breakDuration: number; wordDuration: number }>({
    breakDuration: 0,
    wordDuration: 0,
  });
  const stateRef = useRef(state);

  // Keep ref in sync with state
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  /**
   * Display the next word.
   */
  const displayNextWord = useCallback(async () => {
    const currentState = stateRef.current;
    const nextIndex = currentState.currentWordIndex + 1;

    if (nextIndex >= totalWords) {
      // Reading complete
      setState((s) => ({ ...s, isPlaying: false }));
      onComplete?.();
      return;
    }

    // Get next token
    const token = await tokenCache.getToken(nextIndex);
    if (!token) {
      console.error('Failed to get token', nextIndex);
      return;
    }

    // Calculate current WPM
    const currentWpm = getCurrentWpm(currentState.elapsedReadingTime, timingConfig);

    // Calculate durations
    const { breakDuration, wordDuration } = getTotalTokenDuration(token, currentWpm, breakConfig);

    // Record in history
    history.recordEntry(nextIndex, currentState.elapsedReadingTime);

    // Update durations ref
    currentDurationRef.current = { breakDuration, wordDuration };
    wordStartTimeRef.current = performance.now();

    // Update state
    setState((s) => ({
      ...s,
      currentWordIndex: nextIndex,
      currentToken: token,
      currentWpm,
      showingBreak: breakDuration > 0,
    }));

    onWordChange?.(token, nextIndex);

    // Prefetch next chunks
    tokenCache.prefetchAround(nextIndex);

    // Report progress periodically
    if (nextIndex % 10 === 0) {
      const percent = (nextIndex / totalWords) * 100;
      onProgress?.(nextIndex, percent);
    }
  }, [
    totalWords,
    tokenCache,
    timingConfig,
    breakConfig,
    history,
    onWordChange,
    onComplete,
    onProgress,
  ]);

  /**
   * Animation frame callback.
   */
  const tick = useCallback(
    (timestamp: number) => {
      const currentState = stateRef.current;

      if (!currentState.isPlaying) {
        rafRef.current = null;
        return;
      }

      // Calculate delta time
      const deltaTime = timestamp - lastFrameTimeRef.current;
      lastFrameTimeRef.current = timestamp;

      // Update elapsed reading time
      setState((s) => ({
        ...s,
        elapsedReadingTime: s.elapsedReadingTime + deltaTime,
      }));

      // Check if it's time for next word
      const timeSinceWordStart = timestamp - wordStartTimeRef.current;
      const { breakDuration, wordDuration } = currentDurationRef.current;

      // First show break (blank frame), then word
      if (currentState.showingBreak && timeSinceWordStart >= breakDuration) {
        // Transition from break to word
        setState((s) => ({ ...s, showingBreak: false }));
      } else if (!currentState.showingBreak && timeSinceWordStart >= breakDuration + wordDuration) {
        // Time for next word
        displayNextWord();
      }

      // Schedule next frame
      rafRef.current = requestAnimationFrame(tick);
    },
    [displayNextWord]
  );

  /**
   * Start playback.
   */
  const play = useCallback(async () => {
    const currentState = stateRef.current;

    // Load initial token if needed
    if (!currentState.currentToken) {
      const token = await tokenCache.getToken(currentState.currentWordIndex);
      if (token) {
        const currentWpm = getCurrentWpm(currentState.elapsedReadingTime, timingConfig);
        const { breakDuration, wordDuration } = getTotalTokenDuration(
          token,
          currentWpm,
          breakConfig
        );

        currentDurationRef.current = { breakDuration, wordDuration };
        history.recordEntry(currentState.currentWordIndex, currentState.elapsedReadingTime);

        setState((s) => ({
          ...s,
          currentToken: token,
          currentWpm,
          showingBreak: breakDuration > 0,
        }));
      }
    }

    // Start playback
    lastFrameTimeRef.current = performance.now();
    wordStartTimeRef.current = performance.now();

    setState((s) => ({ ...s, isPlaying: true }));
    rafRef.current = requestAnimationFrame(tick);
  }, [tokenCache, timingConfig, breakConfig, history, tick]);

  /**
   * Pause playback.
   */
  const pause = useCallback(() => {
    setState((s) => ({ ...s, isPlaying: false }));

    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
  }, []);

  /**
   * Toggle play/pause.
   */
  const togglePlayPause = useCallback(() => {
    if (stateRef.current.isPlaying) {
      pause();
    } else {
      play();
    }
  }, [play, pause]);

  /**
   * Jump to a specific word index.
   */
  const jumpToIndex = useCallback(
    async (wordIndex: number) => {
      const clampedIndex = Math.max(0, Math.min(wordIndex, totalWords - 1));

      // Get token
      const token = await tokenCache.getToken(clampedIndex);
      if (!token) return;

      // Get elapsed time for this index from history (or estimate)
      const elapsedTime = history.getElapsedTimeForIndex(clampedIndex);

      // Update state
      setState((s) => ({
        ...s,
        currentWordIndex: clampedIndex,
        currentToken: token,
        elapsedReadingTime: elapsedTime,
        showingBreak: false,
      }));

      // Reset word timing
      wordStartTimeRef.current = performance.now();
      currentDurationRef.current = { breakDuration: 0, wordDuration: 0 };

      // Prefetch around new position
      tokenCache.prefetchAround(clampedIndex);
    },
    [totalWords, tokenCache, history]
  );

  /**
   * Rewind by seconds.
   */
  const rewindBySeconds = useCallback(
    (seconds: number) => {
      const newIndex = history.rewindBySeconds(stateRef.current.elapsedReadingTime, seconds);
      jumpToIndex(newIndex);
    },
    [history, jumpToIndex]
  );

  /**
   * Reset to start.
   */
  const reset = useCallback(() => {
    pause();
    history.clearHistory();

    setState({
      isPlaying: false,
      currentWordIndex: startIndex,
      currentToken: null,
      currentWpm: timingConfig.rampStartWpm,
      elapsedReadingTime: 0,
      showingBreak: false,
    });
  }, [pause, history, startIndex, timingConfig.rampStartWpm]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, []);

  // Prefetch initial chunks on mount
  useEffect(() => {
    tokenCache.prefetchAround(startIndex);
  }, [startIndex, tokenCache]);

  return {
    // State
    isPlaying: state.isPlaying,
    currentWordIndex: state.currentWordIndex,
    currentToken: state.currentToken,
    currentWpm: state.currentWpm,
    elapsedReadingTime: state.elapsedReadingTime,
    showingBreak: state.showingBreak,

    // Actions
    play,
    pause,
    togglePlayPause,
    jumpToIndex,
    rewindBySeconds,
    reset,

    // Utilities
    historyLength: history.getHistoryLength(),
  };
}
```

### 7. ORP Text Component (`src/components/reader/ORPText.tsx`)

```typescript
import { useMemo } from 'react'
import { cn } from '@/lib/cn'

interface ORPTextProps {
  text: string
  orpIndex: number
  className?: string
}

/**
 * Renders text with ORP (Optimal Recognition Point) highlighted.
 * The ORP character is highlighted in a different color.
 */
export function ORPText({ text, orpIndex, className }: ORPTextProps) {
  const parts = useMemo(() => {
    const before = text.slice(0, orpIndex)
    const orp = text[orpIndex] || ''
    const after = text.slice(orpIndex + 1)
    return { before, orp, after }
  }, [text, orpIndex])

  return (
    <span className={cn('font-mono', className)}>
      <span className="text-white/70">{parts.before}</span>
      <span className="text-red-500 font-bold">{parts.orp}</span>
      <span className="text-white/70">{parts.after}</span>
    </span>
  )
}
```

### 8. Word Display Component (`src/components/reader/WordDisplay.tsx`)

```typescript
import { ORPText } from './ORPText'
import type { Token } from '@/lib/api/types'

interface WordDisplayProps {
  token: Token | null
  showingBreak: boolean
}

/**
 * Displays the current word with ORP alignment.
 * The word is positioned so the ORP character is at the center.
 */
export function WordDisplay({ token, showingBreak }: WordDisplayProps) {
  if (!token || showingBreak) {
    // Blank frame
    return (
      <div className="h-32 flex items-center justify-center">
        <div className="w-px h-8 bg-white/20" /> {/* Focus line */}
      </div>
    )
  }

  // Calculate positioning to center ORP
  // We use a fixed-width container and position the text so ORP is centered
  const { display_text, orp_index_display } = token

  return (
    <div className="h-32 flex items-center justify-center relative">
      {/* Center guide line */}
      <div className="absolute top-0 bottom-0 left-1/2 w-px bg-white/10" />

      {/* Word container */}
      <div
        className="text-6xl tracking-wider"
        style={{
          // Position so ORP character aligns with center
          transform: `translateX(${calculateORPOffset(display_text, orp_index_display)}ch)`,
        }}
      >
        <ORPText text={display_text} orpIndex={orp_index_display} />
      </div>
    </div>
  )
}

/**
 * Calculate the offset to center the ORP character.
 * Returns offset in 'ch' units (character width).
 */
function calculateORPOffset(text: string, orpIndex: number): number {
  // Characters before ORP should be on the left
  // Characters after ORP (including ORP) should be on the right
  const charsBeforeORP = orpIndex
  const charsAfterORP = text.length - orpIndex - 1

  // Offset = half of (chars after - chars before) to center the ORP
  // Plus 0.5 to center on the ORP character itself
  return (charsBeforeORP - charsAfterORP) / 2 - 0.5
}
```

### 9. Reader Overlay (`src/components/reader/ReaderOverlay.tsx`)

```typescript
import { useEffect, useCallback } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { WordDisplay } from './WordDisplay'
import { usePlaybackEngine } from '@/hooks/usePlaybackEngine'
import { useReaderStore } from '@/stores/readerStore'
import { useAppStore } from '@/stores/appStore'
import { sessionsApi } from '@/lib/api/sessions'
import { calculateRampStartWpm } from '@/lib/playback/ramp'

interface ReaderOverlayProps {
  documentId: string
  sessionId: string
  totalWords: number
  startIndex: number
}

export function ReaderOverlay({
  documentId,
  sessionId,
  totalWords,
  startIndex,
}: ReaderOverlayProps) {
  const navigate = useNavigate()
  const { settings } = useReaderStore()
  const { exitReaderMode } = useAppStore()

  // Calculate timing config from settings
  const timingConfig = {
    targetWpm: settings.targetWpm,
    rampEnabled: settings.rampEnabled,
    rampSeconds: settings.rampSeconds,
    rampStartWpm: calculateRampStartWpm(settings.targetWpm),
  }

  // Progress save callback
  const handleProgress = useCallback(
    async (index: number, percent: number) => {
      try {
        await sessionsApi.updateProgress(sessionId, {
          current_word_index: index,
          last_known_percent: percent,
        })
      } catch (e) {
        console.error('Failed to save progress:', e)
      }
    },
    [sessionId]
  )

  // Completion callback
  const handleComplete = useCallback(() => {
    handleProgress(totalWords - 1, 100)
  }, [handleProgress, totalWords])

  // Initialize playback engine
  const engine = usePlaybackEngine({
    documentId,
    totalWords,
    startIndex,
    timingConfig,
    onProgress: handleProgress,
    onComplete: handleComplete,
  })

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.code) {
        case 'Space':
          e.preventDefault()
          engine.togglePlayPause()
          break

        case 'Escape':
          e.preventDefault()
          engine.pause()
          exitReaderMode()
          navigate({
            to: '/deepread/$documentId',
            params: { documentId },
          })
          break

        case 'ArrowLeft':
          e.preventDefault()
          engine.rewindBySeconds(e.shiftKey ? 30 : 10)
          break

        // More shortcuts will be added in Session 8
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [engine, exitReaderMode, navigate, documentId])

  // Auto-start on mount
  useEffect(() => {
    engine.play()
  }, [])

  // Save progress on unmount/pause
  useEffect(() => {
    if (!engine.isPlaying) {
      const percent = (engine.currentWordIndex / totalWords) * 100
      handleProgress(engine.currentWordIndex, percent)
    }
  }, [engine.isPlaying, engine.currentWordIndex, totalWords, handleProgress])

  return (
    <div className="fixed inset-0 bg-black flex flex-col items-center justify-center">
      {/* Word display */}
      <WordDisplay
        token={engine.currentToken}
        showingBreak={engine.showingBreak}
      />

      {/* Progress indicator */}
      <div className="absolute bottom-8 left-8 right-8">
        <div className="h-1 bg-white/10 rounded-full overflow-hidden">
          <div
            className="h-full bg-primary transition-all duration-100"
            style={{
              width: `${(engine.currentWordIndex / totalWords) * 100}%`,
            }}
          />
        </div>
        <div className="flex justify-between mt-2 text-sm text-white/50">
          <span>{engine.currentWordIndex.toLocaleString()} / {totalWords.toLocaleString()}</span>
          <span>{engine.currentWpm} WPM</span>
        </div>
      </div>

      {/* Play/Pause indicator */}
      {!engine.isPlaying && (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none">
          <div className="text-white/30 text-2xl">PAUSED</div>
        </div>
      )}

      {/* Controls hint */}
      <div className="absolute bottom-4 text-center text-white/30 text-sm">
        Space: Play/Pause | ← Rewind 10s | Shift+← Rewind 30s | Esc: Exit
      </div>
    </div>
  )
}
```

### 10. Update Document Route for Reader

```typescript
// Update src/routes/deepread/$documentId.tsx

import { createFileRoute } from '@tanstack/react-router'
import { Container } from '@/components/layout/Container'
import { PreviewContainer } from '@/components/preview/PreviewContainer'
import { ReaderOverlay } from '@/components/reader/ReaderOverlay'
import { useDocument } from '@/hooks/useDocuments'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'

interface SearchParams {
  reading?: boolean
  sessionId?: string
  startIndex?: number
}

export const Route = createFileRoute('/deepread/$documentId')({
  component: DocumentPage,
  validateSearch: (search: Record<string, unknown>): SearchParams => ({
    reading: search.reading === true || search.reading === 'true',
    sessionId: typeof search.sessionId === 'string' ? search.sessionId : undefined,
    startIndex: typeof search.startIndex === 'number' ? search.startIndex : 0,
  }),
})

function DocumentPage() {
  const { documentId } = Route.useParams()
  const { reading, sessionId, startIndex = 0 } = Route.useSearch()
  const { data: document, isLoading } = useDocument(documentId)

  // Show reader overlay if in reading mode
  if (reading && sessionId && document) {
    return (
      <ReaderOverlay
        documentId={documentId}
        sessionId={sessionId}
        totalWords={document.total_words}
        startIndex={startIndex}
      />
    )
  }

  // Loading state
  if (isLoading) {
    return (
      <Container className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </Container>
    )
  }

  // Preview mode
  return (
    <Container className="max-w-4xl">
      <PreviewContainer documentId={documentId} />
    </Container>
  )
}
```

---

## Verification Checklist

- [ ] Reader overlay fills screen with black background
- [ ] Words display one at a time
- [ ] ORP character is highlighted in red
- [ ] ORP is centered on screen (words shift position)
- [ ] Punctuation causes longer pauses (visible delay)
- [ ] Paragraph breaks show blank frame
- [ ] Ramp works (WPM starts low and increases)
- [ ] Space bar toggles play/pause
- [ ] Left arrow rewinds 10 seconds
- [ ] Shift+Left arrow rewinds 30 seconds
- [ ] Escape exits reader mode
- [ ] Progress bar updates
- [ ] Progress saves to backend
- [ ] Large documents don't lag (token caching works)

---

## Context for Next Session

**What exists after Session 7:**

- Functional RSVP reader with ORP alignment
- Playback engine with timing loop
- Token caching and prefetching
- Ramp function implementation
- Playback history buffer for rewind
- Basic keyboard shortcuts (Space, Left, Escape)

**Session 8 will need:**

- usePlaybackEngine hook (for controls)
- useReaderStore (for settings)
- engine.rewindBySeconds function
- Current state: isPlaying, currentWpm
