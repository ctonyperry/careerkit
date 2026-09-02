# careerkit

An evidence-grounded resume pipeline. A private corpus of what a person has
actually done, a deterministic engine that selects from it, an LLM that
drafts from the selection, and gates that refuse anything the corpus does
not support. Nothing here invents a fact.

## Layout

- `careerkit/` the engine: models, loaders, coverage, selection, brief,
  linter, finalize, stale. `careerkit.paths` is the one place that knows
  where the corpus is.
- `tools/` the gates. Each is a script taking a run directory. Each docstring
  names what the gate cannot see before what it can.
- `evals/defects.yaml` every mistake that reached a person: the text, the
  cause, who caught it, what enforces it now. `tools/regress.py` replays it.
- `examples/sample-corpus/` a fictional person, so everything runs on a fresh
  clone. `examples/sample-run/` a complete run against it that clears every
  gate.
- `skills/` the Claude Code skills that drive the pipeline in chat.
- `docs/` DEVELOPMENT.md (how this improves itself), STYLE-GUIDE.md (every
  writing rule with the defect that caused it), SPINE-SPEC.md (the corpus
  over time).
- `prompts/` the LLM steps: JD parse, resume write, critique.

## Where the person lives

`CAREERKIT_CORPUS` points at a private directory holding `data/spine.yaml`,
`data/evidence/*.yaml`, `data/declined.yaml`, `data/skills.yaml` and
`career-data.md`. Runs and JDs live in another private directory; gates take
a run directory as their argument and `CAREERKIT_RUNS` helps them find the
JD a manifest names. Unset, everything uses the sample corpus and says so on
stderr.

## Read first

1. `docs/DEVELOPMENT.md`. Do not add a feature that a manual run has not yet
   needed.
2. `docs/STYLE-GUIDE.md`.
3. `evals/defects.yaml`. Every document correction gets an entry in the same
   commit.

## The pipeline, on a run directory

    python -m careerkit.cli inbox --serve                  # capture button; `inbox` lists pending
    python -m careerkit.cli triage                         # the inbox ranked; parses validated
    python -m careerkit.cli verdict --jd <jd-parsed.json>   # first, before drafting
    python -m careerkit.cli lint <resume.md> --jd <jd-parsed.json>
    python -m careerkit.cli finalize <resume.md> --jd <jd-parsed.json>
    python tools/citecheck.py     <run>   # every claim traces to its cited unit
    python tools/crosscheck.py    <run>   # spine tense, cross-doc drift, JD trace
    python tools/echo_check.py    <run>   # repetition and sentence-shape density
    python tools/ats_check.py     <run>   # parse risk, searchable terms, gaps
    python tools/screen_check.py  <run>   # seven-second human pass, age signal
    python tools/metrics.py       <run>   # measured page count, bullet shape
    python tools/render_docx.py   <run>   # markdown to .docx
    python tools/regress.py               # every recorded defect still caught
    python tools/panel.py         <run>   # reviewer packets, then run the panel
    python -m careerkit.cli prep --run <run>   # after sign-off: the night-before sheet
    python -m careerkit.cli outcomes           # every run: status, sent, what came back

Gates check form. Only a reader holding the corpus checks meaning. Both halves
run before anything is sent, and the drafter is never the only reader.

## Hard rules

- Never invent a fact. Every resume claim traces to an evidence unit id in the
  run's `claim-sheet.md`.
- Never paraphrase a posting from memory; it is on disk.
- Dates, titles and education render from the spine. The title of record goes
  on the title line; a function goes in the subtitle.
- Obey every unit's `render_notes`. They are corrections already made.
- The visible window is fifteen years. No career tenure figure on the page.
- Heredocs mangle backslashes and choke on more than one per command. Write
  code and multi-file batches with the Write or Edit tools.
- Tests must pass on the sample corpus with no environment set. A test that
  needs a particular person's record belongs in that person's corpus repo.

## Working with the person whose corpus it is

They read shipped documents as quality tests and bring back what feels off.
Each flag is a class, not an instance: find the class, write the rule with a
before/after pair, record the defect. Do not regenerate dormant packages.
