# CareerKit — Implementation Design (JD-first)

> Concrete implementation plan for the architecture in `system-design.md`.
> That file (plus `session-learnings.md`) is the authority on WHY; this file is
> the authority on WHAT gets built, in what order, with what tests.
> Rev 2 (2026-07-01, Tony-confirmed): pivoted to the JD-first workflow and added
> the non-traditional-path rules. Rev 1's gap-interview component is built and
> its go/no-go regression passes; the pivot reorders the workflow around it and
> adds deltas — it does not discard it.

## Goals, in priority order

1. **Get Tony interviews.** Every design decision is tested against real
   applications. Dogfooding is the validation loop.
2. **Portfolio piece.** Falls out of doing (1) in a clean repo: the failure
   analysis, the red-teamed design, the regression test that encodes an
   empirical finding, plus anonymized real runs. No extra machinery.
3. **Possible commercialization — decision DEFERRED** until ~5-10 real
   applications validate the loop. The only commercialization-forced code
   change is a real `llm.py` (standalone operation instead of
   LLM-in-Claude-Code-chat); do not build it before then. Positioning note:
   the sellable thing is the excavation methodology with provenance
   ("defensible resumes"), not another resume generator.

## Framing guard

Ingestion is **propose-and-confirm, never autonomous extract**. Extraction-first
is the v1 failure mode (Claim F1 0.36, hallucination 0.47). Documents jog memory
and surface conflicts; facts enter only through confirmation.

Note: a `career-graph` MCP server exists from the older v2 effort. Reference
material only. Do not retrofit.

## The JD-first workflow (the pivot)

The JD is the entry point. The corpus is not a prerequisite — it is the
**byproduct**: a growing cache of confirmed excavation answers, keyed by
whatever JDs demanded them. Units are reusable across JDs, so the marginal
cost of each application drops. "The system gets faster with every job you
apply to."

```
careerkit start <jd>
  1. Spine bootstrap (one-time, only if spine missing/stale):
       reconciliation interview scoped to roles/orgs/titles/dates/name.
       Minutes, not hours. NEVER skipped, NEVER guessed under deadline
       pressure — every resume needs the skeleton.
  2. JD parse (LLM step in chat, prompts/jd-parse.md) -> parsed JD json.
  3. careerkit gap -> coverage + recovery questions [BUILT].
       Old documents mined per-gap for LEADS (see below).
  4. Gap interview in chat -> new provisional evidence units.
  5. careerkit resume -> draft -> validate -> just-in-time confirm -> send.
```

Why JD-first is the thesis, sharpened: every strong bullet in the reference
run came out because the Figma JD demanded it. A corpus-first process would
never have asked those questions (the "compressed to impressive-but-irrelevant"
failure, session-learnings step 1). Facts recovered against a specific want
are sharper than facts recorded in the abstract.

**Two disciplines JD-first must not relax:**

- **Documents become per-gap leads, tier discipline intact.** For a MISS/THIN,
  old resumes are scanned for candidate leads: "the JD wants X; your 2019
  resume mentions Y — is there a real instance behind it, and when?" The lead
  is SECONDARY (a claim); it becomes evidence only when Tony confirms a
  specific instance. Shortcutting to "the old resume says it, include it"
  rebuilds the slop-laundering machine.
- **Inflation fences become load-bearing.** JD-first captures every fact while
  the user is a motivated witness holding a live application. Keep all of:
  the "did you do X, and when?" framing, the defensibility check, the
  smaller-reading advisory, and provisional-until-finalize (a beat of
  reflection between "remembered while wanting the job" and "goes on paper").

## Non-traditional career paths (design rules, not just a market)

The architecture is structurally an advocacy engine for non-traditional
candidates (GED, self-taught, career changers): credentials are proxies, and
this system deals only in evidence. A self-reported degree is weak evidence; a
published npm package is PRIMARY and independently verifiable. These rules make
that explicit — they serve Tony directly and are the feature set that market
would need anyway:

