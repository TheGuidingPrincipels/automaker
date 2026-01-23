# Session 3: Document Ingestion API (Python Backend)

**Session Document:** `/Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/sessions/SESSION-03-document-ingestion-api.md`

---

## Prompt

You are implementing Session 3 of the Speed Reading System (DeepRead) for the Automaker project.

FIRST, read these two files completely:

1. Main README: /Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/README.md
2. Your session document: /Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/sessions/SESSION-03-document-ingestion-api.md

KEY CONTEXT:

- Sessions 1-2 are complete - database models and tokenizer exist
- You are implementing document API endpoints in "4.Speed Reading System/backend/"
- PDF upload is DEFERRED - only implement paste text and Markdown (.md) file contents
- v1 uses text JSON (browser reads .md files, sends content as text)

PREREQUISITES TO VERIFY:

- Check that tokenizer module exists and works
- Check that database models exist

YOUR TASK:

1. Read both documents fully before starting
2. Create DocumentService in services/document_service.py
3. Implement API endpoints:
   - POST /api/documents/from-text (create from paste or .md content)
   - GET /api/documents/{id} (metadata)
   - GET /api/documents/{id}/preview (full text + anchors)
   - GET /api/documents/{id}/tokens (paginated chunks)
   - DELETE /api/documents/{id}
4. Enforce 20,000 word limit
5. Ensure atomic writes (document + tokens in same transaction)
6. Run all verification checklist items

DELIVERABLE: Working document ingestion API with token storage.

---

## Important Notes

1. **Read Both Documents First**: Read the main README and your session document before starting any implementation.

2. **Code Organization**: Python backend code goes in `4.Speed Reading System/backend/`.

3. **Compatibility**: Verify that Sessions 1-2 deliverables exist and work correctly before implementing.

4. **Verification**: The session document has a verification checklist - all items must pass before the session is complete.

5. **PDF is Deferred**: PDF upload/parsing is not implemented in v1. Only paste text and .md file contents.
