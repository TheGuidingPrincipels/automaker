# System Overview: The Iterative Specification Engine

**System Purpose**
To transmute raw, unstructured feature ideas into rigorously defined, developer-ready documentation through a three-stage recursive process of structuring, questioning, and synthesizing.

**Core Philosophy**
Ideas are not "found" complete; they are "excavated." This system separates the **organization** of the idea from the **exploration** of the idea, ensuring that complexity is managed sequentially rather than simultaneously.

---

## 1. The Three Architects (System Roles)

The system operates using three distinct AI agents (prompts), each with a specific "Prime Directive."

### A. The Intake Architect (The Strategist)

* **Role:** Structure & Roadmap.
* **Input:** The user's "Brain Dump" (messy, unstructured text/audio).
* **Behavior:** Assesses context, clarifies critical blockers only, and breaks the system down into logical "Areas."
* **Output:**
* `raw_idea_v1.md`: The idea organized into a consistent taxonomy.
* `progression.md`: A session-based project roadmap.



### B. The Socratic Idea Architect (The Excavator)

* **Role:** Behavioral Extraction.
* **Input:** Current `raw_idea_vX.md` + `progression.md`.
* **Behavior:** Focuses on 1-2 specific areas per session. Uses "Funnel Questioning" to extract tacit knowledge, edge cases, and user flows. It *never* solves problems; it only reveals them.
* **Output:**
* `open_questions_N.md`: Specific gaps identified that require research or decisions.



### C. The Integration Architect (The Synthesizer)

* **Role:** Coherence & Merge.
* **Input:** Current `raw_idea_vX.md` + Answered `open_questions_N.md`.
* **Behavior:** Merges the answers from the research phase into the main document. It detects contradictions between the original vision and the new research.
* **Output:**
* `raw_idea_v(X+1).md`: The evolved, more detailed specification.
* Updated `progression.md`.



---

## 2. The Operational Workflow

The system functions as a loop.

### Phase 1: Initialization (One-Time)

1. **User Action:** Provides a brain dump to the **Intake Architect**.
2. **System Action:**
* Analyzes complexity.
* Identifies 4-12 distinct functional areas.
* Groups areas into logical "Sessions" (e.g., Core, User Flow, Edge Cases).


3. **Deliverable:** A roadmap (`progression.md`) defining the exploration path.

### Phase 2: The Specification Loop (Recursive)

*This phase repeats for each Session defined in the roadmap.*

**Step A: Exploration (Socratic Architect)**

* User initiates a session (e.g., "Starting Session 1: User Authentication").
* The Architect asks 5-10 targeted questions to define behavior (not tech).
* **Output:** A list of `Open Questions` (OQs) that need answers/decisions.

**Step B: The "Deep Research" Bridge (User/External)**

* *Note: This happens outside the 3 Prompts.*
* The User takes the `open_questions_N.md`.
* The User answers these questions (via research, technical validation, or executive decision).
* **Output:** A completed Markdown file with answers.

**Step C: Synthesis (Integration Architect)**

* User feeds the *Old Idea* + *Answered Questions* to the Integration Architect.
* The Architect weaves the new details into the text, flagging any contradictions.
* **Output:** `raw_idea_v(N+1).md`.

### Phase 3: Finalization

* Once all sessions in `progression.md` are marked "Complete."
* The final `raw_idea` document serves as the "Source of Truth" for the engineering team.

---

## 3. Artifact Lifecycle & Data Flow

Understanding how the files evolve is critical for system maintainers.

| Artifact | Created By | Modified By | Purpose |
| --- | --- | --- | --- |
| **raw_idea_v[X].md** | Intake Architect | Integration Architect | The "Living Specification." Starts as a sketch, ends as a blueprint. **Never edited manually.** |
| **progression.md** | Intake Architect | Integration Architect | The Project Manager. Tracks which areas are "Done" and what is next. |
| **open_questions_[N].md** | Socratic Architect | **User** (Answers) | The Research Packet. Ephemeral documents used to bridge sessions. |
| **session_notes_[N].md** | Socratic/Integration | Read-Only | Audit trail for major pivots or contradictions. |

---

## 4. Decision Points & Logic

**Decision Point 1: The "Context" Gate (Intake)**

* *Condition:* Does the idea have enough distinct parts to split into sessions?
* *If NO:* Intake Architect asks clarifying questions immediately.
* *If YES:* Proceed to roadmap generation.

**Decision Point 2: The "Open Question" Trigger (Socratic)**

* *Condition:* Does the user know the answer *right now* based on past behavior?
* *If YES:* Extract the detail and log it.
* *If NO (Uncertainty/Hypothetical):* Stop questioning on that point. Log it as an `Open Question` for the research phase.

**Decision Point 3: The "Contradiction" Flag (Integration)**

* *Condition:* Does the researched answer conflict with the original raw idea?
* *If YES:* Do not overwrite. Create a `[CONTRADICTION]` block and force the user to resolve it in the next session.

---

# Recommendations & Stress Test

Sir, having analyzed your prompts, I have identified three areas to strengthen the system for robustness.

### 1. The "Deep Research" Gap

**The Issue:** The system relies on a "Deep Research System" (mentioned in handoffs) to answer the Open Questions, but you have not defined a prompt for this. If the user answers these questions lazily, the Integration Architect will integrate low-quality data.
**Recommendation:** Create a **"Research Validator"** prompt (or distinct instructions for yourself). This agent should take the `open_questions.md` and act as a devil's advocate, forcing you to prove your answers technically before they go to Integration.

### 2. Handling "Scope Creep"

**The Issue:** During Socratic exploration, new features often pop up. The current `progression.md` is static.
**Recommendation:** Add a specific instruction to the **Integration Architect**: *"If the answers imply a new functional area not previously listed in progression.md, you must append this new area as a new Session at the end of the roadmap."* This makes the roadmap dynamic.

### 3. The "Definition of Done"

**The Issue:** Socratic questioning can be infinite.
**Recommendation:** Explicitly define "Saturation" in the Socratic Architect's instructions.

* *Current:* "5-10 questions per area."
* *Refinement:* "Stop questioning an area when the user cannot provide behavioral examples without speculating." Speculation is the signal to move to Research.

### Suggested Next Step

Would you like me to draft the **"Research Validator"** prompt to fill the gap between the Socratic output and the Integration input? This would ensure the answers fed into your specification are rigorous.