1. **Credential normalization is a validator-blocked hazard.** Tony's
   AI-processed old resume HALLUCINATED an education entry (community-college
   HS diploma) — the model rounding a profile toward the pattern it expects.
   For non-traditional candidates the "corrections" always point toward
   inventing credentials. HARD RULE: **the education section renders verbatim
   from the spine with zero LLM liberty.** The writer transcribes education,
   never composes it. Deterministic check; the hallucinated-diploma case is
   the regression test.
2. **Requirement kinds.** JD requirements get a `kind`:
   - `capability` — recovery question on MISS/THIN (the existing flow).
   - `credential` — NOT excavatable; no recovery question. Instead a strategy
     note: hard gate or boilerplate ("or equivalent experience" detection),
     plus which adjacent evidence units compensate.
   - `tenure` ("8+ years") — computed deterministically from the spine, never
     vibes. Prove it, don't claim it.
3. **Defensive framing is a slop category.** Alongside atmosphere-poses, the
   semantic critique flags compensatory language: "self-taught fast learner,"
   "no formal degree but...", anything apologizing for or over-explaining the
   path. Reads as insecurity; also self-rating. Fix is the usual one —
   specificity: "tested out of high school by examination; ran technical
   operations for 400+ member companies by 25."
4. **Render policies are user knobs, never LLM judgment:**
   - Education placement per application: bottom-minimal / omitted / present
     (ATS forms sometimes force a value).
   - Earliest-year-shown: compress roles before the cutoff to an "Earlier:"
     line. Age-signal management for older candidates; the same knob prevents
     thin-history padding for younger ones.
5. **Evidence units may carry a public `link`** (repo, npm, published work).
   Verifiable artifacts are the non-traditional candidate's substitute for
   credential shorthand.

## System shape

A small Python CLI package (`careerkit`) operating on flat files in this repo.
No database, no web UI, no services.

- Python 3.12+, pydantic, pytest (TDD-first), ruff, mypy strict, pre-commit,
  Conventional Commits.
- The package is fully deterministic. LLM steps (JD parse, question phrasing,
  document-lead proposal, bullet writing, semantic critique) run in Claude Code
  chat and exchange files with the package (see `prompts/`). A real `llm.py`
  wrapper is deferred to commercialization (see Goals).
- Interviews happen in Claude Code chat: the tool produces question lists and
  coverage analyses as files, Tony answers conversationally, answers are
  written back as provisional evidence units.

## Data model (three files, one derived index) — BUILT

Structured YAML with `career-data.md` as the human-readable narrative
companion. Coverage math and ranking need structured fields; re-parsing
markdown per run would reintroduce nondeterminism where determinism is
required.

### 1. `data/spine.yaml` — the timeline

Identity, roles/orgs/titles/dates with corrections on record, education (with
framing note), render notes. Human-authored. Machine audits and flags — never
writes. Bootstrapped once via the scoped reconciliation interview for a cold
start.

### 2. `data/evidence/*.yaml` — one file per evidence unit

```yaml
id: linkedin-mcdonalds
role: linkedin-tc            # spine ref; null + kind: portfolio-project for projects
narrative: >-
  ...grain + specificity...
car: {challenge: ..., action: ..., result: ...}   # optional
metrics:
  - {value: "$10M program", tier: PRIMARY}
skills: [scim, sso, enterprise-integration]
tier: PRIMARY                # PRIMARY | DOC | MEMORY
status: confirmed            # confirmed | provisional
link: null                   # optional public artifact URL (repo, npm) [PIVOT DELTA]
render_notes:                # framing corrections travel WITH the unit
  - "Frame as 'partnered with engineering', not 'selected first'"
verify: []                   # open [VERIFY] items blocking finalization
```

### 3. `data/skills.yaml` — alias/taxonomy table only

A skill exists iff >=1 unit carries the tag. Proficiency is computed (unit
count x tier diversity x span x recency), displayed, never hand-set. The table
grows by confirmation: unknown JD terms are flagged, never guessed silently.

Single-user throughout; `data/` is the only generality concession.

## Component 1 — Gap interview — BUILT (pivot deltas landed; `careerkit start` doc pending)

