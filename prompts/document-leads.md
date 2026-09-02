# Document Leads Prompt (LLM step, run in Claude Code chat)

Mine ONE uploaded old document (a prior resume, a review packet, an SOW) for
LEADS against EVERY open gap at once. This is the per-gap document mining from
implementation-design.md, run as a single global fan-out: one upload is scanned
against all open MISS/THIN wants, not re-read once per want.

A lead is a memory jogger, never a fact. It is SECONDARY tier: a claim in an old
document that a real instance MIGHT sit behind. It becomes evidence only after
the author confirms a specific instance through the four-beat interview. Shortcutting
"the old resume says it, include it" rebuilds the slop-laundering machine the
whole system exists to avoid. Do not do it.

## Inputs

1. `gap-report.md` from `careerkit gap`. Read its Coverage table and Recovery
   questions. The open gaps are every requirement/skill marked MISS or THIN.
   IGNORE skills marked HIT (already covered) and DECLINED (The author confirmed he
   has not done them; never resurface these from a document).
2. The uploaded document, read as text with its structure intact. You need the
   role/section HEADINGS, not just the bullet text, so a lead can carry its
   provenance.

## Task

For each open MISS/THIN want, scan the WHOLE document for phrases that might
point to a real instance behind that want. Fan out: a single phrase may serve
more than one want; list it under each. Many wants will get zero leads. That is
fine and expected. Do not invent a lead to fill a want.

For every lead, capture the SOURCE document's role location IF the phrase sat
under a role/company heading. Location is the memory coordinate system (people
index experience by era); carrying the document's own placement lets the
recovery question jog memory with "under your 2019 LinkedIn section you wrote
X." This is the ONE case where placement may precede confirmation, and only
because it is the DOCUMENT's placement, shown as provenance, not an assertion
that the unit belongs there. The author still confirms the real role in the interview.

If the phrase had no role heading above it (a skills blob, a summary line),
say so: `role_location: null`.

## Output

Write `document-leads.md` next to the document:

```markdown
# Document leads: <document filename>

> SECONDARY tier. Each lead is a claim to confirm, not a fact. Nothing here
> enters evidence until the author confirms a specific instance (four-beat protocol:
> existence -> location -> specifics -> defensibility).

## <want / skill tag> (<MISS|THIN>)

- quote: "the exact phrase from the document, verbatim"
  serves: <want id or skill tag>   # repeat the quote under each want it serves
  role_location: <role heading the phrase sat under, or null>
  source: <document filename>
```

If a want got no leads, omit it (the gap report already lists it as open).
If the whole document produced nothing, say so plainly.

## Rules

- Quote verbatim. Do not paraphrase, upgrade, or merge phrases; the point is to
  show the author his own past words so he can decide if a real instance is behind
  them.
- Never assign a skill tag the document does not support. A lead points at a
  want; it does not confirm the tag.
- Never turn a lead into a bullet or a metric. No `[VERIFY]` numbers here; if
  the document states a number, quote it inside the phrase and leave it as the
  document's claim.
- Leads feed the recovery questions as memory joggers. They do not answer them.
  The interview still asks "did you do this, and when?" and the author still owns the
  answer.

A worked example of the downstream artifact these leads feed:
the run's gap report (the recovery questions) and `prompts/jd-parse.md` (the
sibling chat step that produces the parsed JD).
