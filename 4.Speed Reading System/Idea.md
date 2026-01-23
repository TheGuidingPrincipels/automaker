## Key decisions locked in (so the plan is internally consistent)

- **Option B (chunked tokens)**: backend stores tokens; frontend fetches chunks around the current index and prefetches ahead/behind.
- **Rewind is time-based**, not word-based: 10s / 15s / 30s (implemented via playback history ring buffer).
- **Build-up (ramp) mode**: start at ~50% of target WPM (e.g., 300 → 600) and linearly ramp over 30s (configurable 0–60s).
- **Inputs**: paste text + upload `.md` + upload `.pdf` (best effort extraction).
- **Languages**: English + German (user selects at ingest time).
- **Persistence**: documents persist until deleted; **sessions/history auto-expire after 7 days**.
- **Single active reader** assumption (but architecture won’t break if you later allow multiple).

---

## Stress-test (pushback) — the 4 real risks you’re signing up for

1. **“Click a word in full preview to start there” is expensive at scale**
   Rendering every word as a clickable span can choke on large docs (PDF books). Mitigation in plan: **virtualized preview** + chunked token retrieval; only render what’s on screen.

2. **PDF text extraction is not deterministic**
   Layout artifacts, broken hyphenation, missing paragraph boundaries. Mitigation: best-effort extraction + normalization heuristics + user-visible warnings.

3. **Time-based rewind must stay correct under ramp + live WPM changes**
   If you try to “compute” rewind purely from multipliers, it will drift. Mitigation: **record actual playback history** (elapsed reading time → word index mapping) and rewind by that.

4. **ORP alignment is easy only with monospace**
   Proportional fonts need measurement (canvas `measureText`) to be pixel-accurate. Mitigation: v1 defaults to a monospace font for alignment correctness; add proportional-font support later if needed.

---

# DeepRead (RSVP Speed-Reading) — Refined Full-Stack Plan (Backend-First, React Frontend Later)

## 1) Objective and scope (v1)

### Primary objective

Enable users to **consume text faster** using RSVP: one word at a time, fixed focal point (ORP alignment), high-contrast black reader mode.

### Supported inputs (v1)

1. **Paste text** into a textbox (plain text).
2. **Upload Markdown** (`.md`).
3. **Upload PDF** (`.pdf`) (best-effort extraction).

### Supported languages (v1)

- **English**
- **German**
  User selects language at ingest time.

### Persistence (v1)

- Documents persist until deleted.
- Reading sessions and progress history persist for **7 days** (auto-expire).

### Non-goals (v1)

- Multi-user accounts/auth (design hooks exist; implement later if needed).
- Rich Markdown rendering in preview (preview is plain-text/structured for v1).
- EPUB/HTML ingestion.

---

## 2) Product requirements (functional)

### 2.1 Core reading modes

#### A) Preview mode (before Start)

- Show **full extracted/normalized text** in a scrollable view.
- User can:
  - Scroll to a section.
  - Use a **progress bar** to jump to ~X% of the document.
  - **Click a word** to set the starting position.

- “Start reading” begins at:
  - the clicked word, if selected, else
  - the scrubbed location, snapped to a **sentence start** (or paragraph/heading start based on preference).

#### B) Reader mode (during playback)

- Full-screen (or page-contained overlay) **black background**.
- Display one word at a time, ORP-aligned.
- Overlay controls (auto-hide):
  - Play/Pause
  - Rewind by time: **10s / 15s / 30s**
  - (Optional) Forward by time: 10s / 15s / 30s
  - WPM target control
  - Ramp/build-up toggle + duration
  - Scrubber/progress

- Keyboard shortcuts:
  - Space: Play/Pause
  - ← / →: Rewind/Forward (10s default; Shift modifies to 30s)
  - ↑ / ↓: ±25 WPM (updates target WPM; ramp recalculates)
  - Esc: Exit Reader mode back to Preview

### 2.2 Build-up (ramp) mode

If enabled:

- User chooses **Target WPM** (e.g., 600).
- Playback starts at **Start WPM** (default: max(100, round(0.5 × target))).
- Over **Ramp Duration** (default 30s; configurable 0–60s), WPM increases smoothly to target.
- Ramp applies at session start (optional later: also after long pauses).

