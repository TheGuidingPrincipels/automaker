# Session 8: Reader Controls & Shortcuts

## Overview

**Duration**: ~3-4 hours
**Goal**: Build the reader controls UI including play/pause, rewind buttons, WPM slider, ramp toggle, and complete keyboard shortcut support with auto-hiding behavior.

**Deliverable**: Fully controllable reader with intuitive UI and comprehensive keyboard shortcuts.

---

## Prerequisites

- Session 7 completed (reader engine with playback)
- usePlaybackEngine hook functional
- useReaderStore with settings

---

## Objectives & Acceptance Criteria

| #   | Objective            | Acceptance Criteria                  |
| --- | -------------------- | ------------------------------------ |
| 1   | Play/Pause button    | Visual state matches playback        |
| 2   | Rewind buttons       | 10s, 15s, 30s rewind options         |
| 3   | WPM slider           | Live update during playback          |
| 4   | Ramp toggle          | Enable/disable with duration setting |
| 5   | Progress scrubber    | Jump to position while reading       |
| 6   | Keyboard shortcuts   | Full shortcut support                |
| 7   | Auto-hide controls   | Fade out after inactivity            |
| 8   | Settings persistence | Remember user preferences            |

---

## File Structure

```
frontend/src/
├── components/
│   └── reader/
│       ├── ReaderOverlay.tsx       # Update with controls
│       ├── ReaderControls.tsx      # Main controls container
│       ├── PlaybackControls.tsx    # Play/pause/rewind
│       ├── WpmControl.tsx          # WPM slider
│       ├── RampControl.tsx         # Ramp toggle and duration
│       ├── ReaderProgress.tsx      # Progress bar with scrubber
│       └── ControlsOverlay.tsx     # Auto-hiding overlay
├── hooks/
│   └── useAutoHide.ts              # Auto-hide logic
└── lib/
    └── keyboard.ts                 # Keyboard shortcut definitions
```

---

## Implementation Details

### 1. Keyboard Shortcuts Definition (`src/lib/keyboard.ts`)

```typescript
export interface KeyboardShortcut {
  key: string;
  code: string;
  shift?: boolean;
  ctrl?: boolean;
  alt?: boolean;
  description: string;
  action: string;
}

export const READER_SHORTCUTS: KeyboardShortcut[] = [
  {
    key: ' ',
    code: 'Space',
    description: 'Play / Pause',
    action: 'togglePlayPause',
  },
  {
    key: 'ArrowLeft',
    code: 'ArrowLeft',
    description: 'Rewind 10 seconds',
    action: 'rewind10',
  },
  {
    key: 'ArrowLeft',
    code: 'ArrowLeft',
    shift: true,
    description: 'Rewind 30 seconds',
    action: 'rewind30',
  },
  {
    key: 'ArrowUp',
    code: 'ArrowUp',
    description: 'Increase WPM (+25)',
    action: 'increaseWpm',
  },
  {
    key: 'ArrowDown',
    code: 'ArrowDown',
    description: 'Decrease WPM (-25)',
    action: 'decreaseWpm',
  },
  {
    key: 'r',
    code: 'KeyR',
    description: 'Toggle ramp mode',
    action: 'toggleRamp',
  },
  {
    key: 'Escape',
    code: 'Escape',
    description: 'Exit reader',
    action: 'exit',
  },
  {
    key: 'h',
    code: 'KeyH',
    description: 'Show/hide controls',
    action: 'toggleControls',
  },
];

export function formatShortcut(shortcut: KeyboardShortcut): string {
  const parts: string[] = [];

  if (shortcut.ctrl) parts.push('Ctrl');
  if (shortcut.alt) parts.push('Alt');
  if (shortcut.shift) parts.push('Shift');

  // Format special keys
  const keyName =
    {
      ' ': 'Space',
      ArrowLeft: '←',
      ArrowRight: '→',
      ArrowUp: '↑',
      ArrowDown: '↓',
      Escape: 'Esc',
    }[shortcut.key] || shortcut.key.toUpperCase();

  parts.push(keyName);

  return parts.join(' + ');
}
```

### 2. Auto-Hide Hook (`src/hooks/useAutoHide.ts`)

