# Session 4: Sessions & Navigation API (Python Backend)

**Session Document:** `/Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/sessions/SESSION-04-sessions-navigation-api.md`

---

## Prompt

You are implementing Session 4 of the Speed Reading System (DeepRead) for the Automaker project.

FIRST, read these two files completely:

1. Main README: /Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/README.md
2. Your session document: /Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/sessions/SESSION-04-sessions-navigation-api.md

KEY CONTEXT:

- Sessions 1-3 are complete - the backend is nearly complete
- This session completes the Python backend
- After this, frontend sessions begin
- Ramp start WPM = 50% of target WPM
- Sessions have 7-day fixed retention from creation

PREREQUISITES TO VERIFY:

- Check that document endpoints work
- Check that token endpoints work

YOUR TASK:

1. Read both documents fully before starting
2. Create SessionService and NavigationService
3. Implement session API endpoints:
   - POST /api/sessions (create)
   - GET /api/sessions/recent (list, sorted by created_at DESC)
   - GET /api/sessions/{id} (get by ID)
   - GET /api/sessions/document/{id}/latest (for "Continue Reading")
   - PATCH /api/sessions/{id}/progress (update, does NOT extend expiry)
   - DELETE /api/sessions/{id}
4. Implement resolve-start endpoint:
   - POST /api/documents/{id}/resolve-start (snap to sentence/paragraph/heading)
5. Implement background cleanup task for expired sessions
6. Run all verification checklist items

DELIVERABLE: Complete backend API with session CRUD, progress tracking, and navigation resolution.

---

## Important Notes

1. **Read Both Documents First**: Read the main README and your session document before starting any implementation.

2. **Code Organization**: Python backend code goes in `4.Speed Reading System/backend/`.

3. **Compatibility**: Verify that Sessions 1-3 deliverables exist and work correctly before implementing.

4. **Verification**: The session document has a verification checklist - all items must pass before the session is complete.
