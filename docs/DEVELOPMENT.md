# How this project improves itself

Restated 2026-08-26, after three attempts at the same idea. Two died with the
thesis intact and no resume produced; this one has shipped six applications.
The difference was never the idea. It was the order of work, and this file
exists so the order does not get lost.

## 1. The process that produced it is the spec

The first good resume was made by hand, in a long session, with every claim
checked against a record. Everything mechanical here reproduces a step of that
manual run. Nothing here was built because it seemed like good architecture.

**Rule:** no feature ships before a manual run has needed it. A tool that cannot
beat the by-hand result for the step it replaces should not exist. When in
doubt, do the next application by hand and see what hurts.

**Corollary for onboarding:** the spine interview is not a feature to design. It
is the transcript of what it took to get one person's record straight, turned
into a prompt. Build it from the second person's manual run, not from
imagination.

## 2. The defect corpus is the backlog, the test suite, and the changelog

`evals/defects.yaml` records every mistake that got past a person: the exact
text, the cause, who caught it, and what enforces it now. `tools/regress.py`
replays all of it against the live gates on every run and fails if anything
once caught is no longer caught.

That gives three things for the price of one file:

- **A backlog that cannot inflate.** An entry needs a real defect and its real
  text. There is no place to write "add semantic search".
- **A regression suite whose fixtures are true.** Each entry's `text` is the
  fixture. The rule that catches it is tested against the sentence that
  actually escaped, not against an example someone invented.
- **A ratchet.** `no longer caught: 0` is the number that must not move. A gate
  that stops firing is a regression even if no document has broken yet.

**Rule:** every correction to a document gets an entry, in the same commit, with
`shipped: true` if it had already left the machine. The count of shipped
defects is allowed to go up. What is not allowed is a shipped defect with no
rule and no note explaining why a rule is impossible.

## 3. Every gate states what it cannot see

Each tool's docstring names its blind spot, and the pipeline map lists them in
a column. This is not humility for its own sake. Every escape this project has
had came through a blind spot that was knowable in advance:

- `finalize` validates the brief's selection, so it cannot see an override.
- `citecheck` matches terms, so a bullet can misrepresent a unit using only
  that unit's own words.
- `lint` blocks an invented credential and cannot see a real one omitted.
- Every gate validates against the corpus, so a wrong fact **in** the corpus is
  invisible to all of them. The Apple title of record shipped in four
  packages this way.

**Rule:** a new gate's docstring must say what it does not catch before it says
what it does. If that sentence cannot be written, the gate is not understood
well enough to trust.

## 4. Gates check form. Readers check meaning. Neither is optional.

On one package: lint 0, finalize READY, crosscheck 0, adversarial review
7 blocking. On the next: a style reviewer singled out "retry that knows a 429
from a 404" as the most convincing detail on the page, and `citecheck` blocked
it, because 404 appears nowhere in the evidence. A reader judging voice will
reward a concrete-sounding fabrication precisely because it sounds concrete.

**Rule:** no document reaches a person without both halves. And the drafter is
never the only reader: a self-review of one package found two things; the real
panel found a tenure window that did not reconcile with the spine and a
recruiter who passed at the fold. Same text. The delta was method.

## 5. Reviewers are differentiated by input, not persona

Telling a model to "be a recruiter" produces a model pretending. Giving it only
what a recruiter sees in seven seconds, and never the posting, produces a
recruiter's verdict. The four packets:

| Reviewer | Sees | Never sees |
|---|---|---|
| Recruiter | above the fold | the posting |
| Hiring manager | everything | nothing withheld |
| Writing critic | the documents, company redacted | posting, company |
| Evidence verifier | documents and corpus | the claim sheet |

**Rule:** a new reviewer is defined by what is withheld from it. If nothing is
withheld, it is the hiring manager again.

## 6. A blind panel is how a rule gets promoted

Five critics read five packages independently. Three complaints came back from
nearly all of them: restated facts, colon-then-list as the default sentence,
doubled-verb openers. Those became `echo_check.py` the same day. One critic's
opinion is an opinion. The same opinion from readers who could not have
conferred is a rule waiting to be counted.

**Rule:** a finding that recurs across three or more independent packets is a
candidate for a mechanical check. A finding from one packet is recorded and
watched.

## 7. A gate that cannot fire is worse than no gate

`dangling-reference` reported clean on every run the day it was written,
because a shell heredoc had turned its regex word boundaries into literal
backspace bytes. It compiled, ran, and matched nothing. Four repair attempts
failed identically. A green light with nothing behind it trains the operator to
wave things through.

**Rule:** a new rule is not done until it has been run against the sentence it
was written to catch and against a near-miss it must not catch, and both
results are in the commit. `regress.py` enforces both: an entry's `text` must
fire the rule and its `must_not_match` must not. The first afternoon this
existed, it caught a rule firing on the exact figure it demanded, and then
caught its own author committing a fixture with the two fields swapped. The
ratchet applies to the person holding it.

## 8. Rules are tables, not sentences

"Purpose before parts" produced "Handled the cases that quietly lose data,
because instrumentation nobody trusts gets switched off" within an hour, and
the author read it as promotional. The correction was one clause away from the rule
that caused it. It went into STYLE-GUIDE.md as a before/after table, because a
sentence can be re-read to mean its own violation and a table cannot.