```typescript
import { useState, useEffect, useCallback, useRef } from 'react';

interface UseAutoHideOptions {
  timeout?: number;
  initialVisible?: boolean;
}

export function useAutoHide({ timeout = 3000, initialVisible = true }: UseAutoHideOptions = {}) {
  const [isVisible, setIsVisible] = useState(initialVisible);
  const [isPinned, setIsPinned] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const show = useCallback(() => {
    setIsVisible(true);

    // Reset timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    if (!isPinned) {
      timeoutRef.current = setTimeout(() => {
        setIsVisible(false);
      }, timeout);
    }
  }, [timeout, isPinned]);

  const hide = useCallback(() => {
    if (!isPinned) {
      setIsVisible(false);
    }
  }, [isPinned]);

  const toggle = useCallback(() => {
    setIsVisible((v) => !v);
  }, []);

  const pin = useCallback(() => {
    setIsPinned(true);
    setIsVisible(true);
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
  }, []);

  const unpin = useCallback(() => {
    setIsPinned(false);
    // Start hide timeout
    timeoutRef.current = setTimeout(() => {
      setIsVisible(false);
    }, timeout);
  }, [timeout]);

  // Handle mouse movement
  useEffect(() => {
    const handleMouseMove = () => {
      show();
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [show]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return {
    isVisible,
    isPinned,
    show,
    hide,
    toggle,
    pin,
    unpin,
  };
}
```

### 3. Controls Overlay (`src/components/reader/ControlsOverlay.tsx`)

```typescript
import { ReactNode } from 'react'
import { cn } from '@/lib/cn'

interface ControlsOverlayProps {
  isVisible: boolean
  children: ReactNode
  position: 'top' | 'bottom'
}

export function ControlsOverlay({
  isVisible,
  children,
  position,
}: ControlsOverlayProps) {
  return (
    <div
      className={cn(
        'absolute left-0 right-0 transition-all duration-300',
        position === 'top' ? 'top-0' : 'bottom-0',
        isVisible
          ? 'opacity-100 translate-y-0'
          : position === 'top'
            ? 'opacity-0 -translate-y-4 pointer-events-none'
            : 'opacity-0 translate-y-4 pointer-events-none'
      )}
    >
      {/* Gradient background */}
      <div
        className={cn(
          'absolute inset-0',
          position === 'top'
            ? 'bg-gradient-to-b from-black/80 to-transparent'
            : 'bg-gradient-to-t from-black/80 to-transparent'
        )}
      />

      {/* Content */}
      <div className="relative z-10">{children}</div>
    </div>
  )
}
```

### 4. Playback Controls (`src/components/reader/PlaybackControls.tsx`)

```typescript
import { Play, Pause, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/cn'

interface PlaybackControlsProps {
  isPlaying: boolean
  onPlayPause: () => void
  onRewind: (seconds: number) => void
}

export function PlaybackControls({
  isPlaying,
  onPlayPause,
  onRewind,
}: PlaybackControlsProps) {
  return (
    <div className="flex items-center gap-2">
      {/* Rewind buttons */}
      <RewindButton seconds={30} onRewind={onRewind} />
      <RewindButton seconds={15} onRewind={onRewind} />
      <RewindButton seconds={10} onRewind={onRewind} />

      {/* Play/Pause */}
      <Button
        variant="ghost"
        size="lg"
        onClick={onPlayPause}
        className="h-14 w-14 rounded-full bg-white/10 hover:bg-white/20"
      >
        {isPlaying ? (
          <Pause className="h-6 w-6 text-white" />
        ) : (
          <Play className="h-6 w-6 text-white ml-0.5" />
        )}
      </Button>
    </div>
  )
}

interface RewindButtonProps {
  seconds: number
  onRewind: (seconds: number) => void
}

function RewindButton({ seconds, onRewind }: RewindButtonProps) {
  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => onRewind(seconds)}
      className="h-10 px-3 text-white/70 hover:text-white hover:bg-white/10"
    >
      <RotateCcw className="h-4 w-4 mr-1" />
      <span className="text-sm">{seconds}s</span>
    </Button>
  )
}
```

