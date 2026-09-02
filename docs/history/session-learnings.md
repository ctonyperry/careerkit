# Session Learnings — Why the Design Is What It Is

> This file is the empirical backing for `system-design.md`. Each learning came from
> actually running the pipeline by hand on Tony's real data during one long session,
> and watching it succeed or fail. When Claude Code implements the design, these are
> the concrete reference points for "does my implementation reproduce what worked."

## The reference run (what happened, in order)

1. Built a resume from the "memory picture" of Tony (context + summaries). It was
   WEAK — wrong experiences as bullets, generic framing. FAILURE MODE: the memory
   picture had compressed his career to its most IMPRESSIVE facts (McDonald's scale,
   xAPI library) and dropped the RELEVANT ones (customer-facing discovery, security
   conversations). Selection failed because the input was pre-filtered by
   impressiveness, not relevance.

2. Uploaded two real old resumes. They disagreed with each other AND reality:
   - Different NAME (Tony Perry vs Charles A. Perry — both partial truths)
   - IMS start 1999 vs 2000
   - Microsoft 1998 vs 1998–1999
   - AthenaOnline "Present" vs 2017 (both wrong; real answer 2018)
   - One resume was AI-generated FROM the other → "corroboration" was just COPYING
   - The AI-processed one HALLUCINATED an education entry (community-college HS diploma)
   - The valuable facts (McDonald's $10M, CEU, IQVIA) appeared in NEITHER resume
   LEARNING: frequency/voting extraction would surface the generic copied facts and
   bury the rare differentiating ones. It optimizes for exactly the wrong evidence.

3. Tony corrected the conflicts from memory in seconds. → accurate spine. This is
   the reconciliation interview, done by hand. It worked and was fast BECAUSE the
   truth was in his head and cheap to query.

4. Ran a gap analysis against the Figma JD. The JD wanted security-conversation and
   discovery experience. The file was thin. Asking "did you do this?" surfaced the
   McDonald's IT-and-L&D-guidance work that had been COMPRESSED AWAY. Every strong
   bullet on the final resume came from THIS move. THE GAP INTERVIEW IS THE SYSTEM.

5. Grounded the Apple section in real project docs Tony uploaded. The docs CAUGHT two
   things memory would have inflated:
   - Tony recalled "used Playwright"; docs listed Playwright as FUTURE work. (Turned
     out Tony DID do it — the doc was stale — but the check was correct to flag it.)
   - Memory said Apple was "customer-facing"; it was internal IC instrumentation.
   LEARNING: primary sources catch inflation that self-confirmation can't.

6. Iterated ~12 times on the resume. Each pass jogged loose a NEW buried specific:
   the McDonald's franchise context, the CEU three-way brokering, the IQVIA
   data-health ripple, the dBase migration, the one-handed-mobile dice-game UX.
   NONE were written in any document. LEARNING: iteration is not a cost to minimize —
   it IS the excavation mechanism. A perfect first draft would be a WORSE resume
   because it would never trigger the excavation.

## Specific failure/success pairs (regression targets)

| Weak version (memory-built) | Strong version (excavated) | What fixed it |
|---|---|---|
| "Anchored the McDonald's engagement, 2M users, $10M" | "...company-wide rollout to every front-line worker across franchisee-owned stores... guided IT+L&D through integration decisions... chased SCIM at unprecedented scale" | Gap interview asked WHY it was that big |
| "Built xAPI stuff" (fused two projects) | Apple: built a React telemetry library; LinkedIn: USED engineering's library to ship integrations | Asking for specifics separated two distinct facts |
| (missing) | Big Four CEU compliance rescue | Past-conversation recall surfaced it |
| (missing) | IQVIA escalation → data-health initiative | Direct question about escalation experience |
| "used Playwright to test" | "verified signal output end-to-end with Playwright, driving real browser sessions, asserting emitted statements matched activity" | Describe the BEHAVIOR, not the tool |

## Inflation catches (the motivated-witness problem, live)

Tony himself caught these mid-session — the system must reproduce this discipline:
- "Cut analytics payload 93%" → was a design iteration, not a shipped measured result → CUT
- "Selected first from a group of consultants" → over-framed → softened to "partnered with engineering"
- "259K-line enterprise-grade" dice game (prior session) → credibility risk → cut to honest TDD reference
- Apple "customer-facing" → corrected to internal IC instrumentation

## The no-slop learning

When asked "does anything here scream AI," the slop was concentrated in the SUMMARY,
not the bullets. Bullets were clean because they were anchored to concrete facts.
The summary floated because it was atmospheric. The tells were:
- "owns the hard, customer-facing part of..." (the "the hard part" pose)
- "staying in the room when something breaks at scale" (evocative-generic)
- "a hands-on builder who ships production software" (LinkedIn-influencer register)
THE RULE: every clause that describes a FEELING of competence instead of a concrete
ACTION is a slop risk. The fix is always to replace atmosphere with specificity.
Specificity is the enemy of slop — which is also why the bullets were fine.
Mechanical tells absent and good: no em dashes, no accidental tricolons in bullets.

## Format/length learning

- The "just over one page" resume is the WORST shape (reads as "couldn't edit down,
  didn't have enough for two"). Either commit to one dense page or fill two.
- For a high-volume first screen (like Figma), one dense page won on interview-odds logic.
- Length is context-dependent, not a universal rule. Keep a fuller master; send the cut.
- Title-mirroring is real: "Technical Solutions Consultant" mirrors the JD's "Solutions
  Consultant" while staying honest to Tony's actual "Technical Consultant" title.

## The meta-learning

The whole session WAS the reference implementation of the system, executed manually.
The resume is the artifact; the PROCESS that produced it is the spec. When
implementing, the question is never "is this good architecture" — it's "does this
reproduce what the manual run did." If a component can't beat the by-hand result,
it shouldn't exist.

## 2026-08-24 session (Okta / Cash App / Google CE, chat-driven, outside the pipeline)

1. **Cross-JD contamination is real, not hypothetical.** A Cash App cover letter
   acquired "Block being all-in on AI" — a paraphrase of the OKTA JD. Tony caught
   it by asking "where does it say that?"; a web check then showed the sentiment
   happened to be true of Block anyway, which is exactly why this failure class is
   dangerous: plausible bleed survives casual review. RULE: every JD- or
   company-referencing sentence must trace to the JD file on disk or a cited
   source. Paraphrase-from-conversation-memory is banned.

2. **Chat output bypasses every deterministic gate.** A chat-written resume
   exported to Google Drive contained em dashes (house lint) and an invented role
   title ("Architect & Engineer" vs spine "xAPI Specialist"). The linter would
   have blocked both; it never ran because generation happened outside the
   pipeline. RULE: no rendered prose reaches an external destination without
   passing lint + finalize; encode as a skill so chat sessions structurally
   cannot skip it.

3. **Multi-document runs drift without a consistency pass.** The resume said
   Apple "2025 - Present" while the cover letter said "recently wrapped up",
   simultaneously, for the same application. The spine had the answer all along.
   RULE: dates/titles render only from the spine; a cross-document consistency
   check runs over every artifact in a run before export.

4. **A stale or foreign corpus is worse than no corpus.** A connected MCP tool
   (career-graph) was serving a corpus for a DIFFERENT PERSON entirely; any
   generation against it would have been confident, well-formatted, and 100%
   wrong. RULE: corpus-consuming tools verify identity (name + spine hash)
   before generating; mismatch hard-fails.

5. **The corpus design works — the failures were all outside it.** Everything
   generated directly from evidence YAMLs stayed inside defensible bounds across
   three targets, and render_notes caught model-introduced framing errors twice
   ("Sole Technical Owner" heading; "delivery guarantees" overclaim). Strongest
   evidence yet for "the writer sees only selected evidence units."

## 2026-08-25: the first pipeline run (Okta), and what it changed

1. **The adversarial pass is not optional.** On one package: `lint` 0 blocking,
   `finalize` READY, `crosscheck` 0 blocking, and then the skeptic agent found
   SEVEN blocking defects of meaning: a fabricated tenure figure, a decade-level
   date error, two house-rule violations quoted almost verbatim from CLAUDE.md,
   an invented motive, and a metric drawn from a unit the run had declared
   excluded. Deterministic gates check form. Only a reader holding the corpus
   checks meaning. A run without the eval pass is not gated, it is
   spell-checked.

2. **Fabricated aggregates are the characteristic hallucination.** The invented
   number was not a metric attached to a story ($10M, ~2M users, 5/5 CSAT all
   traced correctly). It was a SUMMARY AGGREGATE: "fifteen years of
   customer-facing integration consulting". Aggregates feel like arithmetic
   rather than claims, so they bypass the instinct to check a source, and
   `_CLAIM_NUMBER_RE` deliberately exempts bare years so nothing caught them.
   Two shipped the same day, on two different resumes.
   NOW ENFORCED: `tenure-not-computed` (BLOCK) checks every "N years" against
   the spans the spine can actually compute (whole career, one role, one role
   through to the present) plus tenures a unit itself carries.

3. **Chat-written documents carry defects corpus-written ones do not.** Of the
   seven blockers, six came from the cover letter written in chat and one from
   the resume written from a careerkit brief. Same day, same model, same corpus
   available. The difference was whether the writer was reading evidence units
   or its own memory of them.

4. **Skill tags cannot express "this is about the employer's product".** For an
   Okta application the ranker cut `linkedin-okta-exposure`, the unit describing
   hands-on work inside customer Okta orgs, because its tags duplicated
   higher-ranked units.
   NOW HANDLED, deliberately NOT by promotion: `target_affinity` breaks ties
   below relevance, and any affinity unit the budget drops is surfaced in the
   brief under "Cut, but about the target company", pointed at the cover letter.
   Measured on the real run, that unit scores relevance 6 against a top-ten cut
   at 8. A bonus big enough to promote it would let weak evidence beat strong,
   which is the failure the ranker exists to prevent. The cover letter is the
   honest home for it.

5. **Coverage flatters credential requirements.** `gap` scores a skill-less
   requirement HIT, so "A Bachelor's degree required" counted toward a headline
   "15 of 17 HIT" for a candidate who does not hold one. The review page
   relabels credential and tenure rows from the parsed JD; `report.py` still
   does not.

6. **Measure the page count, never estimate it.** Both resumes rendered to two
   pages while reading as one-page drafts (947 and 910 markdown words against a
   measured ~780-word ceiling). The rule against the "just over one page" shape
   is only enforceable if someone renders the docx and counts.
