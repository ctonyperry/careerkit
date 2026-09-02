# Resume Write Prompt (LLM step, run in Claude Code chat)

Turn a writer brief (`resume-brief.md`, produced by `careerkit resume`) into a
resume draft in markdown. You write ONLY from the brief. You do not rank, you do
not add material, you do not reach for anything not in the brief. The brief is
the whole world; the ordering in it is already the right ordering.

    careerkit resume --jd <jd>-parsed.json --length one-page --register <choice>
    # then: write the draft in chat with this prompt
    # then: careerkit lint <draft>.md   (see prompts + the linter)

## Hard rules (these recreate past failures if broken)

- **Only selected evidence.** Every bullet traces to a unit in the brief. If it
  is not in the brief, it does not exist. (The v1 failure was a writer that saw
  the whole corpus and wandered into impressive-but-irrelevant material.)
- **Education transcribed VERBATIM from the brief's Education section.** Never
  compose, upgrade, infer, or add a credential. If the brief lists coursework,
  you write coursework, not a degree. (An AI-processed resume once hallucinated
  a diploma; for non-traditional paths the model always drifts toward inventing
  credentials. Do not.)
- **Never invent a number.** Any figure not present in the unit renders as
  `[VERIFY]`. Do not smooth "a couple dozen" into "24". Do not attach a metric a
  unit does not carry.
- **Honor render_notes and CONTINUITY flags.** A render_note is a framing
  correction ("partnered with engineering, not selected first") and it wins over
  your instinct. A CONTINUITY unit gets exactly ONE factual line; do not mine or
  expand it.
- **PROVISIONAL units** may be drafted, but if the brief says DRAFT, watermark
  the output DRAFT and mark each provisional bullet so finalize can confirm it.

## House style (the mechanical linter blocks violations; write to pass it)

- No em dashes. En dashes in date ranges are fine.
- No puffery or filler adjectives. No self-rating ("expert", "passionate",
  "results-driven", "seasoned").
- No defensive/compensatory framing ("self-taught but", "no degree yet"). Never
  apologize for or over-explain the path; replace it with specificity.
- No three-item lists in prose, EXCEPT scope-of-work resume bullets ("migrated
  X, built Y, and modernized Z" is accepted idiom).
- Short sentences mixed with longer ones. Concrete actions over atmosphere. The
  real slop is semantic: a clause describing a FEELING of competence ("owns the
  hard part", "stays in the room when it breaks") instead of a concrete action.
  Replace atmosphere with the specific thing done.

## Shape (mirror examples/sample-run/resume.md)

1. Header: name and contact VERBATIM from the brief; a title line mirroring the
   JD title; then the SUMMARY (see its own rules below).
2. Experience: roles in brief order, newest first. Each role gets a title/org/
   dates line, an optional one-line italic context from role_notes, then bullets
   from its units. A strong unit may become two bullets; a CONTINUITY unit gets
   one line.
3. Earlier: the brief's single compressed line.
4. Projects: from the brief's Projects units, if any.
5. Technical Skills: grouped from the skills the written bullets actually
   demonstrate. Do not list a skill no bullet supports.
6. Education: transcribed verbatim per the brief's placement.

## The summary: trajectory, not a fit claim

The summary is the only line on the page with no evidence unit under it, which
makes it the riskiest. Two failure modes live here, and both are the summary
floating free of anything concrete:

1. **Atmosphere** (session-learnings): clauses describing a FEELING of
   competence. "Owns the hard part." "Stays in the room when it breaks."
2. **JD-mirroring** (The author, 2026-08-19): paraphrasing the posting back at the
   reader. "Guides customer engineering teams from integration design through
   production rollout, then traces what breaks at scale to root cause" is just
   the JD's own bullets in the first person.

Mirroring is redundant and it is weak. Redundant because the BULLETS already
argue fit: they were selected against this JD deterministically, so the whole
page is targeted. Weak because every other applicant is mirroring the same
posting, so it is the most commoditized sentence on the page. It also reads as
eager, which is the wrong footing for a senior candidate.

**Write the career's trajectory instead.** Where this person started, the shape
of the path, where they are now. That is differentiating because nobody else has
it, and it needs no adjective to land: the facts are the interest.

- Ground it in the spine: real roles, real spans, real transitions.
- Years of experience are COMPUTED from the spine, never estimated.
- You MAY choose which true parts of the trajectory to foreground for the target
  (the customer-facing years for a consulting role, the hands-on years for an
  engineering one). You may NOT paraphrase the JD's requirements.
- Keep it concrete. "Started on a tier-2 support desk in 1995" is a fact. "A
  seasoned technologist passionate about..." is slop wearing a career for a hat.
- No defensive framing about the path. Never explain the GED, never apologize.

`careerkit lint --jd <parsed>.json` flags this as `jd-mirroring` (WARN): it
measures how many distinctive JD words the summary reuses. Bullets are exempt
and should share the JD's vocabulary.

## Output

Write the draft to `<jd-name>-resume-draft.md`. Then, in order:

1. `careerkit deslop <draft>.md` (optional but recommended): auto-fixes the
   mechanical slop it safely can (em dashes to commas, stray whitespace). It
   never rewrites a claim.
2. `careerkit lint <draft>.md --jd <jd>-parsed.json`: fix every remaining BLOCK
   by hand (unsourced numbers, invented credentials, puffery). Pass `--jd` so
   the summary gets the jd-mirroring check.
3. `prompts/resume-critique.md`: advisory semantic pass.
4. `careerkit finalize <draft>.md --jd <jd>`: the just-in-time trust gate.
5. Ship format: `node scripts/md2resume.js <final>.md <final>.docx` renders the
   Word version FROM the approved markdown, so no line is ever retyped by hand
   (`npm i docx` once; it is not a project dependency).

   ALWAYS check the resulting page count; never assume it. session-learnings:
   "just over one page is the WORST shape" — a second page holding three lines
   reads as could-not-edit-down. Either tighten the density constants in the
   script until it is one full page, or add enough to genuinely fill two. The
   script's header shows the Word incantation for counting pages.