### 5. WPM Control (`src/components/reader/WpmControl.tsx`)

```typescript
import { Minus, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'

interface WpmControlProps {
  currentWpm: number
  targetWpm: number
  onTargetChange: (wpm: number) => void
  isInRamp: boolean
}

export function WpmControl({
  currentWpm,
  targetWpm,
  onTargetChange,
  isInRamp,
}: WpmControlProps) {
  const handleDecrease = () => {
    onTargetChange(Math.max(100, targetWpm - 25))
  }

  const handleIncrease = () => {
    onTargetChange(Math.min(1500, targetWpm + 25))
  }

  return (
    <div className="flex items-center gap-4">
      <div className="text-white/70 text-sm min-w-[80px]">
        <div className="text-lg font-bold text-white">{currentWpm}</div>
        <div className="text-xs">
          {isInRamp ? `→ ${targetWpm}` : 'WPM'}
        </div>
      </div>

      <Button
        variant="ghost"
        size="icon"
        onClick={handleDecrease}
        className="h-8 w-8 text-white/70 hover:text-white hover:bg-white/10"
      >
        <Minus className="h-4 w-4" />
      </Button>

      <Slider
        value={[targetWpm]}
        onValueChange={([v]) => onTargetChange(v)}
        min={100}
        max={1500}
        step={25}
        className="w-32"
      />

      <Button
        variant="ghost"
        size="icon"
        onClick={handleIncrease}
        className="h-8 w-8 text-white/70 hover:text-white hover:bg-white/10"
      >
        <Plus className="h-4 w-4" />
      </Button>
    </div>
  )
}
```

### 6. Ramp Control (`src/components/reader/RampControl.tsx`)

```typescript
import { TrendingUp } from 'lucide-react'
import { Switch } from '@/components/ui/switch'
import { Slider } from '@/components/ui/slider'
import { cn } from '@/lib/cn'

interface RampControlProps {
  enabled: boolean
  seconds: number
  onEnabledChange: (enabled: boolean) => void
  onSecondsChange: (seconds: number) => void
}

export function RampControl({
  enabled,
  seconds,
  onEnabledChange,
  onSecondsChange,
}: RampControlProps) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-2">
        <TrendingUp
          className={cn(
            'h-4 w-4',
            enabled ? 'text-primary' : 'text-white/50'
          )}
        />
        <span
          className={cn(
            'text-sm',
            enabled ? 'text-white' : 'text-white/50'
          )}
        >
          Ramp
        </span>
      </div>

      <Switch
        checked={enabled}
        onCheckedChange={onEnabledChange}
      />

      {enabled && (
        <div className="flex items-center gap-2">
          <Slider
            value={[seconds]}
            onValueChange={([v]) => onSecondsChange(v)}
            min={0}
            max={60}
            step={5}
            className="w-20"
          />
          <span className="text-sm text-white/70 min-w-[30px]">
            {seconds}s
          </span>
        </div>
      )}
    </div>
  )
}
```

### 7. Reader Progress (`src/components/reader/ReaderProgress.tsx`)

```typescript
import { Slider } from '@/components/ui/slider'

interface ReaderProgressProps {
  currentIndex: number
  totalWords: number
  onSeek: (index: number) => void
  elapsedTime: number
  currentWpm: number
}

export function ReaderProgress({
  currentIndex,
  totalWords,
  onSeek,
  elapsedTime,
  currentWpm,
}: ReaderProgressProps) {
  const percentage = totalWords > 0 ? (currentIndex / totalWords) * 100 : 0

  // Estimate remaining time
  const remainingWords = totalWords - currentIndex
  const remainingMinutes = remainingWords / currentWpm
  const remainingTime = formatTime(remainingMinutes * 60)

  const handleSeek = (value: number[]) => {
    const newIndex = Math.floor((value[0] / 100) * totalWords)
    onSeek(newIndex)
  }

  return (
    <div className="space-y-2 px-4">
      <Slider
        value={[percentage]}
        onValueChange={handleSeek}
        max={100}
        step={0.1}
        className="w-full"
      />

      <div className="flex justify-between text-sm text-white/50">
        <span>
          {currentIndex.toLocaleString()} / {totalWords.toLocaleString()} words
        </span>
        <span>{percentage.toFixed(1)}%</span>
        <span>~{remainingTime} remaining</span>
      </div>
    </div>
  )
}

function formatTime(seconds: number): string {
  if (seconds < 60) {
    return `${Math.ceil(seconds)}s`
  }

  const minutes = Math.floor(seconds / 60)
  const remainingSecs = Math.ceil(seconds % 60)

  if (minutes < 60) {
    return remainingSecs > 0 ? `${minutes}m ${remainingSecs}s` : `${minutes}m`
  }

  const hours = Math.floor(minutes / 60)
  const remainingMins = minutes % 60

  return `${hours}h ${remainingMins}m`
}
```

