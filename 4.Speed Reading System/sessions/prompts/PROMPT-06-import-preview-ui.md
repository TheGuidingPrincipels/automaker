# Session 6: Import & Preview UI (React/TypeScript)

**Session Document:** `/Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/sessions/SESSION-06-REVISED-import-preview.md`

---

## Prompt

You are implementing Session 6 of the Speed Reading System (DeepRead) for the Automaker project.

FIRST, read these two files completely:

1. Main README: /Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/README.md
2. Your session document: /Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/sessions/SESSION-06-REVISED-import-preview.md

KEY CONTEXT:

- Session 5 is complete - routes and navigation work
- Python backend should be running on port 8001
- You are building the Import and Preview UI components
- PDF upload is DEFERRED - only paste text and .md file upload

PREREQUISITES TO VERIFY:

- Check that speed-reading routes exist
- Check that API client exists
- Check that backend proxy works

YOUR TASK:

1. Read both documents fully before starting
2. Create Import page components:
   - ImportForm with tabs for paste/upload
   - TextInput with Copy/Paste/Paste+ buttons and word count
   - FileUpload for .md files (drag-drop)
   - LanguageSelect for EN/DE
3. Create Preview page components:
   - PreviewText with virtualization (react-window)
   - Clickable words for selecting start position
   - ProgressScrubber for jumping to position
   - StartControls for WPM settings and Start button
4. Create query hooks for documents
5. Install dependencies: react-window, @types/react-window
6. Run all verification checklist items

DELIVERABLE: Working import form and document preview with virtualized text and word selection.

---

## Important Notes

1. **Read Both Documents First**: Read the main README and your session document before starting any implementation.

2. **Code Organization**: Frontend code goes in Automaker's `apps/ui/src/`.

3. **Compatibility**: Verify that Session 5 deliverables exist and work correctly before implementing.

4. **Verification**: The session document has a verification checklist - all items must pass before the session is complete.

5. **PDF is Deferred**: PDF upload/parsing is not implemented in v1. Only paste text and .md file contents.

6. **Backend Must Be Running**: The Python backend must be running on port 8001.
