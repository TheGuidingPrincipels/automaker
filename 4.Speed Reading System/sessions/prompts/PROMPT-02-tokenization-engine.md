# Session 2: Tokenization Engine (Python Backend)

**Session Document:** `/Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/sessions/SESSION-02-tokenization-engine.md`

---

## Prompt

You are implementing Session 2 of the Speed Reading System (DeepRead) for the Automaker project.

FIRST, read these two files completely:

1. Main README: /Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/README.md
2. Your session document: /Users/ruben/Documents/GitHub/automaker/4.Speed Reading System/sessions/SESSION-02-tokenization-engine.md

KEY CONTEXT:

- Session 1 is complete - database models and FastAPI skeleton exist
- ALL code goes in "4.Speed Reading System/backend/app/services/tokenizer/"
- You are building: text normalization, tokenization, ORP calculation, delay multipliers, sentence detection
- Follow TDD: write tests first, verify they fail, then implement

PREREQUISITES TO VERIFY:

- Check that Session 1 files exist (database models, FastAPI app, config)
- The tokenizer module should work with the existing Language enum from models

YOUR TASK:

1. Read both documents fully before starting
2. Create the tokenizer module structure
3. Implement: normalizer.py, tokenizer.py, orp.py, timing.py, sentence.py, constants.py
4. Handle English AND German text correctly
5. Implement Markdown best-effort plain text conversion
6. Write comprehensive tests (>90% coverage target)
7. Run all verification checklist items

DELIVERABLE: A tested tokenization module that processes EN/DE text into RSVP-ready tokens.

---

## Important Notes

1. **Read Both Documents First**: Read the main README and your session document before starting any implementation.

2. **Code Organization**: Python backend code goes in `4.Speed Reading System/backend/`.

3. **Compatibility**: Verify that Session 1 deliverables exist and work correctly before implementing.

4. **Verification**: The session document has a verification checklist - all items must pass before the session is complete.
