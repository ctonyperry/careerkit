---
name: avoid-ai-writing
description: Audit and rewrite prose to remove AI writing tells. Use when asked to clean AI-isms, de-slop, humanize, or check whether writing sounds machine-generated, and when reviewing any drafted prose before it ships.
---

# Avoid AI writing

Coalesced from the four most-used public guides plus the house rules already
enforced in this user's own tooling:

- conorbronsdon/avoid-ai-writing (tier system, modes, context profiles)
- ama-zingco/anti-ai-writing-skill (research-cited structural rules)
- hardikpandya/stop-slop (throat-clearing and emphasis lists, scoring)
- jalaalrd/anti-ai-slop-writing (era-tagged vocabulary, model tells)
- `resume-generator-artifact/STYLE-GUIDE.md` (this user's house style, which
  **wins every conflict** on career documents)

Long word tables live in `references/word-lists.md`. Load that file when doing
a full audit; the rules below are enough for a quick pass.

## The one idea that matters most

**Vocabulary tells expire. Structural tells persist.**

Word lists decay fast: "delve" and "tapestry" were 2023 markers, "increasingly"
and "significant" are the current ones, and models keep shifting. Em dash usage
has already reversed between model generations. Chasing banned words alone is a
treadmill.

Structure is the durable signal: uniform sentence length, symmetrical
paragraphs, three-item groupings, synonym cycling, sparse punctuation,
relentlessly neutral stance. Fix structure first, then vocabulary.

## Modes

- **Detect** (default when asked "does this sound AI?"): flag only, grouped by
  severity, and say which flags are judgment calls rather than defects.
- **Rewrite**: return the corrected text, then a **second pass** re-reading your
  own rewrite for tells that survived. If the second pass changed anything, say
  which version is the deliverable.
- **Edit in place**: minimal targeted edits to a file; report before → after per
  touched span; never touch code, config, tables, quoted or attributed text.

## P0 — credibility killers

- Chatbot artifacts: "Great question!", "I hope this helps", "Certainly!",
  "Let's dive in", "As an AI", "I'd be happy to".
- Cutoff disclaimers: "As of my last update", "While specific details are limited".
- Citation and tracking leaks: `citeturn0search0`, `oai_citation`,
  `utm_source=chatgpt.com`, `[attached_file:1]`.
- Unfilled placeholders: `[Your Name]`, `TODO`, `2025-XX-XX`.
- Vague attribution: "Experts believe", "Studies show", "Independent testing
  confirms" with no source. Name it or drop the claim.
- **Invented specifics.** A fabricated number, name, date, or mechanism is worse
  than the vague phrasing it replaced. If a concrete detail is missing, flag the
  gap; never fill it.

## P1 — obvious tells

**Structural (fix these first)**

- **Uniform sentence length.** If most sentences run 15–25 words it reads as
  machine output. Models produce roughly half to three-quarters of the
  sentence-length variance found in human writing. Follow a long sentence with a
  short one. Fragments are allowed.
- **Uniform paragraph length.** Vary deliberately; some one-sentence paragraphs.
- **Rule of three.** Models group in threes far more than humans. One
  "adjective, adjective, and adjective" per piece, maximum.
  - Distinguish the rhetorical tricolon from a **factual sequence**. "Surfaced
    their logs, traced the failures, and took the cause to engineering" is
    three real actions in order; "thoughtful, rigorous, and deeply human" is
    the tell. A regex counts both. Only the second is a defect — do not
    "fix" a sequence of things that actually happened.
- **"Not X, but Y"** and "not only… but also". Models deploy this far more often
  per thousand sentences than any human corpus. Also its split form: "The
  headline isn't the speed. The real story is Y."
- **Unparseable on one read.** Dropped relative pronouns and stacked modifiers
  produce garden paths: "the expert customer engineering teams built against"
  makes the reader misparse "expert customer" before recovering. Restore the
  pronoun or lead with the verb. In list items specifically, open with the
  action, not an article.
- **Synonym cycling.** AI rotates "developers… engineers… practitioners…
  builders", and rotates "says → notes → explains → emphasizes". Humans repeat
  the clearest word. Default to "says".
- **Sparse punctuation.** Models use fewer commas and semicolons and almost no
  parentheses. Sparse punctuation now signals AI more strongly than em dashes.
- **Overused "and".** The single most overused word in AI prose. Replace some
  with a period.
- **Long Latinate words.** Every major model overuses eight-letter-plus words.
  Prefer use over utilize, help over facilitate, start over commence.
- **Nominalizations.** "Conducted an evaluation of" → "evaluated". Find the
  buried verb.
- **Paragraph-reshuffle test.** If two body paragraphs can swap without breaking
  the piece, it is a list of points, not an argument.
- **Treadmill test.** Per paragraph, name the one fact or turn it adds. If there
  is none, cut it.

**Rhetorical**

- Throat-clearing openers: "Here's the thing", "The truth is", "Let me be
  clear", "What's interesting is", "I'll be honest".
- Emphasis crutches: "Full stop.", "Period.", "Let that sink in.", "Make no
  mistake", "This matters because".
