"""Render a run directory into a single self-contained review page.

    python tools/review_page.py runs/<run-dir> [-o out.html]

The page is the CP5 surface: verdict and gate state first, then coverage, then
every claim with the evidence unit behind it, then the documents themselves.
Report chrome is sans/mono; the documents are set in serif, so what is under
review reads differently from what is reviewing it.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from crosscheck import DEFAULT_SPINE, run_checks  # noqa: E402

FONTS = (
    "https://fonts.googleapis.com/css2?"
    "family=IBM+Plex+Mono:wght@400;500&"
    "family=IBM+Plex+Sans:wght@400;500;600;700&"
    "family=IBM+Plex+Serif:ital,wght@0,400;0,600;1,400&display=swap"
)

CSS = """
:root {
  --ground: #f4f6f9;
  --surface: #ffffff;
  --surface-2: #eef1f6;
  --ink: #131922;
  --ink-muted: #5b6675;
  --rule: #d9dfe8;
  --accent: #1f4b99;
  --accent-soft: #e5ecf8;
  --pass: #14704a;
  --pass-soft: #e0f0e8;
  --warn: #8a5d04;
  --warn-soft: #f8eed6;
  --block: #a8342a;
  --block-soft: #f8e3e0;
  --shadow: 0 1px 2px rgba(19, 25, 34, .06), 0 8px 24px rgba(19, 25, 34, .05);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ground: #0e1219;
    --surface: #161c25;
    --surface-2: #1d2531;
    --ink: #e6ebf2;
    --ink-muted: #939eae;
    --rule: #2a3441;
    --accent: #8fb0ea;
    --accent-soft: #1b2740;
    --pass: #5cc493;
    --pass-soft: #14291f;
    --warn: #e2ac47;
    --warn-soft: #2c2312;
    --block: #f0817a;
    --block-soft: #2e1a19;
    --shadow: 0 1px 2px rgba(0, 0, 0, .4), 0 8px 24px rgba(0, 0, 0, .3);
  }
}
:root[data-theme="dark"] {
  --ground: #0e1219;
  --surface: #161c25;
  --surface-2: #1d2531;
  --ink: #e6ebf2;
  --ink-muted: #939eae;
  --rule: #2a3441;
  --accent: #8fb0ea;
  --accent-soft: #1b2740;
  --pass: #5cc493;
  --pass-soft: #14291f;
  --warn: #e2ac47;
  --warn-soft: #2c2312;
  --block: #f0817a;
  --block-soft: #2e1a19;
  --shadow: 0 1px 2px rgba(0, 0, 0, .4), 0 8px 24px rgba(0, 0, 0, .3);
}

* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--ground);
  color: var(--ink);
  font-family: "IBM Plex Sans", system-ui, -apple-system, sans-serif;
  font-size: 16px;
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}
.wrap { max-width: 60rem; margin: 0 auto; padding: 2.5rem 1.25rem 5rem; }
.stack { display: flex; flex-direction: column; }
.gap-lg { gap: 2.5rem; } .gap-md { gap: 1.25rem; } .gap-sm { gap: .6rem; }

.eyebrow {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: .75rem; letter-spacing: .1em; text-transform: uppercase;
  color: var(--ink-muted);
}
h1 {
  font-size: clamp(1.75rem, 4.5vw, 2.5rem); line-height: 1.15; margin: .2rem 0 0;
  font-weight: 600; letter-spacing: -.02em; text-wrap: balance;
}
h2 {
  font-size: 1.15rem; font-weight: 600; margin: 0; letter-spacing: -.01em;
  display: flex; align-items: baseline; gap: .6rem;
}
h2 .n {
  font-family: "IBM Plex Mono", monospace; font-size: .8rem; color: var(--accent);
  font-weight: 500;
}
h3 { font-size: .95rem; font-weight: 600; margin: 0; }
p { margin: 0; }
a { color: var(--accent); }

.panel {
  background: var(--surface); border: 1px solid var(--rule); border-radius: 10px;
  padding: 1.25rem 1.35rem; box-shadow: var(--shadow);
}
.verdict { border-left: 4px solid var(--accent); }
.verdict .role { color: var(--ink-muted); font-size: 1rem; }

