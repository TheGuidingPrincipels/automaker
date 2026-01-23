# Session 1: Foundation & Schema (Python Backend)

**Session Document:** `/Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/sessions/SESSION-01-foundation-schema.md`

---

## Prompt

You are implementing Session 1 of the Speed Reading System (DeepRead) for the Automaker project.

FIRST, read these two files completely:

1. Main README: /Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/README.md
2. Your session document: /Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/sessions/SESSION-01-foundation-schema.md

KEY CONTEXT:

- This is the FIRST session - you are building the foundation
- ALL Python backend code MUST be stored in "4.Speed Reading System/backend/"
- You are creating: FastAPI skeleton, SQLite database, SQLAlchemy models, Alembic migrations, Pydantic schemas
- The Automaker Express server should ONLY act as a proxy (no business logic there)

YOUR TASK:

1. Read both documents fully before starting
2. Follow the session document's implementation details exactly
3. Create the full directory structure under "4.Speed Reading System/backend/"
4. Implement all database models (Document, Token, ReadingSession)
5. Set up Alembic migrations
6. Create the health check endpoint
7. Set up Docker Compose for local development
8. Run all verification checklist items

DELIVERABLE: A running FastAPI server with health endpoint, database migrations, and Docker setup.

---

## Important Notes

1. **Read Both Documents First**: Read the main README and your session document before starting any implementation.

2. **Code Organization**: Python backend code goes in `4.Speed Reading System/backend/`.

3. **Verification**: The session document has a verification checklist - all items must pass before the session is complete.
