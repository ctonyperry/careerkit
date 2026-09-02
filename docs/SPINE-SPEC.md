# The spine over time

A specification for a career record that is built lazily, refined by use, and
carries its own age. Written 2026-08-26 from what populating one person's spine
actually took, and from what refining it over a week of applications exposed.

## What the reference run says

The spine that works today was not built by an interview. It was built by:

1. **Extract, then diff.** Two old resumes and a profile disagreed on a name,
   three sets of dates and an invented diploma. Conflicts were resolved from
   memory in seconds. Frequency voting was explicitly wrong: a resume
   generated from another resume looks like corroboration.
2. **Gap questions against a real posting.** Every strong bullet came from
   "did you do this?" asked about a requirement the file was thin on.
3. **Iteration on real drafts.** Twelve passes each surfaced a fact in no
   document. Iteration is the excavation, not a cost of it.
4. **Reading rendered output.** Every refinement over the following week came
   from the person reading a resume and saying what was off. Not one came
   from re-interviewing.

So the general design is: **a minimal timeline up front, evidence accrued per
application, refinement by reading.** The corpus's job is to show its age so
the person knows where to look.

## The model

### Spine

Identity plus timeline. Roles with org, title of record, dates, education.
This is the only prerequisite artifact and it takes minutes. Facts here are
human-authored; the machine audits and never writes.

### Evidence units

One file per unit. Fields, with the ones added by this spec marked NEW:

| Field | Meaning |
|---|---|
| `id`, `role`, `narrative`, `skills`, `tier`, `status` | as before |
| `confirmed_on`, `confirmed_by` NEW | when and by whom the unit was last stood behind. Prose notes carried this for 32 units and nothing could query it. |
| `supersedes` NEW | the unit this one replaces. The loader drops the old one; the file stays as history. Two units did this by prose note and the gap engine still counted the old one. |
| `render_notes` | **standing bounds only**: what a rendering may and may not do. The person's own words, dated. |
| `history` NEW | dated corrections: what changed, when, why. Kept off the rules so a reader gets the rule without the changelog. Units carried up to seven notes with corrections mixed in. |
| `verify` | open questions. A unit with any is not sendable. |
| `do_not_print` | literal strings that never reach a document. |
| `link` | public artifact, the non-traditional candidate's credential. |

### Preferences and policies

Dated entries, appended, never overwritten. "Capability is not aspiration",
the projects hold, the visible-window width, the job-function loves list:
each is true on a date. A career shift is a new entry. An old render stays
explicable by the entries in force when it was made.

### Outcomes

`runs/<run>/outcome.yaml`: sent, screened, what was probed, result. The one
loop nothing closes today. A bound that a screen tested becomes a `verify`. A
rejection pattern becomes a strategy note. Six packages have been sent and the
corpus knows nothing about any of them.

## Operations

| Command | Does |
|---|---|
| `stale [--older-than 1y]` NEW | lists units by `confirmed_on`, oldest first, MEMORY tier first. The re-ask list. |
| `reconcile <src>...` NEW, later | extracts a timeline from each source, diffs them, emits only conflicts as questions. The intake for a new person, and for anyone with more than one old resume. |
| `gap`, `resume`, `lint`, `finalize` | as before; `gap` now ignores superseded units. |
| `ingest-session` | repointed at a questions file with answer slots instead of a dead web UI. Revived, not rewritten. |

## Career shifts

Not a mechanism. Three things the record already supports:

- **A shift is a re-read, not a re-interview.** Evidence does not change when
  the target does; which thread of it matters does. `target_affinity` per unit
  carries that. Run a gap pass against two or three representative postings
  for the new direction and set affinities from what surfaces.
- **The taxonomy grows and never rotates.** Tags accrete from real postings.
  Nothing is deleted, so an old direction stays renderable.
- **Bounds outlive shifts.** "No production IdP administration" is true in
  every direction. The bounds are the part that must be most stable, because
  they keep a new pitch honest about old work.

The one thing a shift changes is summary voice, and that is a dated preference
entry.

## Build order

Each step is validated against the next real application before the next step
starts. Nothing here ships ahead of a run that needs it.

1. **Model fields** (`confirmed_on`, `confirmed_by`, `supersedes`, `history`),
   all optional, so every existing unit still loads. Loader honors
   `supersedes`. `stale` command. Migrate the two prose supersessions and the
   dated confirmations that can be read cleanly.
2. **Questions file with answer slots**, and `ingest-session` reading it.
3. **Outcomes file**, and the strategy engine reading it.
4. **`reconcile`**, when a second person's sources exist to diff.
5. **Split `career-data.md`**: conventions stay, facts move to YAML only.

Not on the list: an exhaustive interviewer, a visualizer, an identity
synthesizer. Two earlier attempts built those first and produced no resume.
