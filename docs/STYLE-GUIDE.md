# House style — resumes and cover letters

The consolidated "best of" from every iteration: careerkit, career-graph,
campfire, life-graph, and the shipped documents themselves. Where sources
disagreed, the conflict is named and **resolved**, with the reasoning, so the
same argument is never had twice.

Precedence when something here is unclear: **the author's words > the spine and
evidence corpus > this guide > anything in an older repo.**

Enforcement legend: **[code]** enforced by a gate · **[rule]** documented
convention, human-enforced · **[found]** empirical finding.

---

## 1. Length

### Resume

- **[found] The one-page ceiling is ~780 Word-counted words** at the shipped
  density (9pt Calibri, 0.45in top/bottom, 0.5in left/right, line 228) using
  `scripts/md2resume.js`. Measured 2026-08-24: 777 words rendered to exactly
  one page; 805 words spilled to two.
  - *Conflict resolved.* Three numbers existed: "500-700 words"
    (`resume-generator.ts` RESUME_RULES), "~450-550" (its own lever
    instructions), and "~760 lands on one page" (`md2resume.js`, measured).
    **The measured number wins** because it is the only one tied to the actual
    renderer. The prompt guesses were never verified against a rendered page.
- **[rule] Never assume the page count. Render and measure**, every time:
  ```
  node scripts/md2resume.js <final>.md <final>.docx
  ```
  then in PowerShell, `$d.ComputeStatistics(2)` for pages. Markdown word count
  runs ~3% above Word's, so treat 780 markdown words as the warning line.
- **[found] "Just over one page" is the worst possible shape.** It reads as
  "couldn't edit down, didn't have enough for two." Commit to one dense page,
  or fill two genuinely.
- **[rule] Choosing between them:** one dense page for a high-volume first
  screen or when page two would run less than about two-thirds full. Two pages
  only when the second page is genuinely full of JD-relevant material that is
  already confirmed — never by promoting provisional units just to fill space.
- **[code] Unit budgets:** one-page = 10 units total, 5 per role; two-page =
  16 total, 7 per role (`careerkit/select.py`). Units cut by the budget are
  listed in the brief's "Not selected" section, never dropped silently.
- **[rule] Bullets per role:** at most 6 on a one-page resume, 8 on two. A
  strong unit may become two bullets; a continuity unit gets exactly one line.
  - *Conflict resolved.* careerkit caps units (leaving the bullet count
    undefined), career-graph caps bullets at 3-4/role. The shipped one-page
    one shipped resume runs 6 bullets on LinkedIn and reads fine, so the cap is 6, not
    4 — but it is a cap, and the length ceiling above outranks it.
- **[rule] When it spills, cut content before cutting type size.** Dropping
  below 9pt to win an argument with the page is a tell.
- **[rule] Two pages is the hard ceiling.** Longer only for an academic CV,
  which this is not.
- **[rule] REJECTED: the two-column trick.** Mainstream advice (resume-now,
  Jan 2026) suggests a two-column redesign to fit more on one page. Do not.
  The Ladders eye-tracking study lists multi-column layouts among the things
  that actively hurt, and Workday parsers handle them badly. When the page is
  full, the answer is fewer claims, not narrower ones.

### Cover letter

- **[rule] 200-320 words, three to five short paragraphs.** Under 200 risks
  looking thin for a senior role; over 350 stops being read.
  - *Conflict noted, position held.* Mainstream advice (resume-now, Jan 2026)
    calls for a "two- to three-sentence" summary "tailored to the job you are
    applying for". That is the JD-mirroring defect this guide bans outright,
    and the ban is empirical: the slop in this project concentrated in exactly
    that sentence. Tailor the emphasis, never paraphrase the posting.
  - *Conflict resolved.* career-graph said 300-450, campfire 250-400, its own
    prose-render "~350", and careerkit had no rule at all. Shipped letters run
    180, 230 and 330 on three shipped packages. The band above covers what
    actually ships and what actually gets read.
