# Session 8: Reader Controls (React/TypeScript)

**Session Document:** `/Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/sessions/SESSION-08-REVISED-reader-controls.md`

---

## Prompt

You are implementing Session 8 of the Speed Reading System (DeepRead) for the Automaker project.

FIRST, read these two files completely:

1. Main README: /Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/README.md
2. Your session document: /Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/sessions/SESSION-08-REVISED-reader-controls.md

KEY CONTEXT:

- Session 7 is complete - reader engine works
- You are adding the control overlay UI
- Controls auto-hide during playback (3s timeout)
- Full keyboard shortcut support

PREREQUISITES TO VERIFY:

- Check that reader engine works (play/pause/rewind)
- Check that tokens display correctly
- Check that ORP alignment works

YOUR TASK:

1. Read both documents fully before starting
2. Create auto-hide hook (use-auto-hide.ts)
3. Create keyboard hook (use-reader-keyboard.ts)
4. Create control components:
   - ReaderControls (auto-hiding overlay)
   - PlaybackControls (Play/Pause/Rewind buttons)
   - WpmControl (slider + presets)
   - RampControl (toggle + duration popover)
5. Implement full keyboard shortcuts:
   - Space: play/pause
   - Arrow Left: rewind (10/15/30s with modifiers)
   - Arrow Up/Down: WPM +/-25
   - 1/2/3: quick rewind
   - Escape: exit
6. Run all verification checklist items

DELIVERABLE: Full reader control UI with auto-hiding, keyboard shortcuts, and WPM/ramp adjustments.

---

## Important Notes

1. **Read Both Documents First**: Read the main README and your session document before starting any implementation.

2. **Code Organization**: Frontend code goes in Automaker's `apps/ui/src/`.

3. **Compatibility**: Verify that Session 7 deliverables exist and work correctly before implementing.

4. **Verification**: The session document has a verification checklist - all items must pass before the session is complete.

5. **Backend Must Be Running**: The Python backend must be running on port 8001.
