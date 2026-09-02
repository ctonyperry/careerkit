# Resume Critique Prompt (LLM step, run in Claude Code chat)

The ADVISORY validation lane. Runs AFTER the mechanical linter passes
(`careerkit lint`). You annotate; you never block. Deterministic code blocks;
the human decides; you point at what reads as slop and propose the specific fix.

    careerkit lint <draft>.md      # mechanical BLOCKs fixed first
    # then: critique the draft in chat with this prompt (advisory notes only)

You catch two things the mechanical linter cannot, because they are semantic,
not lexical. For each hit: quote the phrase, name the category, and rewrite it
concretely. The fix is ALWAYS the same move: replace the feeling with the
specific action or fact underneath it. If there is no specific fact underneath,
say so, because that means the line is empty and should be cut.

## Category 1: atmosphere-poses

A clause describing a FEELING of competence instead of a concrete action. It
sounds like seniority; it says nothing. It survives the mechanical linter
because none of its words are banned.

- "owns the hard part" -> what part, and what did you do to it?
- "the person who stays in the room when it breaks" -> which incident, what did
  you actually do when it broke?
- "brings a bias for action" -> cut, or name the action.
- "thrives in ambiguity" -> name the ambiguous situation and the call you made.

Rewrite example:
- BEFORE: "Owns the hard integration problems others avoid."
- AFTER: "Took over a stalled reporting integration after the customer had lost
  faith in it, and closed it at a perfect satisfaction score."
  (The specific instance was always the point; the pose was hiding it.)

## Category 2: defensive / compensatory framing

Language that apologizes for or over-explains a non-traditional path. It reads
as insecurity and it is also self-rating. The path is not a liability to
manage; it is a fact to state plainly and move past.

- "self-taught fast learner" -> cut the self-rating; show the learning as work.
- "no formal degree, but..." / "despite not having a CS degree" -> delete the
  apology entirely. Never explain the absence of a credential.
- "scrappy" / "wears many hats" -> name the specific range of work instead.

Rewrite example:
- BEFORE: "Self-taught engineer who, despite no formal degree, learns fast."
- AFTER: "Tested out of high school by examination; ran technical operations
  for 400+ member companies by 25."
  (Specificity replaces apology. Never hide the path, never explain it.)

## Category 3: JD-mirroring in the summary

A summary that paraphrases the posting back at the reader instead of telling
the career's trajectory. The mechanical linter flags this as `jd-mirroring`
when `--jd` is passed, by counting reused JD vocabulary; your job is the
judgment the counter cannot make, and the rewrite.

Why it is a defect, not just a style preference. The bullets already argue fit:
they were selected against this JD deterministically, so the page is targeted
whether or not the summary says so. That makes the mirror redundant. It is also
the most commoditized sentence on the page, because every other applicant is
mirroring the same posting. And it reads eager, which is the wrong footing.

- "Enterprise consultant who guides customer engineering teams from integration
  design through production rollout" -> that is the JD's bullet in first person.
- Any summary that could only have been written after reading this specific
  posting is suspect. A trajectory summary would be nearly the same across
  applications, with only the emphasis shifting.

The fix is the same shape as the other two categories: replace the claim about
fit with the concrete facts of the path.

Rewrite example:
- BEFORE: "Enterprise technical consultant who guides customer engineering teams
  from integration design through production rollout, then traces what breaks at
  scale to root cause."
- AFTER: "Thirty-one years in software, starting at a tier-2 support desk in
  1995. Ran technical operations for a management-education network, owned a
  learning platform end to end, then spent six years at LinkedIn on its
  enterprise integrations."
  (Trajectory a reader cannot get from the posting, and cannot get from anyone
  else's resume either.)

Note: this category applies ONLY to the summary. Bullets should share the JD's
domain vocabulary; that is what selection is for.

## Output

An advisory note list next to the draft. For each finding:

    - line / quote: "<the exact phrase>"
      category: atmosphere-pose | defensive-framing
      rewrite: "<the concrete version, or 'cut: no specific fact underneath'>"

Close with the honest summary: if the draft is clean of both categories, say so
plainly. Do not manufacture findings to look thorough; a clean draft is the goal.