- Meta-narration: "In this article we will explore", "Let's break this down",
  "First, let's consider", "Breaking this down".
- Rhetorical-question openers, and hypophora generally (posing a question only
  to answer it immediately).
- Transition scaffolding: "Moreover", "Furthermore", "Additionally",
  "In conclusion", "Overall", "When it comes to", "At the end of the day".
- Scene-setting and hypotheticals: "In today's fast-paced…", "In a world
  where…", "Imagine a world where…". (Fine as a genuine teaching device.)
- Significance inflation: "a pivotal moment", "a watershed moment", "marking a
  turning point" for routine events.
- Aphorism formulas: "X is the language of Y", "the architecture of trust".
- Hedge stacking: "could potentially", "may eventually unlock". Pick one hedge.
- Future-narrative closers: "may become one of the most important trends".
  Make a falsifiable prediction or cut.
- Generic closers: "The future looks bright", "Only time will tell".
- Performed candor: "Two caveats I'd rather flag than let you discover".
  Deletion test — if removing the frame loses no information, it was theater.
  A substantive admission ("I haven't tested this on Windows") stays.
- Self-labeling: calling your own point "the contrarian one" or "the surprising
  part". Let the content carry it.
- Lingering-attention claims: "the line I keep coming back to", unless the
  reason is attached.

**Formatting**

- Em dashes. House rule here is zero (see house overlay below); the public
  guides allow at most one per 1,000 words.
- Bold overuse; inline-header lists ("**Performance:** performance improved").
- Emoji as section markers.
- Bullet lists of bare noun phrases with no verbs.
- 3+ headings in under 300 words, or formulaic headers ("Overview", "Key
  Points", "Summary").
- Title Case headings; use sentence case.
- Hashtag stuffing (2–3 specific tags maximum).

## P2 — polish

Copula avoidance ("serves as", "boasts", "features" instead of "is"/"has");
hyphenated modifier stacking; unnecessary hyphenation; numbered-list inflation
("Five things to know"); parenthetical hedging; wall-of-text replies in
conversational registers.

## Vocabulary

See `references/word-lists.md` for the full tables:

- **Tier 1A** — frequency markers, always replace (delve, tapestry, realm,
  testament to, robust, seamless, leverage, game-changer, …).
- **Tier 1B** — clarity edits, same fix but weaker authorship signal (utilize,
  in order to, due to the fact that, …).
- **Tier 2** — flag in clusters of 2+ per paragraph (harness, foster, navigate,
  elevate, streamline, empower, crucial, myriad, cornerstone, …).
- **Tier 3** — normal words, flag only at high density (significant,
  increasingly, innovative, effective, compelling, unprecedented, …).

Current-era markers (2026) worth extra suspicion: *increasingly, significant,
implications, considerations, framework*. Never use two from the same tier list
in one paragraph.

## Rewriting: what never to add

Removal is half the job. A rewrite that clears every flag but reads sterile is
still machine output. Put voice back deliberately where the genre carries voice
— a reaction, a stated preference, one thought left unresolved. For technical,
legal, or encyclopedic text, plain and neutral *is* the correct human voice.

Never inject: fake first person ("in my experience") where the source had no
author presence; manufactured stakes; forced contrarianism; performed candor;
em dashes staged for drama; ordinary sentences chopped into fragments to fake
rhythm; or any specific the source did not contain.

**The test for every edit:** did this information come from the source?
Subtraction and sharpening are in scope. Adding stance, personality, or fact is
not.

## House overlay (this user — wins all conflicts)

- **Em dashes: zero.** Not "sparingly". Comma, colon, or two sentences.
- **No self-rating**: expert in, highly skilled, passionate about, seasoned,
  extensive experience. Let the evidence rate you.
- **No defensive framing** about a non-traditional path ("self-taught but",
  "no degree, but"). Replace apology with specificity. Never hide the path,
  never explain it.
- **Atmosphere is the real slop.** A clause describing a *feeling* of competence
  instead of an action ("owns the hard part", "stays in the room when it
  breaks") is the highest-priority rewrite. If there is no action underneath,
  cut the line.
- **Three-item lists**: banned in prose, allowed in scope-of-work resume bullets
  ("migrated X, built Y, and modernized Z"). The exception is bullet-scoped, not
  summary-scoped.
- **Numbers**: never invent one; any tenure or span figure must be computed from
  the timeline or absent. Spelled-out aggregates ("fifteen years of…") are the
  characteristic hallucination and slip past every mechanical check.
- **On career documents**, defer to `STYLE-GUIDE.md` and run
  `careerkit lint` — this skill does not replace those gates.

## Scoring (optional, for a quick verdict)

Rate 1–10 each, and say which one is dragging: **directness** (states or
announces?), **rhythm** (varied or metronomic?), **trust** (respects the
reader?), **authenticity** (sounds like a person?), **density** (anything
cuttable?). Under 35/50 needs revision.

## Boundaries

Never rewrite quoted material, code blocks, config, tables, or attributed text
— flag them instead. On a large file, confirm which section to clean before
changing anything. If the writing is already strong, say so and make only the
cuts that are needed.