- **[rule] The letter is not governed by the resume's length budget.** It is
  the right home for material the resume's budget cut, for target-company-
  specific exposure, and for the credential conversation.

---

## 2. Formatting

### Header (canonical, and it must stay canonical)

```
# Morgan Vale

**<Title mirroring the JD>**

Portland, OR · morgan.vale@example.com · 503.555.0142 · linkedin.com/in/morganvale-example

<summary prose, no heading>
```

- **[code]** Name and contact render verbatim from `spine.identity`; the
  contact string is middot-separated and built by `brief.py::_contact()`.
- **[rule] The title line is bold and sits between name and contact.**
  - *Conflict resolved.* Three layouts had shipped: bold title above contact
    (two packages), plain title above contact (one), and no title at all
    (one). The bold-title layout wins because the linter's summary parser
    already assumes it, and because a plain title line is indistinguishable
    from summary prose to both a parser and a skimming reader.
  - This mattered: with a `## Summary` heading instead, the linter's
    `_summary_lines()` stopped at the heading and the **jd-mirroring check
    silently never ran** on either 2026-08-24 resume. Fixed in the linter
    2026-08-24, but the canonical layout is still the one to write.
- **[code] Never print a placeholder.** No `[Your Email]`, `TODO`, `N/A`.
  Missing identity means omit the block.

### Dates