### 2.3 Session resume + history

- “Continue reading” resumes last position for a document.
- “Recent sessions (7 days)” shows: document title, last %, last opened.
- Auto-save progress:
  - on pause
  - every N seconds during playback (e.g., 10s)
  - on unload (best-effort)

---

## 3) System architecture (Option B: chunked tokens)

### 3.1 High-level components

**Frontend**

- React 19 + TypeScript 5.9
- Vite 7
- TanStack Router (file-based)
- Tailwind CSS 4
- Radix UI + shadcn/ui

Responsibilities:

- Preview UI (text + word selection + scrubber)
- Reader UI (ORP rendering + controls)
- Playback engine (timing loop, ramp, rewind)
- Token cache + prefetch (chunk window around current index)

**Backend**

- Python 3.11+ + FastAPI
- Parsing + normalization (MD/PDF)
- Tokenization + ORP calculation
- Persistence (documents, tokens, sessions)
- Chunk retrieval endpoints
- “Resolve start index” endpoint (snap to sentence/paragraph/heading start)

**Database**

- Local dev: SQLite
- VM deployment: Postgres (same schema)
- Migrations: Alembic

**Background job**

- Cleanup expired sessions (>7 days)

### 3.2 Data flow (v1)

1. User uploads/pastes + selects language
2. Backend parses → normalizes → tokenizes → stores Document + Tokens
3. Frontend shows Preview (fetch preview + anchors)
4. User selects start → starts session
5. Reader pulls chunks on demand; playback renders + saves progress
6. Session history auto-expires after 7 days

---

## 4) Data model (proposed)

### 4.1 Tables

**documents**

- id (uuid)
- title
- source_type (“paste” | “md” | “pdf”)
- language (“en” | “de”)
- original_filename (nullable)
- original_text (optional)
- normalized_text (text)
- tokenizer_version (string)
- total_words (int)
- created_at, updated_at

**tokens** (word-level tokens; indices 0..total_words-1)

- document_id (uuid, indexed)
- word_index (int, indexed)
- display_text (string) # includes punctuation/quotes
- clean_text (string) # stripped for ORP computation
- orp_index_display (int) # index into display_text
- delay_multiplier_after (float) # pause after this word
- break_before (nullable enum) # “paragraph” | “heading” | null
- is_sentence_start (bool)
- is_paragraph_start (bool)
- char_offset_start/end (int) # optional mapping into normalized_text

Primary key: (document_id, word_index)

**sessions** (7-day history)

- id (uuid)
- document_id (uuid)
- created_at, updated_at
- expires_at
- target_wpm
- ramp_enabled, ramp_seconds, ramp_start_wpm
- current_word_index
- last_known_percent

> Future multi-user hook: add user_id to documents/sessions.

---

## 5) API contract (chunked tokens)

### 5.1 Ingestion

**POST /api/documents/from-text**
Body: title?, language, text
Returns: document meta (id, total_words)

**POST /api/documents/from-file** (multipart)
Fields: language, file (.md/.pdf)
Returns: document meta

### 5.2 Metadata + preview

**GET /api/documents/{doc_id}** → id/title/language/source_type/total_words/tokenizer_version
**GET /api/documents/{doc_id}/preview** → preview_text (plain) + optional anchors

### 5.3 Token chunks (Option B)

**GET /api/documents/{doc_id}/tokens?start={word_index}&limit={N}**
Returns: meta + range + `tokens: TokenDTO[]`

TokenDTO:

- word_index
- display_text
- orp_index_display
- delay_multiplier_after
- break_before
- is_sentence_start
- is_paragraph_start

### 5.4 Snap-to-boundary (start index resolution)

**POST /api/documents/{doc_id}/resolve-start**
Body: approx_word_index, prefer (sentence|paragraph|heading), direction, window
Returns: resolved_word_index + reason

### 5.5 Sessions (7-day history)

**POST /api/sessions** → create session w/ start index + wpm + ramp settings
**GET /api/sessions/recent?days=7** → list sessions + last progress
**PATCH /api/sessions/{session_id}/progress** → save current index, percent, and settings

