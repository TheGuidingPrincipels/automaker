# Session 7: Reader Engine (React/TypeScript)

**Session Document:** `/Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/sessions/SESSION-07-REVISED-reader-engine.md`

---

## Prompt

You are implementing Session 7 of the Speed Reading System (DeepRead) for the Automaker project.

FIRST, read these two files completely:

1. Main README: /Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/README.md
2. Your session document: /Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/sessions/SESSION-07-REVISED-reader-engine.md

KEY CONTEXT:

- Sessions 5-6 are complete - import and preview work
- This is the core RSVP playback engine (most complex session)
- Timing loop is frontend-only; tokens come from backend
- Uses requestAnimationFrame for smooth timing

PREREQUISITES TO VERIFY:

- Check that import flow works (can create documents)
- Check that preview works (can see text and click words)
- Check that sessions can be created via API

YOUR TASK:

1. Read both documents fully before starting
2. Create timing utilities (lib/speed-reading/timing.ts, ramp.ts)
3. Create core hooks:
   - useTokenCache (token chunk prefetching)
   - usePlaybackHistory (ring buffer for rewind)
   - useRamp (WPM ramp calculation)
   - usePlaybackEngine (main timing loop)
4. Create display components:
   - WordDisplay (ORP-aligned word rendering)
   - ReaderOverlay (fullscreen dark reader)
   - ReaderProgress (progress bar)
5. Create the SpeedReadingReader page component
6. Implement play/pause/seek/rewind
7. Run all verification checklist items

DELIVERABLE: Core RSVP reader with ORP display, token caching, ramp mode, and time-based rewind.

---

## Important Notes

1. **Read Both Documents First**: Read the main README and your session document before starting any implementation.

2. **Code Organization**: Frontend code goes in Automaker's `apps/ui/src/`.

3. **Compatibility**: Verify that Sessions 5-6 deliverables exist and work correctly before implementing.

4. **Verification**: The session document has a verification checklist - all items must pass before the session is complete.

5. **Backend Must Be Running**: The Python backend must be running on port 8001.