.chips { display: flex; flex-wrap: wrap; gap: .5rem; }
.chip {
  display: inline-flex; align-items: center; gap: .45rem;
  font-family: "IBM Plex Mono", monospace; font-size: .78rem;
  padding: .3rem .6rem; border-radius: 999px; border: 1px solid transparent;
  white-space: nowrap;
}
.chip .dot { width: .5rem; height: .5rem; border-radius: 50%; background: currentColor; flex: none; }
.chip.pass { color: var(--pass); background: var(--pass-soft); border-color: color-mix(in srgb, var(--pass) 25%, transparent); }
.chip.warn { color: var(--warn); background: var(--warn-soft); border-color: color-mix(in srgb, var(--warn) 25%, transparent); }
.chip.block { color: var(--block); background: var(--block-soft); border-color: color-mix(in srgb, var(--block) 30%, transparent); }
.chip.info { color: var(--accent); background: var(--accent-soft); border-color: color-mix(in srgb, var(--accent) 22%, transparent); }

.gates { display: grid; grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr)); gap: .75rem; }
.gate {
  background: var(--surface-2); border-radius: 8px; padding: .8rem .9rem;
  display: flex; flex-direction: column; gap: .35rem; border: 1px solid var(--rule);
}
.gate .name { font-family: "IBM Plex Mono", monospace; font-size: .75rem; color: var(--ink-muted); text-transform: uppercase; letter-spacing: .08em; }
.gate .val { font-size: .9rem; font-weight: 500; }

.counts { display: flex; gap: 1.5rem; flex-wrap: wrap; }
.count .num { font-size: 2rem; font-weight: 600; font-variant-numeric: tabular-nums; line-height: 1; }
.count .lbl { font-family: "IBM Plex Mono", monospace; font-size: .72rem; text-transform: uppercase; letter-spacing: .08em; color: var(--ink-muted); }
.count.pass .num { color: var(--pass); }
.count.warn .num { color: var(--warn); }
.count.block .num { color: var(--block); }

.scroll { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: .88rem; }
th, td { text-align: left; padding: .55rem .7rem; border-bottom: 1px solid var(--rule); vertical-align: top; }
th { font-family: "IBM Plex Mono", monospace; font-size: .72rem; text-transform: uppercase; letter-spacing: .07em; color: var(--ink-muted); font-weight: 500; }
tbody tr:last-child td { border-bottom: none; }
code, .uid {
  font-family: "IBM Plex Mono", monospace; font-size: .82em;
  background: var(--surface-2); padding: .1rem .35rem; border-radius: 4px;
  color: var(--accent); white-space: nowrap;
}

.finding { display: flex; align-items: flex-start; gap: .75rem; padding: .7rem 0; border-bottom: 1px solid var(--rule); }
.finding:last-child { border-bottom: none; }
.finding .sev { flex: none; }
.finding .body { display: flex; flex-direction: column; gap: .3rem; min-width: 0; }
.finding .msg { font-size: .9rem; }
.finding .ex { font-family: "IBM Plex Mono", monospace; font-size: .78rem; color: var(--ink-muted); overflow-wrap: anywhere; }

ol.decisions { margin: 0; padding-left: 1.2rem; display: flex; flex-direction: column; gap: .7rem; }
ol.decisions li::marker { font-family: "IBM Plex Mono", monospace; font-size: .85rem; color: var(--accent); }
ol.decisions strong { font-weight: 600; }

.doc {
  background: var(--surface); border: 1px solid var(--rule); border-radius: 10px;
  padding: 2rem 2.1rem; box-shadow: var(--shadow);
  font-family: "IBM Plex Serif", Georgia, serif; font-size: .95rem; line-height: 1.6;
}
.doc h1 { font-size: 1.5rem; font-weight: 600; letter-spacing: 0; margin: 0 0 .2rem; }
.doc h2 { font-size: 1.05rem; display: block; margin: 1.4rem 0 .5rem; padding-bottom: .25rem; border-bottom: 1px solid var(--rule); font-family: "IBM Plex Sans", sans-serif; letter-spacing: .01em; }
.doc h3 { font-size: .98rem; margin: 1.2rem 0 .2rem; font-family: "IBM Plex Sans", sans-serif; }
.doc p { margin: .5rem 0; }
.doc ul { margin: .5rem 0; padding-left: 1.1rem; display: flex; flex-direction: column; gap: .45rem; }
.doc em { color: var(--ink-muted); }
.doc .contact { font-family: "IBM Plex Sans", sans-serif; font-size: .85rem; color: var(--ink-muted); }