### 8. Reader Controls Container (`src/components/reader/ReaderControls.tsx`)

```typescript
import { PlaybackControls } from './PlaybackControls'
import { WpmControl } from './WpmControl'
import { RampControl } from './RampControl'
import { ReaderProgress } from './ReaderProgress'
import { ControlsOverlay } from './ControlsOverlay'
import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ReaderControlsProps {
  // Playback state
  isPlaying: boolean
  currentWordIndex: number
  totalWords: number
  currentWpm: number
  elapsedTime: number
  isInRamp: boolean

  // Settings
  targetWpm: number
  rampEnabled: boolean
  rampSeconds: number

  // Visibility
  isVisible: boolean

  // Callbacks
  onPlayPause: () => void
  onRewind: (seconds: number) => void
  onSeek: (index: number) => void
  onTargetWpmChange: (wpm: number) => void
  onRampEnabledChange: (enabled: boolean) => void
  onRampSecondsChange: (seconds: number) => void
  onExit: () => void
}

export function ReaderControls({
  isPlaying,
  currentWordIndex,
  totalWords,
  currentWpm,
  elapsedTime,
  isInRamp,
  targetWpm,
  rampEnabled,
  rampSeconds,
  isVisible,
  onPlayPause,
  onRewind,
  onSeek,
  onTargetWpmChange,
  onRampEnabledChange,
  onRampSecondsChange,
  onExit,
}: ReaderControlsProps) {
  return (
    <>
      {/* Top controls */}
      <ControlsOverlay isVisible={isVisible} position="top">
        <div className="flex items-center justify-between p-4">
          <WpmControl
            currentWpm={currentWpm}
            targetWpm={targetWpm}
            onTargetChange={onTargetWpmChange}
            isInRamp={isInRamp}
          />

          <RampControl
            enabled={rampEnabled}
            seconds={rampSeconds}
            onEnabledChange={onRampEnabledChange}
            onSecondsChange={onRampSecondsChange}
          />

          <Button
            variant="ghost"
            size="icon"
            onClick={onExit}
            className="h-10 w-10 text-white/70 hover:text-white hover:bg-white/10"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>
      </ControlsOverlay>

      {/* Bottom controls */}
      <ControlsOverlay isVisible={isVisible} position="bottom">
        <div className="p-4 space-y-4">
          <div className="flex justify-center">
            <PlaybackControls
              isPlaying={isPlaying}
              onPlayPause={onPlayPause}
              onRewind={onRewind}
            />
          </div>

          <ReaderProgress
            currentIndex={currentWordIndex}
            totalWords={totalWords}
            onSeek={onSeek}
            elapsedTime={elapsedTime}
            currentWpm={currentWpm}
          />
        </div>
      </ControlsOverlay>
    </>
  )
}
```

### 9. Updated Reader Overlay (`src/components/reader/ReaderOverlay.tsx`)

