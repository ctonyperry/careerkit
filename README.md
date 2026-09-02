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

The verdict first. Apply, apply and name the gap, or a gate you do not meet,
with the arithmetic under it.

```bash
python -m careerkit.cli verdict --jd examples/sample-run/jd-parsed.json
```

Then the gap analysis: what the record covers, what it does not, what to ask
the person, and what is a poor fit by their own admission.

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
| `careerkit verdict` | The fit call, computed before any drafting: required capabilities by status, tenure from the timeline, a stated credential with or without an equivalence clause, and one of three answers: apply, apply and name the gap, or a gate you do not meet. | Whether you want the job, and whether a HIT is the story worth telling. |
| `careerkit gap` | Coverage per requirement: HIT, THIN, MISS, DECLINED. Recovery questions for the gaps. Tenure computed from the timeline, never typed. | Whether a HIT is the right story to tell. |
| `careerkit resume` | Selects units under a length budget and writes the brief the LLM drafts from. Provisional evidence makes the brief a DRAFT. | Prose quality. It writes no prose. |
| `careerkit lint` | Em dashes, self-rating, self-casting, scale boasts, numbers with no source, education not in the spine, phrases marked never-print. | A real fact omitted. |
| `careerkit finalize` | Provisional units and open verify items on the selection. | An override the writer made after the selection. |
| `careerkit prep` | The night-before sheet for a run: every cited unit with the bounds you set on it, the figures you doubt, what is still marked verify, and the requirements where the questions will land, with your own declined answer where you have one. | A probe about something the page does not claim. |
| `careerkit inbox` | The capture button: a local receiver and a bookmarklet that writes the posting to jd-inbox verbatim, with frontmatter, never overwriting. | Whether the page was the whole posting; sites fold the rest behind a button. |
| `careerkit outcomes` | Every run in one table: captured, status, sent, and what came back, with your own notes on why. | Why, until you write it down. |
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

Start from the fictional one, replace every line, and point at it:

```bash
python -m careerkit.cli init /path/to/your/corpus
export CAREERKIT_CORPUS=/path/to/your/corpus
```

Runs live wherever you like, one directory per application with a
`manifest.yaml`. Set `CAREERKIT_RUNS` to that directory and `careerkit
outcomes` tabulates them: what went out, what came back, and your notes on
why. That table is the record that outlives the search.

`docs/SPINE-SPEC.md` covers how a record grows and ages across applications
and career changes. `docs/STYLE-GUIDE.md` holds every writing rule with the
defect that caused it. `docs/DEVELOPMENT.md` is how the project improves
itself, and the order things get built in.

## Capturing a posting

One button. Start the receiver, drag the link it shows onto the bookmarks
bar, and click it on any posting on LinkedIn, Indeed, or a company site.

```bash
python -m careerkit.cli inbox --serve
```

It reads company and role off the page, opens a small window on the receiver
that saves the page text verbatim, writes
`jd-inbox/YYYY-MM-DD-company-role.md` with the frontmatter the pipeline reads,
and never overwrites. Verbatim matters: the anti-contamination check quotes
the posting from that file later, and a paraphrased capture poisons the run.
`careerkit inbox` on its own lists what is waiting.

Why a window and not a request: job sites ship a Content Security Policy
that blocks page scripts from calling any origin the site did not list, and a
bookmarklet is a page script. The posting crosses to the receiver by
`postMessage`, which no policy governs.

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
