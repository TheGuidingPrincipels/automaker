# Session 5: Frontend Integration (React/TypeScript)

**Session Document:** `/Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/sessions/SESSION-05-REVISED-automaker-integration.md`

---

## Prompt

You are implementing Session 5 of the Speed Reading System (DeepRead) for the Automaker project.

FIRST, read these two files completely:

1. Main README: /Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/README.md
2. Your session document: /Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/sessions/SESSION-05-REVISED-automaker-integration.md

KEY CONTEXT:

- Sessions 1-4 (Python backend) are complete
- NOW you are integrating frontend into Automaker's existing React app
- This is NOT a standalone app - it integrates into existing Automaker patterns
- Frontend goes in apps/ui/src/, backend proxy goes in apps/server/src/

WHAT YOU CREATE IN AUTOMAKER:

- Route files in apps/ui/src/routes/speed-reading\*.tsx
- Components in apps/ui/src/components/views/speed-reading-\*/
- Hooks in apps/ui/src/hooks/speed-reading/
- API client in apps/ui/src/lib/speed-reading/
- Zustand store in apps/ui/src/store/speed-reading-store.ts
- Backend proxy in apps/server/src/routes/deepread/

YOUR TASK:

1. Read both documents fully before starting
2. Add Speed Reading to sidebar navigation (use-navigation.ts)
3. Add Shift+R keyboard shortcut (libs/types/src/settings.ts)
4. Create all route files for /speed-reading/\*
5. Create the main SpeedReadingPage component
6. Create TypeScript types mirroring Python schemas
7. Create API client functions
8. Create Zustand store for reader settings
9. Create backend proxy route (JSON-only, no multipart)
10. Run all verification checklist items

DELIVERABLE: Speed Reading integrated into Automaker with routing, navigation, proxy, and placeholder components.

---

## Important Notes

1. **Read Both Documents First**: Read the main README and your session document before starting any implementation.

2. **Code Organization**: Frontend code goes in Automaker's `apps/ui/src/`. The Express server proxy goes in `apps/server/src/routes/deepread/`.

3. **Compatibility**: Verify that Sessions 1-4 (Python backend) are complete before implementing.

4. **Verification**: The session document has a verification checklist - all items must pass before the session is complete.

5. **Backend Must Be Running**: The Python backend must be running on port 8001.
