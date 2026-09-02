# CareerKit — System Design

> A system that turns multiple inaccurate resumes into one polished, targeted,
> defensible resume. This design is the OUTPUT of a long working session that
> ran the whole pipeline BY HAND on real data, then red-teamed it. It is not
> theory — every principle below was learned by doing it and watching it succeed
> or fail. Read `session-learnings.md` for the evidence behind each claim.

## The one-sentence thesis

This is NOT an extraction system. It is a **memory-excavation system that uses
documents and job descriptions as excavation tools.** The documents are the pick,
not the gold. The gold is in the user's head, and it only comes out through
grounded, iterative conversation.

## Why previous versions failed (and this is different)

Prior attempts (per Tony's history): multi-persona LLM pipelines, adversarial
validators, graph-first architectures, O*NET mapping. Measured results: Claim F1
0.36, hallucination 0.47. They failed because they:
1. Asked autonomous LLM extraction to hit precision AND recall at once, on the one
   problem where the ground truth (the user) is free to query.
2. Treated old resumes as a data source to extract from — but old resumes are
   inaccurate and generic, so extraction just launders old slop.
3. Gave LLMs authority to judge/block, recreating the cost/false-confidence trap.
4. Tried to eliminate iteration, when iteration IS the excavation mechanism.

## Core architectural commitments

### 1. Split recall and precision across the human/machine boundary
The machine proposes with high RECALL (surface everything, tolerate noise). The
human supplies PRECISION (confirm, correct, reject). Never ask one pass to do both.
BUT: human precision degrades under volume (radiologist fatigue). So a deterministic
junk-filter sits between machine-propose and human-review to keep the queue small.

### 2. Documents are disposable scaffolding
Old resumes serve only two functions: (a) surface CONFLICTS to trigger correction,
(b) JOG MEMORY for forgotten specifics. After that, discard them. Never extract
"evidence" from them as if a resume bullet were a fact — it's a prior polished claim.

### 3. Provenance has reliability TIERS, not just existence
- PRIMARY: commits, shipped artifacts, reviews, others' words, contracts, dashboards
- SECONDARY: the user's own old resumes, self-authored bios — these are CLAIMS, not
  evidence. A unit sourced only to secondary material cannot reach "confirmed"
  status without re-grounding or explicit user ownership.
- Span-existence is NOT span-reliability. (Red-team broke the naive version here.)

### 4. The human is the only trust gate. The LLM never has blocking authority.
LLM jobs: PROPOSE (candidates), AUDIT (flag conflicts + argue smaller readings),
WRITE (bullets from selected evidence only). Deterministic code owns: spine parsing,
skill matching, ranking, format-config, mechanical linting. Human owns confirmation.

### 5. The user is a MOTIVATED witness — fence off inflation structurally
Self-confirmation catches hallucination (things that didn't happen) but is blind to
INFLATION (things that happened, tagged bigger). The user's bias points toward
inflation, especially on a live application. Counter-mechanisms:
- Proficiency is DERIVED and displayed, never hand-set. Evidence density is the ceiling.
- A skeptical advisory pass argues the SMALLER reading of every claim. Advisory only.
- New claims from gap interviews get a defensibility check: specific instance? when?
  primary source or memory? Memory-only allowed but MARKED for conscious ownership.

## The two interview types (the heart of the system)

### Reconciliation interview (triggered by document conflicts)
Deterministic diff of provided documents finds disagreements (dates, names, titles,
gaps). LLM phrases them as questions. Bounded, exhaustible, batch-reviewed one theme
at a time. Output: corrected canonical spine + confirmed facts.
LLM authority here: near-zero (just phrasing detected conflicts).

### Gap interview (triggered by a specific JD) — THE LOAD-BEARING COMPONENT
1. Parse JD → required skills, seniority, role-family, title-to-mirror, register.
2. Compute coverage: what the JD wants vs what the evidence file contains.
3. For each MISS, ask the recovery question — framed correctly:
   NOT "what would make you match better" (invites inflation)
   BUT "this role wants X, I don't see it in your file — did you do X, and when?"
4. A recovered answer → new Evidence Unit → defensibility check → marked, added.
This is the move that produced every strong bullet in the session. It converts a
coverage gap into recovered memory. Build this FIRST; it's where value concentrates
and success is uncertain. If it doesn't reliably surface buried specifics, the whole
premise is wrong — learn that cheaply.

## The resume generation pipeline

1. Parse JD (skills, seniority, role-family, title-to-mirror, register).
2. SELECT + RANK evidence units deterministically:
   relevance-to-JD-skill → evidence-strength → recency. LLM does NOT rank
   (it would rank by fluency = confident bullets about irrelevant work).
3. WRITE bullets — LLM sees ONLY selected units. Can't wander with no material to
   wander into. `[VERIFY]` slot for any number not present in the source unit.
4. VALIDATE — two lanes:
   - Mechanical no-slop linter (deterministic, BLOCKS): em dashes, banned phrases,
     tricolons [note: Tony bypasses the no-3-list rule for scope-of-work bullets],
     sentence-length, passive voice.
   - Semantic no-slop critique (LLM, ADVISORY): flags "poses" — clauses describing
     a FEELING of competence rather than a concrete ACTION ("owns the hard part,"
     "staying in the room when it breaks"). Few-shot against Tony's own taste. The
     fix is always: replace atmosphere with specificity.
5. Length is a FUNCTION of context, not a constant. High-volume first screen → one
   dense page. Senior/two-page defensible only if page two is genuinely full.
6. Tone/register = user picks from a short menu (NOT an LLM classifier — deleted in
   red-team, never missed). Title-mirroring matters (Technical Solutions Consultant).
7. Instant DRAFT allowed from provisional/marked units, but visibly labeled.
   Finalize = user consciously clears the marks on the units THIS resume touches
   (just-in-time confirmation, not a corpus-wide gate). No fake "export wall."

## Data model (flat JSON / SQLite — NO graph DB, NO infrastructure)

- **Timeline Spine:** roles/orgs/titles/dates, parent-child refs for concurrency +
  promotions. Human-authored. Machine audits, never writes.
- **Evidence Units:** narrative fragment + optional {challenge, action, result,
  metrics} + skill tags + provenance tier + confirmed/provisional status. Metrics
  carry only source-present numbers; else `[VERIFY]`. A good unit's defining property
  is GRAIN + SPECIFICITY ("guided IT+L&D through franchise-wide integration decisions,
  chased SCIM at unprecedented scale" NOT "anchored the McDonald's engagement").
- **Skills:** nodes; Evidence Units are evidencing edges. No skill without ≥1 unit.
  Proficiency derived (density/diversity/span/recency) + shown, never declared.

## Scope discipline (the anti-over-engineering rule)

Functions 1 (extract facts) and 2 (build timeline) are NOT programs. They are a
well-structured personal data file + an LLM that proposes additions and audits it.
If you find yourself building machinery there, that's the old disease — STOP.
Function 3 (targeted resume) is the only real program. The test for every component:
does it beat what Tony did BY HAND in the reference session? If not, don't build it.

## Build order

1. Gap-interview component (inputs: career-data.md + a JD; outputs: coverage +
   recovery-question list). This is the load-bearing wall and the risky part.
2. Only if (1) proves out: the deterministic resume writer + selection/ranking.
3. The two no-slop lanes (linter + advisory).
4. Reconciliation diff (easy, low-risk, do last).

## Non-goals

- No frequency/voting-based "corroboration" across documents. (Tony's own two resumes
  disagreed on his NAME; repeated facts are often COPIED, not independently confirmed.
  Union + flag-conflicts is right; intersection/voting is wrong.)
- No JD-register auto-classifier. User picks.
- No LLM with blocking authority anywhere.
- No graph database. No microservices. It runs on a laptop for an audience of one.