**Rule:** a style rule ships with at least one before/after pair drawn from a
real document. If the pair does not exist yet, the rule is a hunch.

## 9. The corpus outranks the draft, so the corpus must be checkable by a person

Every automated check trusts the corpus. That is the right design and its cost
is that the corpus's own errors are unreachable by tooling. What reached them:
the author reading the document and saying "I think technically my title was
Security Analyst." Nothing else could have.

**Rule:** facts in the corpus carry who confirmed them and when. Bounds are
recorded on the unit, in the person's own words, so a later draft cannot
quietly exceed what was said. And the person reads the output, because the
person is the only gate with access to the truth.

## What to build next, in the order the manual runs earned it

1. ~~Negative fixtures in the defect corpus.~~ **Done 2026-08-26.** `must_not_match`
   on an entry is a near-miss the rule must leave alone, and `regress.py`
   asserts both directions. The first three fixtures found a rule firing on a
   sentence carrying the exact figure it existed to demand. Principle 7, made
   mechanical, for the cost of one field.
2. ~~The engine/person split, first half.~~ **Done 2026-08-26.** `CAREERKIT_CORPUS`
   points at any private corpus directory; identity is read from the spine's
   `identity` block, never from code. **Second half done 2026-09-02:** one
   repository, the skills shipped inside it, the gates finding the corpus and
   the runs through `careerkit.paths` and `CAREERKIT_RUNS`, and a test suite
   split into a public contract and a `private_corpus` history. Page count
   still asks Word and returns nothing elsewhere; it has not yet hurt.
3. ~~The corpus shows its age.~~ **Done 2026-08-26.** `confirmed_on`,
   `confirmed_by`, `supersedes` and `history` on every unit, all optional;
   `careerkit stale` lists the re-ask list. Eighteen units had never been dated.
   The general design is in the engine repo's `SPINE-SPEC.md`, and priority
   moved from unblocking one friend to that design: questions with answer
   slots, outcomes fed back, then `reconcile`.
4. ~~A sample corpus for a fictional person.~~ **Done 2026-09-02.**
   `examples/sample-corpus` is Morgan Vale, who does not exist, with one
   provisional unit, one superseded pair, one doubted figure, one declined
   skill and one role that must be omitted, so every mechanism has a case.
   `examples/sample-run` clears every gate. Building it found a gate that only
   worked for one person: `citecheck` matched resume headings against a
   literal tuple of employer names. It reads the spine now. It also found two
   defect entries that could only be replayed against the corpus they came
   from; they carry their fixture context now, so CI can replay them.
5. ~~Interview prep from a run.~~ **Done 2026-09-02.** `careerkit prep` earned
   its place the day the hiring-manager packet came back asking "what would
   you probe" and the answer was already in the corpus: render notes that say
   where a claim stops, verify items still open, the doubted figure beside the
   one that is safe, and the declined record in the person's own words. The
   command re-sorts what exists around the questions. It generates nothing.
6. ~~The verdict as a command.~~ **Done 2026-09-02.** Six manifests carried a
   hand-written verdict at the top and the arithmetic under each was the
   same: required capabilities by status, tenure from the spine, whether a
   credential carries an equivalence clause. `careerkit verdict` computes
   that and says one of three things. The judgement about wanting the job
   stays with the person.
7. ~~The outcomes ledger.~~ **Done 2026-09-02.** Six packages out and no way to
   see across them without opening six files. `careerkit outcomes` reads
   every manifest; `outcome`, `outcome_date` and `outcome_notes` are the
   fields the person fills in when something comes back. Also `careerkit
   init`, because the README's "copy the sample and replace every line" was
   an instruction, and instructions get skipped.
8. ~~The capture button.~~ **Done 2026-09-02.** Every run began with a posting
   pasted into chat and a skill that wrote it to disk, which meant a session
   open and a sentence typed. `careerkit inbox --serve` is a local receiver
   plus a bookmarklet: one click on the posting, one verbatim file in
   `jd-inbox/`, never overwritten. Asked for in so many words: "I go to a
   job listing page, press a button, and it goes to the jd inbox."
9. ~~Triage.~~ **Done 2026-09-02.** Fifteen postings arrived the afternoon the
   button existed and the question was which to spend a run on. `careerkit
   triage` runs the verdict on every parsed posting, ranks them, and refuses
   a parse that uses a tag the alias table does not know, because an
   invented tag is how a MISS turns into a HIT (defect
   jd-parse-invented-tag, 2026-08-25).
10. ~~Deciding unmapped language.~~ **Done 2026-09-02.** Fifteen parses
    produced a hundred-odd unmapped terms and the only mechanism was a
    sentence in a prompt saying the person confirms each. `careerkit terms`
    queues them across the inbox; a decision is alias, gap or ignore, with
    a note, recorded once in `terms.yaml`. A gap scores as a MISS from then
    on, which is the first time "unmapped" turns into an honest number.
11. **Cross-run drift.** The same unit rendered as "developer zero" in one
   package and "first developer" in another. Visible now only by hand.

Not on the list: anything that has not yet hurt in a real run.