details.docwrap { margin: 0; }
details.docwrap > summary {
  cursor: pointer; list-style: none; padding: .8rem 1rem; border-radius: 8px;
  background: var(--surface-2); border: 1px solid var(--rule);
  font-weight: 600; font-size: .95rem;
  display: flex; align-items: center; justify-content: space-between; gap: 1rem;
}
details.docwrap > summary::-webkit-details-marker { display: none; }
details.docwrap > summary .hint { font-family: "IBM Plex Mono", monospace; font-size: .75rem; color: var(--ink-muted); font-weight: 400; }
details.docwrap[open] > summary { border-radius: 8px 8px 0 0; border-bottom: none; }
details.docwrap[open] > .doc { border-radius: 0 0 10px 10px; }
summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

footer { color: var(--ink-muted); font-size: .82rem; border-top: 1px solid var(--rule); padding-top: 1rem; }
@media (max-width: 34rem) { .doc { padding: 1.4rem 1.2rem; } .wrap { padding-top: 1.5rem; } }
"""


def esc(text: str) -> str:
    return html.escape(str(text), quote=False)


def inline_md(text: str) -> str:
    text = esc(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    return text


def md_to_html(md: str) -> str:
    """Small renderer: headings, bullets, paragraphs. Enough for a resume or
    letter, which is all this ever receives."""
    out: list[str] = []
    in_list = False
    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            if in_list:
                out.append("</ul>")
                in_list = False
            continue
        heading = re.match(r"^(#{1,4})\s+(.*)$", line)
        bullet = re.match(r"^[-*]\s+(.*)$", line)
        if heading and in_list:
            out.append("</ul>")
            in_list = False
        if heading:
            level = min(len(heading.group(1)), 3)
            out.append(f"<h{level}>{inline_md(heading.group(2))}</h{level}>")
        elif bullet:
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline_md(bullet.group(1))}</li>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            css = " class=\"contact\"" if "·" in line and "@" in line else ""
            out.append(f"<p{css}>{inline_md(line)}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def coverage_counts(gap_md: str) -> dict[str, int]:
    counts = {"HIT": 0, "THIN": 0, "MISS": 0, "DECLINED": 0}
    for line in gap_md.splitlines():
        if not line.startswith("| ") or line.startswith("| Requirement"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 2 and cells[1] in counts:
            counts[cells[1]] += 1
    return counts


def section(number: str, title: str, body: str) -> str:
    return (
        f'<section class="stack gap-md"><h2><span class="n">{number}</span>{esc(title)}</h2>'
        f"{body}</section>"
    )


def build(run_dir: Path, spine: Path) -> str:
    manifest = yaml.safe_load((run_dir / "manifest.yaml").read_text(encoding="utf-8"))
    company = manifest.get("company", "")
    role = manifest.get("role", "")
    findings = run_checks(run_dir, spine)
    blocks = [f for f in findings if f.severity == "BLOCK"]
    warns = [f for f in findings if f.severity != "BLOCK"]

    gap_path = run_dir / "gap-report.md"
    counts = coverage_counts(gap_path.read_text(encoding="utf-8")) if gap_path.exists() else {}

    parts: list[str] = []

    # Verdict
    ready = not blocks
    state_chip = (
        '<span class="chip pass"><span class="dot"></span>gates clear</span>'
        if ready
        else f'<span class="chip block"><span class="dot"></span>{len(blocks)} blocking</span>'
    )
    parts.append(
        f'<header class="panel verdict stack gap-sm">'
        f'<div class="eyebrow">Application review · {esc(manifest.get("captured", ""))}</div>'
        f"<h1>{esc(company)}</h1>"
        f'<div class="role">{esc(role)}</div>'
        f'<div class="chips" style="margin-top:.5rem">{state_chip}'
        f'<span class="chip info"><span class="dot"></span>{esc(manifest.get("status", ""))}</span>'
        f'<span class="chip info"><span class="dot"></span>verdict: {esc(manifest.get("verdict", "n/a"))}</span>'
        f"</div>"
        f'<p style="margin-top:.6rem;color:var(--ink-muted);font-size:.92rem">'
        f'{inline_md(manifest.get("verdict_notes", ""))}</p>'
        f"</header>"
    )

    # Gates
    gates = manifest.get("gates", {}) or {}
    gate_cards = "".join(
        f'<div class="gate"><span class="name">{esc(k)}</span>'
        f'<span class="val">{esc(v)}</span></div>'
        for k, v in gates.items()
    )
    cross = (
        f'<div class="gate"><span class="name">crosscheck (live)</span><span class="val">'
        f'{len(blocks)} blocking, {len(warns)} advisory</span></div>'
    )
    parts.append(
        section(
            "CP4",
            "Gates",
            f'<div class="gates">{gate_cards}{cross}</div>'
            + (
                '<div class="panel stack gap-sm">'
                + "".join(
                    f'<div class="finding"><span class="sev chip '
                    f'{"block" if f.severity == "BLOCK" else "warn"}">'
                    f'<span class="dot"></span>{esc(f.severity.lower())}</span>'
                    f'<div class="body"><span class="msg"><code>{esc(f.rule)}</code> '
                    f"{esc(f.doc)}:{f.line} &middot; {esc(f.message)}</span>"
                    + (f'<span class="ex">{esc(f.excerpt)}</span>' if f.excerpt else "")
                    + "</div></div>"
                    for f in findings
                )
                + "</div>"
                if findings
                else ""
            ),
        )
    )

    # Non-capability requirements (credential, tenure) have no skills, so
    # careerkit's coverage defaults them to HIT and does the real assessment in
    # the strategy notes. Showing "HIT" against a degree requirement would read
    # as "you have the degree", so relabel them from the parsed JD.
    kinds: dict[str, str] = {}
    parsed_name = manifest.get("parsed_jd")
    if parsed_name and (run_dir / parsed_name).exists():
        import json

        parsed = json.loads((run_dir / parsed_name).read_text(encoding="utf-8"))
        for req in parsed.get("requirements", []):
            if req.get("kind", "capability") != "capability":
                kinds[req["text"][:80]] = req["kind"]

    # Coverage
    if counts:
        # Keep the tally to capability requirements so it agrees with the table.
        counts["HIT"] = max(0, counts.get("HIT", 0) - len(kinds))
        cards = "".join(
            f'<div class="count {cls}"><div class="num">{counts.get(key, 0)}</div>'
            f'<div class="lbl">{key.lower()}</div></div>'
            for key, cls in (("HIT", "pass"), ("THIN", "warn"), ("MISS", "block"), ("DECLINED", ""))
            if counts.get(key)
        )
        rows = ""
        for line in (run_dir / "gap-report.md").read_text(encoding="utf-8").splitlines():
            if not line.startswith("| ") or line.startswith("| Requirement") or set(line) <= set("|- "):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 2 or cells[1] not in counts:
                continue
            req = cells[0]
            kind = kinds.get(req[:80])
            if kind:
                cls, label = "info", kind
            else:
                cls = {"HIT": "pass", "THIN": "warn", "MISS": "block"}.get(cells[1], "info")
                label = cells[1]
            req = req if len(req) < 150 else req[:147] + "..."
            rows += (
                f"<tr><td>{esc(req)}</td>"
                f'<td><span class="chip {cls}"><span class="dot"></span>{esc(label)}</span></td></tr>'
            )
        # Tenure math and credential strategy, verbatim from the gap report.
        gap_md = (run_dir / "gap-report.md").read_text(encoding="utf-8")
        notes = ""
        for heading, title in (("## Tenure", "Tenure"), ("## Strategy notes", "Credential")):
            block = re.search(re.escape(heading) + r"[^\n]*\n(.*?)(?=\n## |\Z)", gap_md, re.S)
            if not block:
                continue
            text = " ".join(
                line.strip(" -")
                for line in block.group(1).strip().splitlines()
                if line.strip() and not line.startswith("#")
            )
            if text:
                notes += (
                    f'<div class="finding"><span class="sev chip info">'
                    f'<span class="dot"></span>{esc(title.lower())}</span>'
                    f'<div class="body"><span class="msg">{inline_md(text)}</span></div></div>'
                )
        parts.append(
            section(
                "CP1",
                "Requirement coverage",
                f'<div class="panel stack gap-md"><div class="counts">{cards}</div>'
                f'<div class="scroll"><table><thead><tr><th>Requirement</th><th>Coverage</th></tr>'
                f"</thead><tbody>{rows}</tbody></table></div>"
                + (f'<div class="stack">{notes}</div>' if notes else "")
                + "</div>",
            )
        )

    # Claim sheet + decisions
    sheet_name = manifest.get("claim_sheet")
    if sheet_name and (run_dir / sheet_name).exists():
        sheet = (run_dir / sheet_name).read_text(encoding="utf-8")
        decisions = re.search(r"## Open decisions[^\n]*\n(.*?)(?=\n## |\Z)", sheet, re.S)
        table = re.search(r"\| Section \| Bullet \| Evidence \|\n\|[^\n]*\n((?:\|[^\n]*\n)+)", sheet)
        body = ""
        if table:
            rows = ""
            for line in table.group(1).strip().splitlines():
                cells = [c.strip() for c in line.strip("|").split("|")]
                if len(cells) >= 3:
                    ev = re.sub(r"`([^`]+)`", r'<span class="uid">\1</span>', esc(cells[2]))
                    rows += (
                        f"<tr><td>{esc(cells[0])}</td><td>{esc(cells[1])}</td><td>{ev}</td></tr>"
                    )
            body += (
                f'<div class="panel"><div class="scroll"><table><thead><tr>'
                f"<th>Section</th><th>Claim</th><th>Evidence</th></tr></thead>"
                f"<tbody>{rows}</tbody></table></div></div>"
            )
        parts.append(section("CP2", "Claims and their evidence", body))

        if decisions:
            items = ""
            for match in re.finditer(r"^\d+\.\s+(.*?)(?=^\d+\.\s|\Z)", decisions.group(1), re.S | re.M):
                text = " ".join(match.group(1).split())
                items += f"<li>{inline_md(text)}</li>"
            parts.append(
                section(
                    "CP5",
                    "Decisions waiting on you",
                    f'<div class="panel"><ol class="decisions">{items}</ol></div>',
                )
            )

    # Documents
    docs = ""
    for name in manifest.get("documents", []):
        path = run_dir / name
        if not path.exists():
            continue
        label = "Resume" if "resume" in name else "Cover letter"
        docs += (
            f'<details class="docwrap"{" open" if "resume" in name else ""}>'
            f"<summary>{esc(label)}<span class=\"hint\">{esc(name)}</span></summary>"
            f'<article class="doc">{md_to_html(path.read_text(encoding="utf-8"))}</article>'
            f"</details>"
        )
    parts.append(section("CP3", "Documents", f'<div class="stack gap-md">{docs}</div>'))

    parts.append(
        f"<footer>Generated from <code>{esc(run_dir.name)}</code> by "
        f"<code>tools/review_page.py</code>. Coverage and gate results are read from the run; "
        f"the cross-document check runs live at build time against "
        f"<code>spine.yaml</code> and the JD on disk.</footer>"
    )

    return (
        f'<title>{esc(company)} Application Review</title>\n'
        f'<link rel="stylesheet" href="{FONTS}">\n'
        f"<style>{CSS}</style>\n"
        f'<div class="wrap stack gap-lg">{"".join(parts)}</div>'
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a run into a review page.")
    parser.add_argument("run_dir")
    parser.add_argument("-o", "--out", default=None)
    parser.add_argument("--spine", default=str(DEFAULT_SPINE))
    args = parser.parse_args(argv)

    run_dir = Path(args.run_dir)
    out = Path(args.out) if args.out else run_dir / "review.html"
    out.write_text(build(run_dir, Path(args.spine)), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