```typescript
import { useEffect, useCallback } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { WordDisplay } from './WordDisplay'
import { ReaderControls } from './ReaderControls'
import { usePlaybackEngine } from '@/hooks/usePlaybackEngine'
import { useAutoHide } from '@/hooks/useAutoHide'
import { useReaderStore } from '@/stores/readerStore'
import { useAppStore } from '@/stores/appStore'
import { sessionsApi } from '@/lib/api/sessions'
import { calculateRampStartWpm, isInRampPeriod } from '@/lib/playback/ramp'

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
  const {
    settings,
    setTargetWpm,
    setRampEnabled,
    setRampSeconds,
  } = useReaderStore()
  const { exitReaderMode } = useAppStore()

  // Auto-hide controls
  const controls = useAutoHide({ timeout: 3000 })

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
          target_wpm: settings.targetWpm,
          ramp_enabled: settings.rampEnabled,
        })
      } catch (e) {
        console.error('Failed to save progress:', e)
      }
    },
    [sessionId, settings.targetWpm, settings.rampEnabled]
  )

  // Completion callback
  const handleComplete = useCallback(() => {
    handleProgress(totalWords - 1, 100)
    controls.pin()  // Show controls on completion
  }, [handleProgress, totalWords, controls])

  // Initialize playback engine
  const engine = usePlaybackEngine({
    documentId,
    totalWords,
    startIndex,
    timingConfig,
    onProgress: handleProgress,
    onComplete: handleComplete,
  })

  // Exit handler
  const handleExit = useCallback(() => {
    engine.pause()
    const percent = (engine.currentWordIndex / totalWords) * 100
    handleProgress(engine.currentWordIndex, percent)
    exitReaderMode()
    navigate({
      to: '/deepread/$documentId',
      params: { documentId },
    })
  }, [engine, totalWords, handleProgress, exitReaderMode, navigate, documentId])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Prevent default for all our shortcuts
      const handled = true

      switch (e.code) {
        case 'Space':
          e.preventDefault()
          engine.togglePlayPause()
          break

        case 'Escape':
          e.preventDefault()
          handleExit()
          break

        case 'ArrowLeft':
          e.preventDefault()
          engine.rewindBySeconds(e.shiftKey ? 30 : 10)
          break

        case 'ArrowUp':
          e.preventDefault()
          setTargetWpm(Math.min(1500, settings.targetWpm + 25))
          break

        case 'ArrowDown':
          e.preventDefault()
          setTargetWpm(Math.max(100, settings.targetWpm - 25))
          break

        case 'KeyR':
          e.preventDefault()
          setRampEnabled(!settings.rampEnabled)
          break

        case 'KeyH':
          e.preventDefault()
          controls.toggle()
          break

        default:
          // Not our shortcut
          return
      }

      // Show controls briefly when using keyboard
      controls.show()
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [
    engine,
    handleExit,
    settings,
    setTargetWpm,
    setRampEnabled,
    controls,
  ])

  // Auto-start on mount
  useEffect(() => {
    const timer = setTimeout(() => {
      engine.play()
    }, 500)  // Short delay for visual readiness

    return () => clearTimeout(timer)
  }, [])

  // Save progress on pause
  useEffect(() => {
    if (!engine.isPlaying && engine.currentWordIndex > startIndex) {
      const percent = (engine.currentWordIndex / totalWords) * 100
      handleProgress(engine.currentWordIndex, percent)
    }
  }, [engine.isPlaying])

  // Check if in ramp period
  const isInRamp = isInRampPeriod(
    engine.elapsedReadingTime,
    settings.rampSeconds
  ) && settings.rampEnabled

  return (
    <div className="fixed inset-0 bg-black flex items-center justify-center select-none">
      {/* Word display */}
      <WordDisplay
        token={engine.currentToken}
        showingBreak={engine.showingBreak}
      />

      {/* Controls overlay */}
      <ReaderControls
        isPlaying={engine.isPlaying}
        currentWordIndex={engine.currentWordIndex}
        totalWords={totalWords}
        currentWpm={engine.currentWpm}
        elapsedTime={engine.elapsedReadingTime}
        isInRamp={isInRamp}
        targetWpm={settings.targetWpm}
        rampEnabled={settings.rampEnabled}
        rampSeconds={settings.rampSeconds}
        isVisible={controls.isVisible}
        onPlayPause={engine.togglePlayPause}
        onRewind={engine.rewindBySeconds}
        onSeek={engine.jumpToIndex}
        onTargetWpmChange={setTargetWpm}
        onRampEnabledChange={setRampEnabled}
        onRampSecondsChange={setRampSeconds}
        onExit={handleExit}
      />

      {/* Paused overlay */}
      {!engine.isPlaying && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-white/20 text-4xl font-bold">PAUSED</div>
        </div>
      )}
    </div>
  )
}
```

