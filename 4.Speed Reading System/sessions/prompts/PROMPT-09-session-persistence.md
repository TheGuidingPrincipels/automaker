# Session 9: Session Persistence (React/TypeScript)

**Session Document:** `/Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/sessions/SESSION-09-REVISED-session-persistence.md`

---

## Prompt

You are implementing Session 9 of the Speed Reading System (DeepRead) for the Automaker project.

FIRST, read these two files completely:

1. Main README: /Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/README.md
2. Your session document: /Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/sessions/SESSION-09-REVISED-session-persistence.md

KEY CONTEXT:

- Sessions 5-8 are complete - reader with controls works
- This is the FINAL frontend session
- After this, the Speed Reading System is feature-complete for v1
- Session 10 (deployment) is deferred

PREREQUISITES TO VERIFY:

- Check that reader works end-to-end
- Check that backend sessions API works
- Check that progress updates save correctly

YOUR TASK:

1. Read both documents fully before starting
2. Create session query hooks (use-sessions.ts)
3. Create auto-save hook (use-auto-save.ts):
   - Save every 10 seconds during playback
   - Save on pause
   - Save on WPM change
4. Create before-unload hook (use-before-unload.ts):
   - Best-effort save on page close/refresh
   - Save on visibility change
5. Create session list components:
   - RecentSessions (session list)
   - SessionCard (individual card with progress)
   - DeleteSessionDialog (confirmation)
6. Update main page with recent sessions list
7. Update reader to use auto-save
8. Install date-fns for time formatting
9. Run all verification checklist items

DELIVERABLE: Full session persistence with auto-save, resume, recent sessions list, and "Continue Reading" functionality.

---

## Important Notes

1. **Read Both Documents First**: Read the main README and your session document before starting any implementation.

2. **Code Organization**: Frontend code goes in Automaker's `apps/ui/src/`.

3. **Compatibility**: Verify that Sessions 5-8 deliverables exist and work correctly before implementing.

4. **Verification**: The session document has a verification checklist - all items must pass before the session is complete.

5. **Backend Must Be Running**: The Python backend must be running on port 8001.

6. **Final Session**: This completes the v1 Speed Reading System. Session 10 (deployment) is deferred.
