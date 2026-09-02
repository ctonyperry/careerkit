# JD Parse Prompt (LLM step, run in Claude Code chat)

Parse a job description into the JSON shape below and save it next to the JD
as `<jd-name>-parsed.json`. Then run:

    careerkit gap --jd <jd-name>-parsed.json

## Rules

- `requirements[].skills` may ONLY use canonical tags that exist under
  `aliases:` in `data/skills.yaml`. Do not invent tags.
- JD language you cannot map to a canonical tag goes in `unknown_terms`.
  Tony confirms each as a new alias (or dismisses it); never guess silently.
- `title_to_mirror`: the closest honest mirror of the JD's title
  (e.g. JD "Solutions Consultant" + actual title "Technical Consultant"
  mirrors as "Technical Solutions Consultant").
- `register` stays null. Tony picks register from a menu at write time;
  it is never auto-classified.
- Split the JD into one requirement per distinct want. Keep the JD's own
  wording in `text`; the recovery question quotes it back to Tony.
- `weight` is "required" or "preferred" per the JD's own framing.

## Shape

```json
{
  "source": "path/to/jd.md",
  "title_to_mirror": "...",
  "role_family": "...",
  "seniority": "...",
  "register": null,
  "requirements": [
    {"id": "kebab-slug", "text": "the JD's own words", "skills": ["canonical-tag"], "weight": "required"}
  ],
  "unknown_terms": []
}
```

A worked example: `tests/fixtures/figma-jd-parsed.json` (parses
`examples/figma-jd.md`).
