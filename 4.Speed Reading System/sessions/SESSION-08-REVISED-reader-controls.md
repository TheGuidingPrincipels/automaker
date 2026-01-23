# Session 8 (REVISED): Reader Controls

## Overview

**Goal**: Implement the full reader control UI with auto-hiding behavior, keyboard shortcuts, WPM adjustment, and progress scrubber.

**Prerequisites**:

- Session 7 (REVISED) completed
- Reader engine working with play/pause/rewind

> ⚠️ **Code Organization**: All components in this session are **frontend-only** (UI controls). Backend APIs are in `4.Speed Reading System/backend/`. See `README.md` for details.

---

## Deliverables

| #   | Component         | Description                  |
| --- | ----------------- | ---------------------------- |
| 1   | ReaderControls    | Auto-hiding control overlay  |
| 2   | PlaybackControls  | Play/Pause/Rewind buttons    |
| 3   | WpmControl        | WPM slider and adjustment    |
| 4   | RampControl       | Ramp toggle and duration     |
| 5   | ProgressScrubber  | Seekable progress bar        |
| 6   | useAutoHide       | Auto-hide hook on inactivity |
| 7   | useReaderKeyboard | Full keyboard shortcuts      |

---

## File Structure

```
components/views/speed-reading-reader/
├── components/
│   ├── reader-controls.tsx        # Main control overlay
│   ├── playback-controls.tsx      # Play/Pause/Rewind
│   ├── wpm-control.tsx            # WPM slider
│   ├── ramp-control.tsx           # Ramp settings
│   ├── progress-scrubber.tsx      # Seekable progress
│   └── reader-progress.tsx        # Progress indicator

hooks/speed-reading/
├── use-auto-hide.ts               # Auto-hide on inactivity
└── use-reader-keyboard.ts         # Keyboard shortcuts
```

---

## Implementation

### 1. Auto-Hide Hook (`hooks/speed-reading/use-auto-hide.ts`)

```typescript
import { useState, useEffect, useCallback, useRef } from 'react';

interface UseAutoHideOptions {
  /** Time in ms before hiding (default: 3000) */
  delay?: number;
  /** Whether auto-hide is enabled */
  enabled?: boolean;
}

export function useAutoHide({ delay = 3000, enabled = true }: UseAutoHideOptions = {}) {
  const [isVisible, setIsVisible] = useState(true);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const show = useCallback(() => {
    setIsVisible(true);

    // Clear existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    // Set new hide timeout
    if (enabled) {
      timeoutRef.current = setTimeout(() => {
        setIsVisible(false);
      }, delay);
    }
  }, [delay, enabled]);

  const hide = useCallback(() => {
    setIsVisible(false);

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
  }, []);

  // Track mouse movement
  useEffect(() => {
    if (!enabled) {
      setIsVisible(true);
      return;
    }

    const handleMouseMove = () => {
      show();
    };

    const handleMouseLeave = () => {
      // Start hide timer when mouse leaves
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      timeoutRef.current = setTimeout(() => {
        setIsVisible(false);
      }, delay);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseleave', handleMouseLeave);

    // Initial hide timer
    show();

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseleave', handleMouseLeave);
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [delay, enabled, show]);

  return {
    isVisible,
    show,
    hide,
  };
}
```

### 2. Reader Keyboard Hook (`hooks/speed-reading/use-reader-keyboard.ts`)

```typescript
import { useEffect, useCallback } from 'react';

interface UseReaderKeyboardOptions {
  onToggle: () => void;
  onRewind: (seconds: number) => void;
  onForward?: (seconds: number) => void;
  onAdjustWpm: (delta: number) => void;
  onExit: () => void;
  enabled?: boolean;
}

export function useReaderKeyboard({
  onToggle,
  onRewind,
  onForward,
  onAdjustWpm,
  onExit,
  enabled = true,
}: UseReaderKeyboardOptions) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!enabled) return;

      // Don't capture if in input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      switch (e.key) {
        case ' ':
          e.preventDefault();
          onToggle();
          break;

        case 'ArrowLeft':
          e.preventDefault();
          if (e.shiftKey) {
            onRewind(30);
          } else if (e.altKey) {
            onRewind(15);
          } else {
            onRewind(10);
          }
          break;

        case 'ArrowRight':
          e.preventDefault();
          if (onForward) {
            if (e.shiftKey) {
              onForward(30);
            } else if (e.altKey) {
              onForward(15);
            } else {
              onForward(10);
            }
          }
          break;

        case 'ArrowUp':
          e.preventDefault();
          onAdjustWpm(25);
          break;

        case 'ArrowDown':
          e.preventDefault();
          onAdjustWpm(-25);
          break;

        case 'Escape':
          e.preventDefault();
          onExit();
          break;

        // Number keys for quick rewind
        case '1':
          e.preventDefault();
          onRewind(10);
          break;
        case '2':
          e.preventDefault();
          onRewind(15);
          break;
        case '3':
          e.preventDefault();
          onRewind(30);
          break;
      }
    },
    [enabled, onToggle, onRewind, onForward, onAdjustWpm, onExit]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
}
```

