# Future Feature: PDF Upload

## Status

Deferred (not included in the initial web-only implementation).

## Decision

The initial Speed Reading (DeepRead) integration will support **web-only usage** and will **not** include PDF upload.

PDF support will be revisited after the core RSVP reading flow is stable and deployed.

## Rationale

- PDF ingestion typically introduces extra complexity (parsing quality, encoding issues, layout artifacts, extraction failures).
- PDF parsing often pulls in heavier/native dependencies and increases security hardening needs (file validation, size limits, sandboxing).
- Deferring PDF keeps the first release focused on the core reading experience and makes cloud deployment simpler.

## Current Scope (v1)

- Import via **paste text** (and/or other non-PDF inputs as planned).
- Document preview, start selection, RSVP reader, session persistence.

## Future Scope (vNext)

When we add PDF upload, we should implement:

- Backend: `POST /api/documents/from-file` accepting PDFs with strict validation:
  - Max file size, content-type sniffing, allowlist extensions.
  - Robust extraction with clear error messages and metrics.
- UI: PDF upload option in import page with progress + failure states.
- Ops: security review + abuse controls (rate limiting, timeouts), plus cloud storage strategy if needed.
