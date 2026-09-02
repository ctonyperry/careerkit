---
name: targeted-resume
description: Produce a targeted resume and/or cover letter for a specific job description, through careerkit's evidence corpus and deterministic gates. Use whenever the user asks to write, tailor, rewrite, or review resume or cover-letter content for a role, or asks whether a job fits. Also use for single-section rewrites; a "quick edit" is exactly how ungrounded claims get in.
---

# Targeted resume pipeline

Resume prose is never written from conversation memory. It is written from
selected evidence units, checked by deterministic gates, and confirmed by the user
before it leaves the machine. This skill exists because the 2026-08-24 session
proved that chat-written documents drift: they acquired another company's JD
language, an invented job title, em dashes against house style, and dates that
contradicted the spine, all in one afternoon.

## Systems

- **Engine + gates**: this repository. The `careerkit` CLI (`python -m
  careerkit.cli ...`), the gates under `tools/`, `prompts/`, and
  `evals/defects.yaml`.
- **Corpus**: the directory `CAREERKIT_CORPUS` points at (`data/spine.yaml`,
  `data/evidence/*.yaml`, `data/declined.yaml`, `data/skills.yaml`,
  `career-data.md`). Unset, the fictional sample in `examples/sample-corpus`
  is used, which is only ever right for a demo.
- **Runs**: a private directory of your own holding `jd-inbox/` and `runs/`.
  Gates take a run directory as their argument, so it can live anywhere.

## Hard rules

1. **Never invent a fact.** Every resume claim traces to an evidence unit id.
   If a JD wants something the corpus lacks, that is a gap interview question
   for the user, not a sentence you write.
2. **Never paraphrase a JD from memory.** Any sentence referring to the target
   company or posting must quote the JD file in `jd-inbox/`. Facts about the
   company from outside the JD (news, docs) require a cited source shown to
   the user. This is the rule that the Okta-to-Cash-App bleed broke.
3. **Dates, titles, tenure, and education render from the spine**, never from
   recall. The visible window is fifteen years (the user's decision, 2026-08-26):
   no total-career tenure figure, no dated role older than that, older roles
   compressed undated into `Earlier`. The old "Thirty-one years... 1995"
   opener is retired. Sub-spans are computed from the spine.
4. **Obey `render_notes` on every unit you use.** They encode corrections the user
   already made; violating one re-introduces a known error.
5. **Check `data/declined.yaml` before claiming anything.** Currently: no
   certifications exist, and OIDC is unclaimable.
6. **Provisional/MEMORY-tier units are flagged to the user before they ship**, not
   silently included.
7. **the user is the trust gate.** Checkpoints are not optional and are not
   summarized away.

## The pipeline

### CP1 — JD on disk, then fit verdict

The JD must exist as a file in `jd-inbox/` (use `/save-jd` if it does not).
Read it from disk; do not work from what was pasted into chat.

Give an honest fit verdict, including "do not apply" when that is the answer.
Weigh: does the corpus honestly cover the minimum qualifications? Check
`career-data.md`'s job-function preferences (the user's "loves" list ranks a role
up; a mostly-liaison role gets flagged even at full coverage). State gaps
plainly. **Stop for the user's go/no-go.**

### CP2 — Claim sheet

Parse the JD with `prompts/jd-parse.md` into `<jd>-parsed.json`, then:

    python -m careerkit.cli gap --jd <parsed>.json --out gap-report.md
    python -m careerkit.cli resume --jd <parsed>.json --out resume-brief.md

Present a claim sheet: chosen evidence unit ids, the angle for each, which
render notes apply, what is deliberately excluded, and any THIN/MISS
requirements with recovery questions. **Stop for the user's approval of the claim
sheet before drafting.** Deciding the angle here is what stops mid-sentence
improvisation later (the invented "Architect & Engineer" title came from
drafting without this step).

### CP3 — Draft with citations

Write from the brief only, following `prompts/resume-write.md` and the user's
writing standards in `CLAUDE.md` (no em dashes, no puffery, no self-rating, no
JD-mirroring in the summary, atmosphere replaced by specificity). Keep an
evidence id against every bullet in the run's `claim-sheet.md`.

### CP3.5 — De-slop the draft

Before any gate, run the `avoid-ai-writing` skill over the draft in detect
mode. The gates catch fabrication and mechanics; they do not catch a trailing
clause that exists for rhythm, an approval-framed boast, or a summary written
for cadence. Apply the deletion test to every clause you would not miss.

### CP4 — Gates (all of them, in order)

Create `runs/YYYY-MM-DD-company-role/` with `manifest.yaml` (company, role,
`jd:` path, `resume:`, `claim_sheet:`, `documents:`), the documents, and the
claim sheet. Then:

    # house style, blocking
    python -m careerkit.cli lint <draft>.md --jd <parsed>.json
    # coverage/readiness gate
    python -m careerkit.cli finalize <draft>.md --jd <parsed>.json
    # cross-document: spine tense, run drift, JD tracing, claim attribution
    python tools/crosscheck.py runs/<run-dir>

Every BLOCK must be fixed, not explained. Then run the **adversarial eval**:
spawn a subagent (Agent tool, `Explore`) whose only job is to refute, giving it
the JD path, the run directory, and the evidence directory:

> Try to refute this application package. For each resume/letter sentence:
> (1) name the evidence unit that supports it, or report it unsupported;
> (2) check any company/JD reference against the JD file verbatim;
> (3) check dates, titles, and tenure against spine.yaml;
> (4) flag any claim stronger than its evidence tier, any render_note
> violation, and any claim in declined.yaml. Default to "unsupported" when
> uncertain. Report findings only, no rewrites.

Fix what it confirms. Note that crosscheck is word-overlap only, so semantic
contamination is this agent's job.

### CP5 — the user signs off, then export

Show the user: the fit verdict, what changed, every provisional/MEMORY claim used,
every advisory finding left standing and why, and anything the eval agent
flagged. **Only after his sign-off**, export (Drive doc, PDF, docx).

On export: update the run's `manifest.yaml` with the destination and move any
superseded document ids into `superseded:`. When re-exporting a corrected
version, trash the stale one so only one live version exists.

## After the run

- New facts the user confirms during the run become evidence units or render notes
  in the corpus (their confirmation required; `verify:` flags for
  anything he has not explicitly confirmed).
- Run `python -m pytest -q` in this repository after corpus edits; tests
  must stay green.
- If a chat-only shortcut was taken, record why in `session-learnings.md`.
  That file is how this pipeline learns.