### 3. Reader Controls Overlay (`components/reader-controls.tsx`)

```typescript
import { X, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAutoHide } from '@/hooks/speed-reading/use-auto-hide';
import { PlaybackControls } from './playback-controls';
import { WpmControl } from './wpm-control';
import { RampControl } from './ramp-control';
import { cn } from '@/lib/utils';

interface ReaderControlsProps {
  isPlaying: boolean;
  effectiveWpm: number;
  targetWpm: number;
  rampEnabled: boolean;
  rampSeconds: number;
  onPlayPause: () => void;
  onRewind: (seconds: number) => void;
  onWpmChange: (wpm: number) => void;
  onRampToggle: (enabled: boolean) => void;
  onRampSecondsChange: (seconds: number) => void;
  onExit: () => void;
}

export function ReaderControls({
  isPlaying,
  effectiveWpm,
  targetWpm,
  rampEnabled,
  rampSeconds,
  onPlayPause,
  onRewind,
  onWpmChange,
  onRampToggle,
  onRampSecondsChange,
  onExit,
}: ReaderControlsProps) {
  const { isVisible } = useAutoHide({
    delay: 3000,
    enabled: isPlaying,
  });

  return (
    <>
      {/* Top bar - exit and settings */}
      <div
        className={cn(
          'absolute top-0 left-0 right-0 p-4 flex justify-between items-center',
          'transition-opacity duration-300',
          isVisible ? 'opacity-100' : 'opacity-0 pointer-events-none'
        )}
      >
        <Button
          variant="ghost"
          size="icon"
          className="text-white/70 hover:text-white hover:bg-white/10"
          onClick={onExit}
        >
          <X className="h-6 w-6" />
        </Button>

        <div className="flex items-center gap-4">
          <RampControl
            enabled={rampEnabled}
            seconds={rampSeconds}
            onToggle={onRampToggle}
            onSecondsChange={onRampSecondsChange}
          />
        </div>
      </div>

      {/* Bottom bar - playback controls */}
      <div
        className={cn(
          'absolute bottom-0 left-0 right-0 p-6',
          'bg-gradient-to-t from-black/80 to-transparent',
          'transition-opacity duration-300',
          isVisible ? 'opacity-100' : 'opacity-0 pointer-events-none'
        )}
      >
        <div className="max-w-2xl mx-auto space-y-4">
          {/* WPM Control */}
          <WpmControl
            effectiveWpm={effectiveWpm}
            targetWpm={targetWpm}
            onChange={onWpmChange}
          />

          {/* Playback buttons */}
          <PlaybackControls
            isPlaying={isPlaying}
            onPlayPause={onPlayPause}
            onRewind={onRewind}
          />
        </div>
      </div>

      {/* Status indicator (always visible when paused) */}
      {!isPlaying && (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 mt-24">
          <span className="text-sm text-white/50 font-medium tracking-wider">
            PAUSED
          </span>
        </div>
      )}
    </>
  );
}
```

### 4. Playback Controls (`components/playback-controls.tsx`)

```typescript
import { Play, Pause, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface PlaybackControlsProps {
  isPlaying: boolean;
  onPlayPause: () => void;
  onRewind: (seconds: number) => void;
}

export function PlaybackControls({
  isPlaying,
  onPlayPause,
  onRewind,
}: PlaybackControlsProps) {
  return (
    <div className="flex items-center justify-center gap-4">
      {/* Rewind 30s */}
      <Button
        variant="ghost"
        size="sm"
        className="text-white/70 hover:text-white hover:bg-white/10"
        onClick={() => onRewind(30)}
      >
        <RotateCcw className="h-4 w-4 mr-1" />
        30s
      </Button>

      {/* Rewind 15s */}
      <Button
        variant="ghost"
        size="sm"
        className="text-white/70 hover:text-white hover:bg-white/10"
        onClick={() => onRewind(15)}
      >
        <RotateCcw className="h-4 w-4 mr-1" />
        15s
      </Button>

      {/* Rewind 10s */}
      <Button
        variant="ghost"
        size="sm"
        className="text-white/70 hover:text-white hover:bg-white/10"
        onClick={() => onRewind(10)}
      >
        <RotateCcw className="h-4 w-4 mr-1" />
        10s
      </Button>

      {/* Play/Pause */}
      <Button
        size="lg"
        className="h-14 w-14 rounded-full bg-white/10 hover:bg-white/20 text-white"
        onClick={onPlayPause}
      >
        {isPlaying ? (
          <Pause className="h-6 w-6" />
        ) : (
          <Play className="h-6 w-6 ml-1" />
        )}
      </Button>

      {/* Spacer for symmetry */}
      <div className="w-[180px]" />
    </div>
  );
}
```

