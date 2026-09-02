# Evaluation

Three layers, cheapest and most reliable first. The ordering is deliberate:
this project's own history records validators that produced output without
changing a decision (careerkit's v1 measured Claim F1 0.36 with adversarial
validators in place; career-graph's quality gates "never throw, never
re-prompt, never block"). Anything here that stops changing decisions should be
deleted rather than kept for appearances.

## 1. Deterministic scorecard — `tools/metrics.py`

No model involved. Measured page count, bullets stating a result, bullets
opening with a verb, sentence-length variance, prose tricolons, type-token
ratio, domain terms absent from the JD, skills-line terms no bullet supports.
`--baseline` writes `metrics.json` into the run so changes are comparable.

Every measure here changed a decision by hand before it was automated.

## 2. Defect regression — `defects.yaml` + `tools/regress.py`

Every quality failure this project shipped or nearly shipped, with provenance:
what the text was, who caught it, and which gate catches it now. Replays each
against the real gates.

`enforced_by: human` is an honest verdict, not a gap. Six defects are recorded
that way, each with the reason mechanisation would be wrong. The approval-framed
boast is the clearest: "brought in to break a renewal-blocking problem" is also
approval-framed and reads well, so the test is what the sentence is about, which
no regex can see.

On its first run this found four claimed enforcements that no longer fired,
including a tenure rule that permitted the exact figure it was written to block.

## 3. Expert panel — `tools/panel.py`

Reviewers differ by **what they are given**, not by an adjective in a prompt.

| Reviewer | Gets | Cannot see | Answers |
|---|---|---|---|
| recruiter | only what fits above the fold (name, title, summary, first role, first bullets) | the JD, the rest of the resume | keep or pass, on what |
| hiring manager | full application plus the JD | nothing | interview or decline, what to probe, what is missing |
| writing critic | full application, company name masked | the JD, the target | does this read as human |
| skeptic | the corpus, spine, declined list, JD | nothing | is every claim true and sourced |

The recruiter slice is principled rather than arbitrary: eye-tracking research
puts a seven-second scan on the name, current title, most recent company, and
first two or three bullets, so that is exactly what the packet contains.

The critic's masking matters most. Given the posting, a reviewer rationalises a
weak sentence as relevant; without it, the only question left is whether a
person wrote it.

Run `python tools/panel.py runs/<run-dir>`, then spawn one agent per packet.