- **[rule] Months for roles inside the 10-year recency window, years only for
  older ones.** `Sep 2025 – Jun 2026`, `Jun 2019 – Sep 2025`, then `2011 – 2018`,
  `2000 – 2011`.
  - *Conflict resolved.* career-graph banned months outright ("avoids false
    precision"); careerkit prints them. Both are right about different eras:
    recent dates are precise and recruiters check them; twenty-year-old months
    are noise. This codifies what the shipped resumes already do.
- **[code] En dashes in ranges are fine. Em dashes anywhere are not.**
- **[code] A finished role never reads as ongoing.** `crosscheck.py`'s
  `spine-tense` blocks "Present"/"currently" on a role the spine has ended.

### Sections and their order

`Name/title/contact` → `summary` → `## Experience` (newest first) →
`### Earlier` (one compressed line) → `## Projects` (only if a project earns
the space) → `## Technical Skills` → `## Education`.

- **[code] Every non-omitted spine role appears**, even with no JD-relevant
  evidence, as a single factual line. A gap reads worse than an off-topic line.
- **[code] `earliest_year_shown`** compresses older roles into the `Earlier`
  line. Two roles, one line, no bullets.
- **[rule] Projects is the first section to cut when the page spills**, and on
  a resume with deep, directly relevant employment it usually should not appear
  at all. It earns space only when the work history is thin, or when the project
  is the *only* evidence for a stated requirement. Adding one to anchor a
  keyword is a sign the bullets are wrong, not that a section is missing.
- **[code] Skills lists only what the bullets demonstrate.** A skill exists iff
  at least one selected unit carries the tag. Do not claim in Skills what the
  gap report scores MISS.
- **[code] Education renders verbatim from the spine.** The linter BLOCKs any
  credential word not present there. This rule exists because an AI-processed
  resume once invented a community-college diploma.
- **[rule] The visible window is fifteen years.** the author's decision, 2026-08-26,
  after asking why nothing caught age tells and learning that the canonical
  summary opener mandated the loudest one. No total-career tenure figure
  anywhere on the page; per-role tenure is fine, since a job length is not an
  age. No dated role older than the window; older roles compress into the
  undated `Earlier` line, one short factual clause each. Education shows the
  2018 accelerator; the 1993 and 1992 lines come off unless the GED policy
  below brings the GED back for a degree-gated posting. `screen_check`
  reports every year older than the window and any spelled-out tenure over
  fifteen, so a lapse is visible rather than felt. The thirty-one years stay
  true and stay available for the interview.
- **[rule] The GED is included deliberately, not by default.** Include it when
  the JD states a degree requirement (transparency beats omission, and it keeps
  the resume consistent with the letter); leave it off when education is not at
  issue. Never hide the path, never apologize for it, never argue against the
  requirement on the resume.

---

## 3. Voice and style

## 0. ATS, and what it actually does [research-backed, 2026-08-26]

Optimising for an auto-rejecting keyword algorithm means optimising against
something that mostly does not exist. The "75% of resumes are rejected by ATS"
figure traces to a 2012 sales pitch by Preptel, a company that folded in 2013
and never published a methodology; 68% of recruiters surveyed said they first
heard it from job seekers. 92% of recruiters say their systems do not
automatically reject on formatting, keywords, or a match score, and Greenhouse
does not algorithmically score resumes at all: it parses into fields and routes
to human scorecards.

Two mechanisms are real, and they point somewhere different:

1. **Recruiter boolean full-text search.** Greenhouse documents boolean queries
   and a Full Text Search toggle over resume text and internal notes: "job
   titles, skills, locations, and other keywords". That is search over the
   document text, not a filter on a structured title field, and their
   documented filters are a separate feature. Nothing in the docs ranks titles
   above skills. Postings draw 400 to 2000+ applicants and search orders the
   review queue rather than rejecting, though if a reviewer only opens the hits
   the practical effect on everyone else is similar.
2. **Criteria filters applied by people.** HBS and Accenture found 88% of
   employers agree qualified candidates get screened out for not matching exact
   JD criteria, and 49% of companies filter out employment gaps of six months
   or more.

- **[code] `tools/ats_check.py` enforces this.** Parse risk in the contact block
  and role titles, searchable-term coverage, title presence, and spine gaps.
- **[rule] The term split is the whole discipline.** A JD term the corpus
  supports is a legitimate win: the evidence exists and the draft happened to
  pick a different synonym. A JD term the corpus does not support is a
  fabrication with a keyword rationale. The tool reports the two separately and
  never recommends the second. This is the same line `crosscheck:jd-trace`
  holds.
- **[rule] Glyphs stay out of the title line and the contact block.** No arrows,
  em dashes or en dashes in either. Those are the two fields a parser extracts
  and a recruiter searches, and a mangled title line is the most expensive parse
  failure available. Date ranges use "to". The promotion renders as
  "Sr. Technical Consultant (promoted from Technical Consultant)".
- **[rule] Keyword stuffing is still banned.** Everything above is about being
  findable with claims already made, never about adding claims to be found.

---

### What a bullet is, before anything else [rule]

This section was written on 2026-08-25, after the author read a package that passed
every gate and said of the Apple bullets: "I'm just kinda like, huh? what did I
just read?" He was right, and the guide was part of the cause. Up to that point
it was four hundred lines of prohibitions with no positive statement of what a
bullet should contain, so a draft could satisfy every rule in it and still tell
the reader nothing.

**The standard resume voice, stated plainly.** Implied first person, no "I".
Past tense for past roles. Active voice. Open on the verb, never an article.
And the part that was missing here: **a bullet names what the work was FOR
before it names how it was done.** The widely used formulations all encode the
same order. Google's XYZ, "accomplished X as measured by Y by doing Z", puts
the accomplishment first and the mechanism last. CAR and STAR put the challenge
and the result around the action. This corpus already agrees: evidence units
carry a `car:` block with `challenge`, `action` and `result`. The failure on
2026-08-25 was rendering the action and discarding the other two.

**A bullet reports; it does not narrate.** Added 2026-08-26 after the author read a
set that had drifted into storytelling: "prioritizing verbosity over impact...
I want bullets people will actually read." The tell is sequence. A narrated
bullet walks the reader through what happened in order, joined by "then",
"and later", "once it sold", and it arrives at 35 to 50 words because every
step gets its own clause. A reported bullet leads with the claim and follows
with only the specifics that prove it.

| Narrated (what it was) | Reported (what it became) |
|---|---|
| Sat in with account executives on sales calls to talk through feasibility, drew out enough of the customer's business to recommend which integration surfaces and configurations fit, then ran the scoping cycle and delivered the work once it sold. | Joined account executives on sales calls as the technical voice: assessed feasibility, recommended the integration surfaces that fit the customer's business, then scoped and delivered the work after close. |
| Diagnosed a provisioning sync failing partway through the rollout... Had the customer surface their SCIM debug logs, compared them against ours, traced it to rate limiting, then changed our pipeline and re-ran... | Traced a mid-rollout SCIM provisioning failure to rate limiting by comparing the customer's debug logs against ours. Fixed the pipeline and re-ran with their IT team and implementation partner. |

- **[rule] Lead with the finding, not the procedure.** "Traced X to Y by doing Z"
  beats "did Z, then Z, then found Y". The reader wants the answer first.
- **[rule] Cut sequencing connectives.** "then... and later... once..." is how a
  story is told, not how a claim is made. One "then" per bullet at most.
- **[rule] Cut hedged quantifiers.** "drew out enough of the customer's
  business" is three words of hedge around "the customer's business".
- **[rule] Do not over-plain it either.** the author, same message: "sometimes the
  opposite, speaking too plainly." "Wrote the tests in plain English so the
  customer could check them" explains itself to nobody who needed it. The
  register is a competent professional writing to a peer, neither a college
  professor nor a children's book.
- **[metric] Watch the word count per bullet.** The narrated set averaged in
  the high thirties; the reported set came in around twenty-five, and the whole
  resume dropped from 712 words to 659 with nothing cut but manner.

**Purpose is a fact, not an argument.** This qualifier was added within an hour
of the rule above, because acting on that rule produced "Handled the cases that
quietly lose data, because instrumentation nobody trusts gets switched off", and
the author's read was immediate: "reads promo material rather than informational."
He was right. Naming what a thing is for is informational. Explaining why the
reader should be impressed is promotion, and the two are one clause apart.

The difference is testable:

| Informational | Promotional |
|---|---|
| measures UX friction across internal security web applications | finds where people get stuck in the tools they have to use |
| retry on 5xx, network errors and 429 but not 4xx | handles the cases that quietly lose data |
| trained product support to triage those issues without escalating them | so those issues stopped being escalated |

The promotional column is doing three things a resume should not: an evaluative
adverb ("quietly"), a causal clause justifying the work ("because X"), and a
verb chosen for feeling rather than accuracy ("handled" for "built"). None of it
adds a fact. **State what was built and what it does. The reader supplies the
significance; that is what a reader is for.**

- **[rule] No justification clauses.** If a "because", "so that" or "which
  means" is explaining why the work mattered rather than recording a fact, cut
  to the fact.
- **[rule] No evaluative adverbs or adjectives on your own work.** Not
  "quietly", "seamlessly", "cleanly", "properly", "unglamorous".
- **[rule] Use the accurate verb, not the weightier one.** Built, wrote, ran,
  migrated, diagnosed. Not "handled", "drove", "spearheaded", "owned" where a
  plainer verb is true.
- **[rule] No "I" on a resume.** Implied first person throughout. Violated on
  2026-08-25 in "so I brokered a new API", introduced while fixing something
  else; nothing mechanical catches it yet.

**The test.** Read the bullet as someone who is not a software engineer, because
recruiters and most hiring managers are not. If the answer to "why would anyone
want this" is not on the line, the bullet is mechanism without purpose and it
reads as noise however precise it is.

- **[rule] Purpose before parts.** "Built the telemetry library the security
  group uses to find where people get stuck in its internal tools" earns the
  right to then say TypeScript, zero-dependency, under 10KB. Reversing that
  order spends the reader's attention on parts before they know what the thing
  is.
- **[rule] Jargon is allowed, but only after the purpose has landed.** `5xx`,
  `sendBeacon` and `SCIM` are credibility to a technical reader and noise to
  everyone else. They belong in the second half of a bullet, never the first.
- **[rule] Prefer the plain-English version of a technical fact when it costs
  nothing.** "Checked the data coming out matched what had actually happened"
  says what "asserted emitted xAPI statements matched the performed activity"
  says, to strictly more readers.
- **[metric] `bullets_with_result` is the check.** `tools/metrics.py` counts
  bullets stating an outcome. On one draft it fell from 8 of 15 to 5
  of 16 across three style passes, and nobody looked, because style review was
  chasing rhythm and no gate blocks on it. Read it every run. A resume where
  most bullets state no result is a list of tasks.

### Blocked outright [code]

| Rule | What it catches |
|---|---|
| `em-dash` | any `—`; use a comma, colon, or two sentences |
| `banned-phrase` | results-driven, proven track record, detail-oriented, team player, self-starter, go-getter, think outside the box, synergy, world-class, best-in-class, rockstar, ninja, wear many hats, hard-working |
| `self-rating` | expert in, expert-level, guru, highly skilled, highly proficient, passionate about, seasoned, extensive experience |
| `self-casting` | the technical voice, the go-to, the person who, the one who, trusted advisor, thought leader. Claiming a **part** rather than a level. The actions underneath say it better, and a reader who concludes it trusts it. |
| `scale-boast` | at a scale, never handled before, unprecedented scale. A superlative standing in for a figure, on pages that give figures freely. Use the number or cut the clause. |
| `number-without-source` | any figure not in a source unit and not marked `[VERIFY]` |
| `education-not-in-spine` | any credential word not in the spine |

### Advisory [code]

`tricolon` (three-item list in prose), `rhythm` (every sentence in a bullet
over 22 words), `jd-mirroring` (summary shares 5+ distinctive words with the JD),
`register-spike` (latterly, whilst, amongst, aforementioned: formal registers in
otherwise flat American prose; advisory because one may occasionally be right).

### The tricolon rule and its exception

- **[rule] No three-item lists in prose. The exception is scope-of-work
  *bullets*** ("migrated X, built Y, and modernized Z" is accepted idiom).
  **The exception is bullet-scoped, not summary-scoped** — a tricolon in the
  summary is slop and gets rewritten.
- The delimiter-separated Skills line trips this check harmlessly; it is a
  known false positive, not a defect to fix.

### Semantic slop — the three categories that survive the linter

1. **Atmosphere-poses.** A clause describing a *feeling* of competence instead
   of an action: "owns the hard part", "stays in the room when it breaks",
   "thrives in ambiguity". Fix by naming the action; if there is no action
   under it, cut the line.
   - *This is not hypothetical:* a 2026-08-24 letter shipped "I was the
     one in the room with the customer... until it worked", almost verbatim the
     example the rules name.
2. **Defensive / compensatory framing.** "self-taught but", "no degree, but",
   "despite not having a CS degree", "scrappy". Replace apology with
   specificity. *Also shipped once:* "The degree. I don't have a bachelor's...
   let the interviews decide."
3. **JD-mirroring in the summary.** See below.

### Two tests from live review (2026-08-25)

**The boast test.** A fact whose grammatical subject is someone else's approval
of you reads as boasting, even when the fact is the strongest thing on the page.
"The contract was extended to nine months" makes the sentence about their
opinion; "picked up by further sites, which extended the engagement to nine
months" makes it about the work. Same fact, re-subjected.
- Not a lint rule: "brought in to break a renewal-blocking problem" is also
  approval-framed and reads fine, because the approval sets up a challenge
  rather than serving as the payoff. The test is *what is the sentence about*.

**The bullet-opener test.** Every institutional guide gives the same first
rule: a bullet opens with an action verb. A bullet opening with an article is a
noun phrase instead, and noun-phrase openers are where clumsy compression
breeds. The live example: *"The API subject-matter expert customer engineering
teams built against"* drops its relative pronoun ("the expert **that** customer
engineering teams built against") and garden-paths the reader through "expert
customer" before they can recover. Written as "Advised customer engineering
teams building against the API", it parses on the first pass.
- Now `bullet-opener` (WARN) in the linter. Advisory rather than blocking
  because a deliberately front-loaded number can earn a noun opener: "A $10M
  program reaching ~2M users" is a defensible choice, not a mistake.
- The general defect it stands in for: **anything that cannot be parsed on one
  read.** Dropped relative pronouns, stacked modifiers, and compressed clauses
  all fail the same test.

**The closure-flourish test.** A trailing clause that adds no information and
exists for rhythm is the most common AI tell that survives every other gate:
"...before anything shipped", "...at every step", "...from day one",
"...along the way". Apply the deletion test: remove it, and if nothing is lost,
it was there for cadence. This is what the `avoid-ai-writing` skill calls
narrated candor and performed emphasis; the fix is to run that skill on the
draft rather than to hope.

### The summary

- **[rule] The summary tells the career's trajectory, never a claim of fit.**
  Where the path started, its shape, where it is now. The bullets already argue
  fit; they were selected against the JD deterministically.
- **[rule] Diagnostic:** a summary that could only have been written after
  reading this specific posting is suspect. A trajectory summary is nearly the
  same across applications, with only the emphasis shifting.
- **[rule] Canonical opener:** "Thirty-one years in software, starting at a
  tier-2 support desk in 1995." The 15+/25-year framings are superseded.
- **[found] The summary is where slop concentrates**, because it is the only
  line on the page with no evidence unit under it. Bullets stay clean because
  facts anchor them.

### Numbers

- **[code] Never invent one.** Any figure not in a source unit renders
  `[VERIFY]`. Do not smooth "a couple dozen" into "24".
- **[rule, new] Every tenure or span figure is spine-computed or absent.**
  Aggregates ("fifteen years of customer-facing consulting") feel like
  arithmetic rather than claims, which is exactly why they slip through. This
  is the characteristic hallucination of this system: it shipped twice on
  2026-08-24, on two different resumes, and the deterministic gates caught
  neither. *Not yet mechanized — the linter deliberately exempts bare years.*
- **[rule] Settled phrasings:** "two dozen-plus" concurrent clients (never
  "25+", never 100-200); "5/5 CSAT"; the soft ~250k figure on the franchise rollout stays off
  paper; "$10M+" and "~2M users" are PRIMARY and print as-is.
- **[rule] Round down, never up.** "99.8%+" may print as 99.8%, never 99.99%.

### Verbs

- **[rule] Banned:** spearheaded, revolutionized, pioneered, championed,
  crushed, dominated; "transformed" and "orchestrated" only in their literal
  technical senses (ETL, container orchestration).
  - *Conflict resolved.* career-graph bans these; campfire's resume editor
    explicitly recommends "orchestrated" and "spearheaded" as power verbs.
    **The ban wins** — they read as embellishment, and campfire is the older,
    less-tested system.
- **[rule] Use:** built, designed, delivered, shipped, led, owned, architected,
  implemented, developed, traced, brokered, coordinated.
- **[rule] Hedge honestly when the evidence is thin:** contributed to,
  supported, assisted with, exposure to.
- **[rule] Describe the behavior, not the tool.** Not "used Playwright to
  test", but "drove real browser sessions and asserted emitted statements
  matched the activity performed".
- **[rule] IC work takes IC verbs.** Not "managed"/"oversaw" for individual
  contribution.

### Voice by document

| | Resume | Cover letter |
|---|---|---|
| Person | no "I"; implied first person | first person, "I" |
| Register | plain, declarative | conversational, still precise |
| Tricolons | bullets only | avoid |
| Flattery | never | never |

- **[rule] No flattery toward the target.** No "aligns with your mission", no
  "perfect fit for the X team", no "passionate about your vision". Relevance
  does the tailoring.
- **[rule] No filler openers.** Not "I am writing to express", not "Throughout
  my career".
- **[rule] Register is picked per run, never auto-classified.** Default plain
  and direct.
- **[rule] Salutation:** "Dear Hiring Manager," by default; "Hi," when the
  company's own writing is informal. Sign off with the full name.
  - *Conflict resolved.* Shipped letters used all three of no-salutation, "Hi,"
    and "Dear Hiring Manager,". Pick one default so it stops being a decision.

---

## 4. Strategy

- **[rule] Title mirroring is allowed and it works** ("Technical Solutions
  Consultant" for a JD's "Solutions Consultant"), but it is a **conscious
  decision at claim-sheet time, never a drafting default.** An unapproved
  mirror is how "Architect & Engineer" appeared over a spine title of "xAPI
  Specialist".
- **[rule] Mirror the JD's vocabulary in bullets where it is truthful; never in
  the summary.**
- **[code, hard] Every JD- or company-referencing sentence traces to the JD
  file on disk or a cited source.** Paraphrase from conversation memory is
  banned; it is how one company's posting language ends up in another's letter.
- **[code] Ranking is deterministic:** relevance to JD skills (required
  weighted 2, preferred 1), then evidence strength (PRIMARY 3 / DOC 2 /
  MEMORY 1, +1 confirmed), then recency. The writer sees only what was
  selected, never the whole corpus.
- **[found] The ranker is blind to target-company specificity.** For an identity-vendor
  application it cut the unit describing hands-on work inside customer Okta
  orgs, because its tags duplicated higher-ranked units. Carry that kind of
  evidence in the cover letter instead.
- **[code] Recency window is 10 years.** Older evidence counts as THIN. Keeping
  a stale-but-real skill is allowed; expect it to be probed.
- **[code] Requirement kinds:** capability → recovery question; credential →
  no question, a strategy note (is "or equivalent" present?); tenure → computed
  from the spine, never claimed.
- **[rule] A missing must-have is omitted or compensated with adjacent
  experience. It is never faked.** "Never did that" is a first-class answer and
  goes in `declined.yaml` so it is never asked again.
- **[rule] The resume does not argue the credential; the letter states the path
  plainly and moves on.**
- **[rule] Fit verdict comes before drafting, and "don't apply" is a valid
  output.** JDs heavy on the author's "loves" rank up; mostly-liaison roles get
  flagged even at full coverage.

---

## 5. What the gates actually catch (measured 2026-08-24)

| Gate | Caught on one package |
|---|---|
| `careerkit lint` | 0 blocking |
| `careerkit finalize` | READY |
| `crosscheck` | 0 blocking |
| **adversarial eval** | **7 blocking defects of meaning** |

Deterministic gates check form. Only a reader holding the corpus checks
meaning. **A run without the adversarial pass is not gated, it is
spell-checked.** Of those 7 blockers, 6 came from the cover letter written in
chat and 1 from the resume written from a careerkit brief — same day, same
corpus available. The difference was whether the writer was reading evidence
units or its own memory of them.

---

## 5b. Now enforced in code (added 2026-08-25)

- **`tenure-not-computed` (BLOCK)** — every "N years" claim, digits or spelled
  out, must match a span the spine can compute or a tenure a unit carries.
- **Doubted metrics** — `doubted: true` on a metric removes it from the
  linter's sourced set, so a figure the source has stopped standing behind
  blocks as `number-without-source`. Confirmation and doubt are symmetric.
- **`do-not-print` (BLOCK)** — `do_not_print: [...]` on a unit lists literal
  strings that must never reach a sent document, whatever the coverage maths
  says: a figure no longer trusted, an artifact not ready to share, a customer
  name that stays generic. Render notes carry the reasoning, this carries the
  enforcement.

## 6. Known gaps in enforcement

1. **The skills line is not checked against the bullets.** The rule is that it
   may only restate what a bullet proves; nothing enforces it, and a JD-required
   keyword was found sitting there alone on 2026-08-25.
2. **`jd-trace` is word-overlap, not comprehension.** A sentence can share
   vocabulary with the JD while asserting something it never says.
3. **Credential requirements score as HIT** in the coverage tally, flattering
   the headline count. The review page relabels them; the gap report does not.
4. **`/clean-ai-writing` is a dead command** — it points at
   `~/.claude/skills/avoid-ai-writing/SKILL.md`, which does not exist. This
   guide's section 3 is the content that command was reaching for.
5. **Two shipped "FINAL" resumes violate rules written after them**
   (an early final draft opens with the exact JD-mirroring shape the
   critique prompt names as its BEFORE example; two finals use "Sole Technical
   Owner" as a heading against the spine's framing note). They are historical
   artifacts, not templates.