### 5. WPM Control (`components/wpm-control.tsx`)

```typescript
import { Minus, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';

interface WpmControlProps {
  effectiveWpm: number;
  targetWpm: number;
  onChange: (wpm: number) => void;
}

export function WpmControl({ effectiveWpm, targetWpm, onChange }: WpmControlProps) {
  const handleDecrease = () => {
    onChange(Math.max(100, targetWpm - 25));
  };

  const handleIncrease = () => {
    onChange(Math.min(1500, targetWpm + 25));
  };

  const isRamping = effectiveWpm !== targetWpm;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-white/50">Speed</span>
        <div className="flex items-center gap-2">
          <span className="text-white font-mono tabular-nums">
            {effectiveWpm} WPM
          </span>
          {isRamping && (
            <span className="text-white/50">→ {targetWpm}</span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-white/70 hover:text-white hover:bg-white/10"
          onClick={handleDecrease}
        >
          <Minus className="h-4 w-4" />
        </Button>

        <Slider
          value={[targetWpm]}
          min={100}
          max={1500}
          step={25}
          onValueChange={([value]) => onChange(value)}
          className="flex-1"
        />

        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-white/70 hover:text-white hover:bg-white/10"
          onClick={handleIncrease}
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      {/* Quick presets */}
      <div className="flex justify-center gap-2">
        {[200, 300, 400, 500, 600].map((preset) => (
          <Button
            key={preset}
            variant="ghost"
            size="sm"
            className={`text-xs px-2 h-6 ${
              targetWpm === preset
                ? 'text-white bg-white/20'
                : 'text-white/50 hover:text-white hover:bg-white/10'
            }`}
            onClick={() => onChange(preset)}
          >
            {preset}
          </Button>
        ))}
      </div>
    </div>
  );
}
```

### 6. Ramp Control (`components/ramp-control.tsx`)

```typescript
import { Zap } from 'lucide-react';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Slider } from '@/components/ui/slider';
import { Button } from '@/components/ui/button';

interface RampControlProps {
  enabled: boolean;
  seconds: number;
  onToggle: (enabled: boolean) => void;
  onSecondsChange: (seconds: number) => void;
}

export function RampControl({
  enabled,
  seconds,
  onToggle,
  onSecondsChange,
}: RampControlProps) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className={`text-white/70 hover:text-white hover:bg-white/10 gap-2 ${
            enabled ? 'text-primary' : ''
          }`}
        >
          <Zap className={`h-4 w-4 ${enabled ? 'fill-current' : ''}`} />
          Ramp
          {enabled && <span className="text-xs">({seconds}s)</span>}
        </Button>
      </PopoverTrigger>

      <PopoverContent className="w-72 bg-zinc-900 border-zinc-800" align="end">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-white">Build-up Mode</Label>
              <p className="text-xs text-white/50">
                Start slow and increase to target speed
              </p>
            </div>
            <Switch checked={enabled} onCheckedChange={onToggle} />
          </div>

          {enabled && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-white/50">Ramp Duration</span>
                <span className="text-white font-mono">{seconds}s</span>
              </div>
              <Slider
                value={[seconds]}
                min={0}
                max={60}
                step={5}
                onValueChange={([value]) => onSecondsChange(value)}
              />
              <div className="flex justify-between text-xs text-white/30">
                <span>0s (instant)</span>
                <span>60s</span>
              </div>
            </div>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}
```

### 7. Progress Indicator (`components/reader-progress.tsx`)

```typescript
import { Progress } from '@/components/ui/progress';

interface ReaderProgressProps {
  progress: number;
  currentIndex: number;
  totalWords: number;
}

export function ReaderProgress({
  progress,
  currentIndex,
  totalWords,
}: ReaderProgressProps) {
  return (
    <div className="px-6 py-3 bg-black/50">
      <div className="max-w-4xl mx-auto space-y-1">
        <Progress value={progress} className="h-1 bg-white/10" />
        <div className="flex justify-between text-xs text-white/50">
          <span>
            {currentIndex.toLocaleString()} / {totalWords.toLocaleString()} words
          </span>
          <span>{progress.toFixed(1)}%</span>
        </div>
      </div>
    </div>
  );
}
```