---

## 6) Tokenization & timing rules (backend)

### 6.1 Normalization

- Normalize whitespace; preserve paragraph boundaries.
- PDF: conservative hyphen-join; sentence join heuristics.
- German punctuation wrappers „“ »« treated properly.
- Minimal abbreviation list to reduce false sentence breaks (extendable).

### 6.2 Token rules

- Store _words_ as tokens; keep punctuation in `display_text`.
- Compute ORP on `clean_text`, shift by leading punctuation count to get `orp_index_display`.
- Delay multipliers:
  - `. ? ! :` → 2.5×
  - `, ;` → 1.5×
  - long word (>8 letters) → 1.2× (multiplicative)

- Paragraph/heading breaks:
  - mark `break_before` on the next word rather than creating extra DB tokens.

### 6.3 Timing model (frontend)

- Base duration: `T_base = 60,000 / current_WPM`
- Word duration: `T = T_base × delay_multiplier_after`
- break_before handling:
  - insert blank frame before the word: paragraph 3.0×, heading 3.5× (tunable)

---

## 7) Playback engine (frontend)

### 7.1 Token cache

- Maintain cache of:
  - previous chunk(s) (for rewind)
  - current
  - next 1–2 chunks (prefetch)

### 7.2 Timing loop

- requestAnimationFrame scheduling with “expected next change” timestamp.
- Recompute per-word duration using **current_WPM** (ramp-aware).

### 7.3 Ramp function (linear, v1)

- `current_WPM(t) = start + (target-start) × clamp(t/ramp_seconds, 0..1)`
- `t` excludes paused time.

### 7.4 Time-based rewind (10/15/30s)

Use a **playback history ring buffer**:

- Each displayed frame records `{word_index, reading_elapsed_ms_at_start}`
- Rewind N seconds:
  - target_elapsed = now_elapsed − N\*1000
  - binary-search / scan back in history to find nearest entry ≤ target
  - jump to that word_index
  - prefetch around it

Edge case:

- If rewind exceeds recorded history (very early in session), fall back to earliest history entry.

### 7.5 Scrubber jump

- percent p → approx index
- call resolve-start (prefer sentence start)
- jump to resolved index and prefetch

### 7.6 Persistence

- PATCH session progress every ~10s + on pause + on unload.
- Resume from latest session for doc.

---

## 8) Minimal UI structure (React v1)

### Routes

`/deepread`

### Key components

- ImportForm (paste/upload + language)
- PreviewTextVirtualized (scroll + click-word start)
- ReaderOverlay (black background RSVP display)
- ReaderControls (play/pause, rewind, WPM, ramp)
- ProgressScrubber (percent jump, current marker)
- SessionHistory (7 days)

---

## 9) Reliability, limits, safety

- File size limits + parse timeouts.
- Structured logs for ingestion/tokenization.
- PDF extraction warnings (don’t silently fail).

---

## 10) Testing

- Backend: golden tokenizer tests (EN/DE), chunk retrieval, resolve-start correctness.
- Frontend: ramp correctness, time-based rewind correctness, scrubber mapping.
- Manual drift QA: 5–10 minutes continuous playback.

---

## 11) Roadmap (backend-first)

- Phase 0: contracts + schema
- Phase 1: backend MVP (ingest → tokenize → store → chunks → sessions → cleanup)
- Phase 2: frontend harness MVP (preview + reader + ramp + rewind)
- Phase 3: polish (virtualization, shortcuts, session library)
- Phase 4: deployment readiness (Docker, Postgres swap, env config)

---

## 12) Definition of Done (v1)

1. Paste or upload .md/.pdf with EN/DE selection → document created.
2. Preview shows full text; click word to set start.
3. Reader mode blacks out interface; ORP-aligned RSVP works with rhythm pauses.
4. Play/Pause is instant.
5. Rewind by **10/15/30s** works reliably (including with ramp + WPM changes).
6. Scrub to 50% starts near sentence start.
7. Progress saves and resumes; recent sessions visible for 7 days.
