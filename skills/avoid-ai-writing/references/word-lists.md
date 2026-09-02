# Word and phrase tables

Load this for a full audit. Tiering follows conorbronsdon/avoid-ai-writing;
era tagging follows jalaalrd/anti-ai-slop-writing; the phrase groupings borrow
from hardikpandya/stop-slop.

**Vocabulary lists expire.** Treat any list here as a snapshot, and weight the
structural rules in SKILL.md higher when they disagree.

## Tier 1A — frequency markers (always replace)

These appear far more often in model output than in human prose.

| Replace | With |
|---|---|
| delve, delve into | explore, dig into, look at |
| tapestry | (describe the actual complexity) |
| landscape (figurative) | field, space, industry |
| realm | area, field, domain |
| paradigm | model, approach, framework |
| embark | start, begin |
| beacon | (rewrite the sentence) |
| testament to | shows, proves, demonstrates |
| robust | strong, reliable, solid |
| comprehensive | thorough, complete, full |
| cutting-edge | latest, newest, advanced |
| leverage (verb) | use |
| pivotal | important, key, critical |
| underscores | highlights, shows |
| meticulous, meticulously | careful, detailed, precise |
| seamless, seamlessly | smooth, easy |
| game-changer, game-changing | (say what changed, and why) |
| watershed moment | turning point, shift |
| nestled | sits, is located |
| vibrant | (describe the activity, or cut) |
| thriving | growing, active (or cite a number) |
| showcasing | showing, demonstrating |
| deep dive, dive into | look at, examine |
| unpack, unpacking | explain, break down |
| bustling | busy (or name what makes it busy) |
| intricate, intricacies | complex, detailed |
| ever-evolving | changing (or describe how) |
| enduring | lasting, long-running |
| daunting | hard, difficult |
| holistic, holistically | complete, full, whole |
| actionable | practical, useful, concrete |
| impactful | effective, significant (or describe the impact) |
| learnings | lessons, findings, takeaways |
| thought leader, thought leadership | expert, authority |
| best practices | what works, proven methods |
| at its core | (cut; state the thing) |
| synergy, synergies | (describe the combined effect) |
| interplay | relationship, connection |
| symphony (metaphor) | (describe the coordination) |
| embrace (metaphor) | adopt, use, switch to |
| garner, garnered | earn, win, collect |
| aforementioned | (name it again, or cut) |
| groundbreaking | new, first (or cite what came before) |

## Tier 1B — clarity edits (same fix, weaker signal)

utilize → use · in order to → to · due to the fact that → because ·
serves as → is · features (verb) → has, includes · boasts → has ·
presents → is, shows · commence → start · ascertain → find out ·
endeavor → effort, try · encompass → include, cover · facilitate → enable, help

## Tier 2 — flag in clusters (2+ in a paragraph)

Legitimate alone, suspicious together.

harness · navigate, navigating · foster, fostering · elevate · unleash ·
streamline · empower · bolster, bolstered · spearhead · resonate ·
revolutionize · underpin · nuanced · crucial · multifaceted · ecosystem
(metaphor) · myriad · plethora · catalyze · reimagine · galvanize · augment ·
cultivate · illuminate · elucidate · juxtapose · transformative · cornerstone ·
paramount · poised to · burgeoning · nascent · quintessential · overarching ·
quietly · deeply · underpinnings

## Tier 3 — flag only at high density

significant, significantly · increasingly · innovative, innovation ·
effective, effectively · dynamic, dynamics · scalable, scalability ·
compelling · unprecedented · exceptional · remarkable · sophisticated ·
instrumental · profound · stunning · world-class, state-of-the-art,
best-in-class · implications · considerations · framework

Fix by replacing with specifics: a number, a comparison, a named benchmark.

## Era tagging (why lists expire)

- **2023 – mid 2024**: delve, tapestry, testament, vibrant, pivotal, meticulous,
  intricate, interplay, bolstered, garner, underscore, landscape, boasts.
- **Mid 2024 – mid 2025**: align with, enhance, fostering, highlighting,
  showcasing, underscore, enduring.
- **Mid 2025 onward**: emphasizing, enhance, highlighting, showcasing.
- **2026 current**: significant, increasingly, consequences, implications,
  framework, considerations.

## Banned phrases

"In today's [adjective] [noun]" · "It's worth noting that" · "It's important to
note that" · "Let's dive in" · "At its core" · "In the realm of" · "When it
comes to" · "A testament to" · "Not just X, but Y" · "This is where X comes in"
· "Whether you're a X or a Y" · "From X to Y" · "At the end of the day" · "The
bottom line is" · "Here's the thing" · "Without further ado" · "In a nutshell"
· "Buckle up" · "Take it to the next level" · "Unlock the power of" · "Elevate
your" · "Supercharge your" · "Bridge the gap" · "Move the needle" · "In
conclusion" · "Firstly… Secondly… Thirdly" · "I hope this finds you well" ·
"Please don't hesitate to reach out" · "Rest assured" · "It goes without saying"

## Throat-clearing openers

"Here's the thing" · "Here's why that matters" · "The uncomfortable truth is" ·
"It turns out" · "The real X is" · "Let me be clear" · "The truth is" · "I'm
going to be honest" · "Can we talk about" · "Here's what I find interesting" ·
"Here's the problem though"

## Emphasis crutches (delete)

"Full stop." · "Period." · "Let that sink in." · "Make no mistake" · "This
matters because" · "I'll say it again"

## Hollow intensifiers and adverbs (default: delete)

really · just · literally · genuinely · honestly · simply · actually · truly ·
deeply · fundamentally · inherently · inevitably · interestingly · importantly ·
crucially · notably · certainly · surprisingly · quite frankly · to be honest ·
let's be clear

## Sentence and paragraph openers to avoid

Certainly · Absolutely · Sure · Great question · That's a great point · I'd be
happy to · As an AI · As a language model · However, it's important to ·
Moreover · Furthermore · Additionally · Interestingly · Notably · Importantly ·
Indeed

## Business jargon

navigate → handle, address · unpack → explain · lean into → accept, commit to ·
landscape → situation, field · game-changer → significant · double down →
commit, increase · deep dive → analysis · take a step back → reconsider ·
moving forward → next · circle back → revisit · on the same page → aligned ·
pain points → problems · value add → benefit · touch base → talk

## Vague declaratives (delete or make specific)

"The reasons are structural" · "The implications are significant" · "This is the
deepest problem" · "The stakes are high" · "The consequences are real" ·
"The results speak for themselves"

## Template constructions

- "a [adjective] step towards [adjective] [noun]" → name the capability
- "Whether you're X or Y" → pick the actual audience
- "I recently had the pleasure of [verb]ing" → say what happened
- "X is a feature, not a bug" → say what it does
- "Plot twist:" / "The catch?" / "The kicker?" → state the thing

## Research notes

- Russell et al. 2025 (arXiv:2501.15654): frequent LLM users detect AI text
  reliably. In their explanations, **vocabulary** was cited 53% of the time,
  **flawless grammar** 25%, **lack of originality** 24%.
- The Economist, July 2026: 55,940 sentences and 1.2m words compared across
  ChatGPT, Claude, Gemini and Grok against journalism and fiction. Findings used
  above: sentence-length variance runs at half to three-quarters of human
  levels; models overuse polysyllabic words; punctuation is sparser than human
  writing; em dash rates have reversed between model generations.
- Orwell 1946, "Politics and the English Language", is the origin of the
  short-Saxon-word preference.