### 10. Add Switch Component from shadcn

```bash
pnpm dlx shadcn@latest add switch
```

---

## Keyboard Shortcuts Reference

| Key       | Action             |
| --------- | ------------------ |
| Space     | Play / Pause       |
| ←         | Rewind 10 seconds  |
| Shift + ← | Rewind 30 seconds  |
| ↑         | Increase WPM (+25) |
| ↓         | Decrease WPM (-25) |
| R         | Toggle ramp mode   |
| H         | Show/hide controls |
| Escape    | Exit reader        |

---

## Testing Requirements

### Manual Testing Checklist

- [ ] Play/Pause button toggles playback
- [ ] Play button shows pause icon when playing
- [ ] Rewind 10s button jumps back correctly
- [ ] Rewind 15s button jumps back correctly
- [ ] Rewind 30s button jumps back correctly
- [ ] WPM slider updates target WPM
- [ ] WPM +/- buttons work in increments of 25
- [ ] Current WPM display shows ramp progress
- [ ] Ramp toggle enables/disables ramp
- [ ] Ramp duration slider adjusts ramp time
- [ ] Progress scrubber allows seeking
- [ ] Progress shows percentage and remaining time
- [ ] Controls auto-hide after 3 seconds
- [ ] Mouse movement shows controls
- [ ] H key toggles controls visibility
- [ ] All keyboard shortcuts work
- [ ] Settings persist between sessions
- [ ] Exit button saves progress and returns to preview

### Integration Test

```typescript
// tests/e2e/reader-controls.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Reader Controls', () => {
  test.beforeEach(async ({ page }) => {
    // Create document and start reading
    await page.goto('/deepread');
    await page.fill('textarea', 'Word '.repeat(100));
    await page.click('text=Continue to Preview');
    await page.click('text=Start Reading');
  });

  test('space toggles playback', async ({ page }) => {
    // Initially playing
    await page.waitForTimeout(500);

    // Pause
    await page.keyboard.press('Space');
    await expect(page.locator('text=PAUSED')).toBeVisible();

    // Resume
    await page.keyboard.press('Space');
    await expect(page.locator('text=PAUSED')).not.toBeVisible();
  });

  test('arrow keys adjust WPM', async ({ page }) => {
    // Get initial WPM
    const wpmText = await page.locator('[data-testid="current-wpm"]').textContent();
    const initialWpm = parseInt(wpmText || '300');

    // Increase
    await page.keyboard.press('ArrowUp');
    await expect(page.locator('[data-testid="target-wpm"]')).toContainText(String(initialWpm + 25));

    // Decrease
    await page.keyboard.press('ArrowDown');
    await expect(page.locator('[data-testid="target-wpm"]')).toContainText(String(initialWpm));
  });

  test('escape exits reader', async ({ page }) => {
    await page.keyboard.press('Escape');
    await expect(page).toHaveURL(/\/deepread\//);
    await expect(page.locator('text=PAUSED')).not.toBeVisible();
  });
});
```

---

## Verification Checklist

- [ ] PlaybackControls shows correct play/pause state
- [ ] Rewind buttons work for 10s, 15s, 30s
- [ ] WpmControl slider and buttons work
- [ ] RampControl toggle and duration slider work
- [ ] ReaderProgress shows correct stats
- [ ] ReaderProgress scrubber seeks correctly
- [ ] ControlsOverlay fades in/out smoothly
- [ ] Auto-hide works after 3 seconds
- [ ] Mouse movement triggers show
- [ ] All keyboard shortcuts work
- [ ] Settings changes update playback immediately
- [ ] Settings persist to localStorage
- [ ] Exit saves progress

---

## Context for Next Session

**What exists after Session 8:**

- Complete reader controls UI
- Auto-hiding overlay behavior
- All keyboard shortcuts
- WPM and ramp settings controls
- Progress scrubber with seeking
- Settings persistence

**Session 9 will need:**

- Session API (already exists)
- useReaderStore for settings
- Progress save functionality (already exists)