`careerkit gap --jd <parsed.json>` [BUILT]

1. JD parse (LLM in chat, `prompts/jd-parse.md`, canonical tags only,
   unknown terms surfaced). [BUILT]
2. Deterministic coverage: MISS (no evidence) / THIN (all support weak:
   MEMORY, provisional, or outside the 10-year recency window measured
   against the spine's newest role — or a single unit) / HIT. Requirement
   status = worst of its skills. [BUILT]
3. Recovery questions, template-constrained: "This role wants X. Your file is
   thin on X. Did you do X, and when?" + specific-instance ask. NEVER "what
   would make you match better". THIN questions name existing evidence to jog
   memory. [BUILT]
4. Answer intake follows a fixed four-beat protocol [workflow, no code needed]:
   **existence -> location -> specifics -> defensibility.**
   Location is answered against the spine (people index memories by era;
   the timeline is the memory coordinate system — this is why the spine is
   the sole prerequisite artifact). Location comes BEFORE specifics so
   follow-ups can use role context. A unit is never created without a role
   ref the user named; placement is an interview OUTPUT, never a guess.
   Sole exception: a document lead may carry its SOURCE document's location,
   provenance shown, still requiring confirmation.
   The answer lands as a provisional MEMORY unit + defensibility check +
   smaller-reading note. Nothing auto-confirms.
5. "Never did that" is a first-class outcome, recorded as negative evidence
   in `data/declined.yaml` ({requirement text, skill tags, date, note}) so
   no future JD re-asks it. Declines feed the strategy note: "this JD wants
   things you've confirmed you haven't done — compensate via X, or skip."
   [PIVOT DELTA — small, deterministic]

**Pivot deltas:**

- `Requirement.kind: capability | credential | tenure` with per-kind handling
  (recovery question / strategy note / spine-computed years). [BUILT —
  `careerkit/strategy.py`]
- Document leads: per-MISS/THIN, an LLM chat step proposes leads from old
  resumes (SECONDARY tier), woven into the recovery question as memory
  joggers. Leads are mined globally per document (one upload fans out to all
  open gaps), and may carry the source document's role location.
  Prompt file: `prompts/document-leads.md`. [BUILT]
- Declined-wants record: `data/declined.yaml` + coverage integration (a
  declined skill is reported as DECLINED, never re-asked, feeds strategy
  notes). [BUILT]
- Optional `link` on evidence units. [BUILT]
- `careerkit start <jd>` orchestration doc for the cold-start path. [OPEN]

### Go/no-go regression — PASSED

`tests/test_regression_figma.py`: real data minus the three excavated units
(McDonald's, CEU, IQVIA) vs the Figma JD reproduces the manual run's gaps
(scim/escalation-management MISS, stakeholder-guidance/sso THIN) with recovery
questions on the right requirements, and the excavated units are exactly what
close them. Non-gaps stay quiet.

## Component 2 — Resume generator (next build)

**Two-register rule (Tony, 2026-07-01):** the living document shown during
wants resolution is an INFORMATIONAL draft — deterministic, templated
directly from evidence-unit fields, zero LLM prose in the interactive loop
(slop-free by construction, instant updates, user confirms facts not
phrasing). The full model (tiers, metrics, links, render notes) accumulates
behind it. Component 2 is the **expert pass** that runs once, at handoff,
when the wants are settled. The finalize ritual applies to the expert
output, where phrasing risk enters.

`careerkit resume <jd.json> --length one-page --register <choice>`

1. **Select + rank (deterministic):** relevance-to-JD-skills -> evidence
   strength (tier + status) -> recency, per-section caps from the length
   budget. The LLM does NOT rank (it ranks by fluency).
2. **Write (constrained LLM, in chat):** sees ONLY selected units (narrative +
   car + metrics + render_notes + link) plus JD summary and register choice.
   Any number not in a source unit renders `[VERIFY]` — enforced by the
   validator, not prompt hope. **Education is transcribed verbatim from the
   spine, never composed** (rule 1 above).
3. **Validate (two lanes):**
   - Mechanical linter (deterministic, BLOCKS): em dashes, banned phrases,
     self-rating phrases, tricolons (with per-bullet `scope-of-work`
     exemption), sentence-length rhythm, numbers-without-source,
     education-matches-spine. Plus `jd-mirroring` (WARN, needs the JD): the
     summary reusing too much of the posting's distinctive vocabulary.
   - Semantic critique (LLM, ADVISORY): atmosphere-poses, defensive/
     compensatory framing (rule 3 above), AND JD-mirroring in the summary.
     Few-shot from session-learnings. Annotates; never blocks.

   **The summary rule (Tony, 2026-08-19).** The summary is the only line with no
   evidence unit under it, and two failure modes live there: atmosphere, and
   paraphrasing the JD. The second is redundant (the bullets already argue fit,
   deterministically), commoditized (every applicant mirrors the same posting),
   and reads eager. The summary's job is the career's TRAJECTORY: where it
   started, its shape, where it is now. Emphasis may shift per target; the JD's
   requirements may not be restated. Tenure comes from the spine.
4. **Draft vs final:** instant drafts from provisional units, visibly
   watermarked. Finalize = just-in-time confirmation of only the marks and
   [VERIFY]s this resume touches. Output markdown -> docx.
5. **Render knobs (user-picked):** length, register, education placement,
   earliest-year-shown.

Regression target: full data + Figma JD produces a draft Tony judges
comparable to `examples/figma-resume-FINAL.docx`.

## Component 3 — Reconciliation, rescoped by the pivot

No longer a standalone bulk-ingest stage. It survives as:

- **(a) Spine bootstrap** (one-time, cold start): diff provided documents for
  spine-level conflicts (dates, names, titles, gaps); bounded question list;
  confirmed answers write the spine.
- **(b) Per-gap document leads** (inside Component 1).

Union + flag conflicts — never vote. Documents are disposable scaffolding.

## Explicit non-goals

- No graph DB, no corpus-build pipeline, no microservices, no web UI.
- No upfront corpus curation stage (the pivot). The spine bootstrap is the
  only prerequisite artifact.
- No auto register classifier; no LLM with blocking authority; no
  frequency/voting corroboration.
- No `llm.py` / standalone operation until the commercialization decision.
- No fact-extraction machinery. If machinery appears in functions 1/2,
  that's the old disease: STOP.

## Build order

1. ~~Data migration to structured units~~ DONE (Tony-confirmed).
2. ~~Gap-interview component + Figma go/no-go regression~~ DONE, PASSED.
3. Gate: Tony evaluates the recovery questions against his memory of the
   manual run. EXERCISED: the Figma gap interview was run in chat, excavating
   three provisional units (rfp-security, support-etl-enablement,
   scim-enterprise) and enriching McDonald's; premise validated a second time.
4. Pivot deltas on Component 1: requirement kinds, tenure computation,
   document-leads prompt, declined-wants state, evidence `link` field. DONE.
   (`careerkit start` flow doc still OPEN; not blocking.)
5. Resume generator: selector/ranker (`select.py`) -> writer brief + prompt
   (`brief.py`, `prompts/resume-write.md`) -> mechanical linter incl.
   education-verbatim (`linter.py`) -> semantic-critique prompt
   (`prompts/resume-critique.md`) -> render knobs. DONE. Plus a finalization
   gate (`finalize.py`, `careerkit finalize`) for the draft->final trust check.
   Plus an optional final de-slop pass (`deslop.py`, `careerkit deslop`,
   Tony-confirmed): deterministic safe rewrites (em dash -> comma, whitespace)
   run like a formatter, so mechanical nits are auto-fixed rather than blocking
   the writer. Judgment slop (unsourced numbers, invented credentials, puffery)
   is never auto-rewritten; it stays with the linter and the semantic critique.
   Pipeline: resume -> write -> deslop -> lint -> critique -> finalize.
6. Dogfood on real applications; anonymized runs feed the portfolio README.
7. Revisit commercialization after ~5-10 real applications.