---

## Updated Reader Page with Full Controls

```typescript
// Update speed-reading-reader/index.tsx
import { useCallback } from 'react';
import { useNavigate, useParams } from '@tanstack/react-router';
import { useSession } from '@/hooks/speed-reading/use-sessions';
import { usePlaybackEngine } from '@/hooks/speed-reading/use-playback-engine';
import { useAutoSave } from '@/hooks/speed-reading/use-auto-save';
import { useReaderKeyboard } from '@/hooks/speed-reading/use-reader-keyboard';
import { useSpeedReadingStore } from '@/store/speed-reading-store';
import { WordDisplay } from './components/word-display';
import { ReaderControls } from './components/reader-controls';
import { ReaderProgress } from './components/reader-progress';

export function SpeedReadingReader() {
  const navigate = useNavigate();
  const { sessionId } = useParams({ from: '/speed-reading/reader/$sessionId' });
  const { settings, setTargetWpm, setRampEnabled, setRampSeconds } = useSpeedReadingStore();

  const { data: session, isLoading: sessionLoading } = useSession(sessionId);

  const engine = usePlaybackEngine({
    documentId: session?.document_id ?? '',
    totalWords: session?.total_words ?? 0,
    initialWordIndex: session?.current_word_index ?? 0,
    targetWpm: settings.targetWpm,
    rampEnabled: settings.rampEnabled,
    rampSeconds: settings.rampSeconds,
  });

  const autoSave = useAutoSave({
    sessionId,
    currentWordIndex: engine.currentWordIndex,
    progress: engine.progress,
    enabled: !!session,
  });

  const handleExit = useCallback(async () => {
    engine.pause();
    await autoSave.saveNow();
    navigate({ to: '/speed-reading' });
  }, [engine, autoSave, navigate]);

  const handleWpmChange = useCallback((wpm: number) => {
    setTargetWpm(wpm);
    // Engine will pick up new value on next tick
  }, [setTargetWpm]);

  // Register keyboard shortcuts
  useReaderKeyboard({
    onToggle: engine.toggle,
    onRewind: engine.rewind,
    onAdjustWpm: (delta) => handleWpmChange(settings.targetWpm + delta),
    onExit: handleExit,
    enabled: true,
  });

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

      {/* Controls Overlay */}
      <ReaderControls
        isPlaying={engine.isPlaying}
        effectiveWpm={engine.effectiveWpm}
        targetWpm={settings.targetWpm}
        rampEnabled={settings.rampEnabled}
        rampSeconds={settings.rampSeconds}
        onPlayPause={engine.toggle}
        onRewind={engine.rewind}
        onWpmChange={handleWpmChange}
        onRampToggle={setRampEnabled}
        onRampSecondsChange={setRampSeconds}
        onExit={handleExit}
      />
    </div>
  );
}
```

---

## Keyboard Shortcuts Reference

| Key       | Action             |
| --------- | ------------------ |
| `Space`   | Play/Pause         |
| `←`       | Rewind 10s         |
| `Alt+←`   | Rewind 15s         |
| `Shift+←` | Rewind 30s         |
| `↑`       | Increase WPM by 25 |
| `↓`       | Decrease WPM by 25 |
| `1`       | Rewind 10s         |
| `2`       | Rewind 15s         |
| `3`       | Rewind 30s         |
| `Escape`  | Exit reader        |

---

## Verification Checklist

### Auto-Hide

- [ ] Controls visible on mouse move
- [ ] Controls hide after 3s inactivity during playback
- [ ] Controls stay visible when paused
- [ ] Smooth fade transition

### Keyboard Shortcuts

- [ ] Space toggles play/pause
- [ ] Arrow keys work for rewind/WPM
- [ ] Modifier keys (Shift/Alt) change rewind amount
- [ ] Number keys work for quick rewind
- [ ] Escape exits reader

### WPM Control

- [ ] Slider adjusts WPM
- [ ] +/- buttons adjust by 25
- [ ] Presets work
- [ ] Shows effective vs target when ramping

### Ramp Control

- [ ] Toggle enables/disables ramp
- [ ] Duration slider works
- [ ] Settings persist in store

---

## Next: Session 9 - Session Persistence

Session 9 adds:

- Auto-save progress every 10s
- Save on pause
- Save on page unload
- Recent sessions list
- Continue reading functionality
