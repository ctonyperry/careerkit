# careerkit

A resume you can be cross-examined on.

Every sentence on the page traces to a record of something you actually did,
written in your own words and confirmed by you. A deterministic engine picks
what goes on the page. A language model drafts the prose. A set of gates
refuses anything the record does not support, and a file of every mistake that
ever got past a person is replayed against those gates on every run.

The LLM never talks to the reader. It talks to the gates, and the gates talk
to you.

## Three things that happened

**A sent document carried a claim nobody had made.** A resume said the
author had used React at Apple. True, and confirmed. The bullet cited the
wrong evidence unit, one that says nothing about React. `citecheck` walked
every bullet back to the units it cited and reported the term as unfound.
The claim was right; the trail was wrong; and a trail that cannot be
followed is what fails a reference check.

**A critic praised a fabrication.** A style reviewer singled out "retry that
knows a 429 from a 404" as the most convincing detail on the page. `citecheck`
blocked it: 404 appears nowhere in the evidence. A reader judging voice rewards
a concrete-sounding invention precisely because it sounds concrete. Gates check
form. Readers check meaning. Neither is optional.

**A gate that could not fire reported clean for a day.** A shell heredoc had
turned the regex word boundaries in a new rule into literal backspace bytes.
It compiled, ran, and matched nothing. The fix was mechanical; the lesson went
into the harness: a rule is not done until it has been run against the
sentence it exists to catch and a near-miss it must leave alone, and both
results are on record. `tools/regress.py` enforces that on every entry.

## Try it in two minutes

Nothing below needs your data. A fictional person ships with the repo.

```bash
git clone https://github.com/ctonyperry/careerkit && cd careerkit
python -m pip install -e ".[dev]"
```

Gap analysis against a posting: what the record covers, what it does not,
what to ask the person, and what is a poor fit by their own admission.

```bash
python -m careerkit.cli gap --jd examples/sample-run/jd-parsed.json --out gap-report.md
```

The gates, on a complete run that clears them:

```bash
python -m careerkit.cli lint examples/sample-run/resume.md --jd examples/sample-run/jd-parsed.json
python tools/citecheck.py examples/sample-run
python tools/crosscheck.py examples/sample-run
python tools/screen_check.py examples/sample-run
```

Interview prep from the same run. Nothing generated: the corpus re-sorted
around the questions the page invites.

```bash
python -m careerkit.cli prep --run examples/sample-run
```

The defect corpus, replayed:

```bash
python tools/regress.py
```

The number that must not move is `no longer caught: 0`.

## What is in the box

| Part | What it does | What it cannot see |
|---|---|---|
| `careerkit gap` | Coverage per requirement: HIT, THIN, MISS, DECLINED. Recovery questions for the gaps. Tenure computed from the timeline, never typed. | Whether a HIT is the right story to tell. |
| `careerkit resume` | Selects units under a length budget and writes the brief the LLM drafts from. Provisional evidence makes the brief a DRAFT. | Prose quality. It writes no prose. |
| `careerkit lint` | Em dashes, self-rating, self-casting, scale boasts, numbers with no source, education not in the spine, phrases marked never-print. | A real fact omitted. |
| `careerkit finalize` | Provisional units and open verify items on the selection. | An override the writer made after the selection. |
| `careerkit prep` | The night-before sheet for a run: every cited unit with the bounds you set on it, the figures you doubt, what is still marked verify, and the requirements where the questions will land, with your own declined answer where you have one. | A probe about something the page does not claim. |
| `careerkit stale` | What in the record has not been re-confirmed, oldest and weakest first. | Whether a fact went stale without anyone noticing. |
| `tools/citecheck.py` | Every distinctive term in every bullet must appear in the unit that bullet cites. | A bullet that misrepresents a unit using only that unit's own words. |
| `tools/crosscheck.py` | Spine tense, drift between documents in a run, sentences about the company that do not quote the posting, references to a bullet that is no longer there. | Semantic contamination that shares no words. |
| `tools/echo_check.py` | Restated facts, colon-then-list as the default sentence, doubled-verb openers. | Whether the repetition was deliberate. |
| `tools/ats_check.py` | Parse risk, searchable terms the posting uses that the corpus supports but the page omits, employment gaps. Built on what applicant tracking systems actually do, not the folklore. | How a given company configured theirs. |
| `tools/screen_check.py` | The seven-second human pass: the six fixations, the left edge, required qualifications with no echo above the fold, signals of age. | The reader's mood. |
| `tools/panel.py` | Reviewer packets differentiated by what each is given, not by an adjective. The recruiter never sees the posting. The verifier never sees the claim sheet. | Anything; it prepares the readers. |
| `tools/regress.py` | Replays every recorded defect against the live gates, in both directions. | A defect nobody recorded. |

Every gate's docstring names its blind spot before it names what it catches.
If that sentence cannot be written, the gate is not understood well enough to
trust.

## Your own record

The corpus is three files and a directory:

- `data/spine.yaml`, the timeline. Human-authored. The machine may flag it and
  never writes to it.
- `data/evidence/*.yaml`, one unit per thing you did, with a provenance tier
  (PRIMARY, DOC, MEMORY), a status (confirmed, provisional), the bounds on
  how it may be rendered in your own words, and what must never be printed.
- `data/declined.yaml`, what you have confirmed you have not done. A first-class
  answer. It stops the question being asked again and turns into a strategy
  note instead.
- `data/skills.yaml`, the alias table that maps posting language to your tags.

Copy `examples/sample-corpus` somewhere private, replace every line, and point
at it:

```bash
export CAREERKIT_CORPUS=/path/to/your/corpus
```

`docs/SPINE-SPEC.md` covers how a record grows and ages across applications
and career changes. `docs/STYLE-GUIDE.md` holds every writing rule with the
defect that caused it. `docs/DEVELOPMENT.md` is how the project improves
itself, and the order things get built in.

## Drafting

Drafting is an LLM step and it runs in Claude Code. `skills/targeted-resume`
is the pipeline as a skill: fit verdict, claim sheet, draft with citations,
de-slop, every gate, adversarial review, then your sign-off. Five checkpoints,
none of them skippable. `skills/save-jd` captures a posting verbatim, because
the anti-contamination check quotes the posting from disk and a paraphrased
capture poisons the run.

Any model can draft. The gates do not care which one.

## Status

One person has used this for their own applications since August 2026. The
defect corpus holds fifty-one entries, thirteen of which reached a sent
document. It is a working tool and an argument, not yet a product. If you
run it on your own record, the thing most worth sending back is the first
sentence that got past every gate and still felt wrong.

MIT.
