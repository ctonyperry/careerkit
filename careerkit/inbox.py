# ruff: noqa: E501  (the bookmarklet source is one long string on purpose)
"""Capture a posting from the browser into jd-inbox with one click.

    careerkit inbox --serve        # start the receiver, open the install page
    careerkit inbox                # list what is waiting

The receiver is a local HTTP server. The install page it serves carries a
bookmarklet: drag it to the bookmarks bar, click it on a posting, and the
page's text arrives here VERBATIM and is written as
jd-inbox/YYYY-MM-DD-<company>-<role>.md with the frontmatter the pipeline
reads. Nothing is summarised or reordered on the way in, because the
anti-contamination check later quotes the posting from this file and a
paraphrased capture poisons the run.

What it cannot see: whether the page was the whole posting. Sites fold long
descriptions behind a "show more"; the bookmarklet clicks the ones it knows
about and takes what is rendered. Read the file once before trusting it.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

DEFAULT_PORT = 8765

_SLUG = re.compile(r"[^a-z0-9]+")


def slug(text: str, limit: int = 40) -> str:
    return _SLUG.sub("-", text.lower()).strip("-")[:limit].rstrip("-") or "untitled"


def _frontmatter(fields: dict[str, str]) -> str:
    lines = ["---"]
    for key, value in fields.items():
        v = str(value).replace("\n", " ").strip()
        # Quote only what YAML would misread. A URL's "https:" is a plain
        # scalar; "Role: Senior" with colon-space is not, and neither is a
        # value opening with a flow or anchor character.
        if ": " in v or " #" in v or v[:1] in "\"'[{&*!|>%@`" or v.endswith(":"):
            v = '"' + v.replace('"', "'") + '"'
        lines.append(f"{key}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def write_capture(inbox: Path, capture: dict, today: dt.date | None = None) -> tuple[Path, bool]:
    """Write one capture. Returns (path, written). Never overwrites: a repost
    is a decision for the person, not the button."""
    inbox.mkdir(parents=True, exist_ok=True)
    today = today or dt.date.today()
    company = str(capture.get("company") or "unknown-company").strip()
    role = str(capture.get("role") or "untitled").strip()
    text = str(capture.get("text") or "").strip()
    if not text:
        raise ValueError("empty capture: no page text arrived")
    path = inbox / f"{today.isoformat()}-{slug(company)}-{slug(role)}.md"
    if path.exists():
        return path, False
    head = _frontmatter({
        "company": company,
        "role": role,
        "url": str(capture.get("url") or "pasted"),
        "captured": today.isoformat(),
        "status": "pending",
        "source": str(capture.get("source") or "bookmarklet"),
    })
    path.write_text(head + text + "\n", encoding="utf-8")
    return path, True


def pending(inbox: Path) -> list[tuple[str, str, str]]:
    """(file, company, role) for every inbox file whose status is pending."""
    out = []
    for p in sorted(inbox.glob("*.md")):
        head = p.read_text(encoding="utf-8").split("---", 2)
        if len(head) < 3:
            continue
        fields = dict(
            (k.strip(), v.strip().strip('"'))
            for k, _, v in (ln.partition(":") for ln in head[1].splitlines() if ":" in ln)
        )
        # "queued" is what the chat skill wrote for a posting saved for later.
        if fields.get("status", "pending") in {"pending", "queued"}:
            out.append((p.name, fields.get("company", ""), fields.get("role", "")))
    return out


# The bookmarklet. Plain ES5-ish so every browser runs it from a javascript:
# URL. It: expands folded descriptions it knows about, takes the job
# container's text where the site has one and the body otherwise, guesses
# company and role from the tab title, asks the person to confirm both, and
# posts to the receiver.
BOOKMARKLET_JS = """
(function(){
  var port=%d;
  var host=location.hostname;
  var q=function(s){return document.querySelector(s);};
  var clicks=document.querySelectorAll('button');
  for(var i=0;i<clicks.length;i++){
    var t=(clicks[i].innerText||'').trim().toLowerCase();
    if(t==='show more'||t==='see more'||t==='show full description'){try{clicks[i].click();}catch(e){}}
  }
  var pick=function(){
    var sels=['.jobs-description','#job-details','.jobs-box__html-content',
              '#jobDescriptionText','.jobsearch-JobComponent','[data-testid="jobsearch-ViewJobLayout-jobDisplay"]',
              'main','article'];
    for(var i=0;i<sels.length;i++){var el=q(sels[i]);if(el&&el.innerText&&el.innerText.length>400)return el.innerText;}
    return document.body.innerText;
  };
  var title=document.title||'';
  var company='',role='';
  var m;
  if(/linkedin/.test(host)){
    m=title.match(/^\\(?\\d*\\)?\\s*(.+?)\\s+at\\s+(.+?)\\s*\\|/); if(m){role=m[1];company=m[2];}
    var c=q('.job-details-jobs-unified-top-card__company-name, .jobs-unified-top-card__company-name');
    if(c&&c.innerText)company=c.innerText.trim();
    var r=q('h1'); if(r&&r.innerText)role=r.innerText.trim();
  } else if(/indeed/.test(host)){
    m=title.match(/^(.+?)\\s+-\\s+.+?\\s+-\\s+(.+?)\\s*\\|/); if(m){role=m[1];company=m[2];}
    var r2=q('h1'); if(r2&&r2.innerText)role=r2.innerText.trim();
    var c2=q('[data-testid="inlineHeader-companyName"], [data-company-name]');
    if(c2&&c2.innerText)company=c2.innerText.trim();
  } else {
    var r3=q('h1'); if(r3&&r3.innerText)role=r3.innerText.trim();
    m=title.match(/(?:at|@|-|\\|)\\s*([^|\\-]+)\\s*$/); if(m)company=m[1].trim();
  }
  setTimeout(function(){
    company=prompt('Company',company); if(company===null)return;
    role=prompt('Role',role); if(role===null)return;
    var body=JSON.stringify({url:location.href,title:title,company:company,role:role,text:pick(),source:'bookmarklet'});
    fetch('http://127.0.0.1:'+port+'/capture',{method:'POST',headers:{'Content-Type':'application/json'},body:body})
      .then(function(r){return r.json();})
      .then(function(j){alert(j.written?('Saved '+j.file+'\\nQueue: '+j.pending+' pending'):('Already captured: '+j.file));})
      .catch(function(e){alert('careerkit inbox is not running.\\nStart it with: careerkit inbox --serve');});
  },400);
})();
"""


def bookmarklet(port: int = DEFAULT_PORT) -> str:
    js = BOOKMARKLET_JS % port
    js = re.sub(r"\n\s*", "", js.strip())
    return "javascript:" + js


def install_page(inbox: Path, port: int) -> str:
    link = bookmarklet(port).replace("&", "&amp;").replace('"', "&quot;")
    queue = pending(inbox)
    rows = "".join(f"<li><code>{f}</code> {c} / {r}</li>" for f, c, r in queue) or "<li>nothing waiting</li>"
    return f"""<!doctype html><meta charset="utf-8"><title>careerkit inbox</title>
<style>body{{font:15px/1.5 system-ui,sans-serif;max-width:40em;margin:3em auto;padding:0 1em}}
a.bm{{display:inline-block;padding:.5em 1em;border:1px solid #888;border-radius:6px;background:#f4f4f4;text-decoration:none;color:#111;font-weight:600}}
code{{font-size:.9em}}</style>
<h1>careerkit inbox</h1>
<p>Receiving at <code>http://127.0.0.1:{port}</code>, writing to <code>{inbox}</code>.</p>
<p>Drag this to your bookmarks bar:</p>
<p><a class="bm" href="{link}">Save JD</a></p>
<p>Then open a posting on LinkedIn, Indeed, or a company site and click it. It
confirms the company and role, sends the page text here verbatim, and tells you
the queue depth. It never overwrites a file it already wrote.</p>
<h2>Pending</h2><ul>{rows}</ul>
"""


class _Handler(BaseHTTPRequestHandler):
    inbox: Path = Path("jd-inbox")
    port: int = DEFAULT_PORT

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        body = install_page(self.inbox, self.port).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            capture = json.loads(raw.decode("utf-8"))
            path, written = write_capture(self.inbox, capture)
            payload = {"file": path.name, "written": written, "pending": len(pending(self.inbox))}
            status = 200
        except (ValueError, json.JSONDecodeError) as exc:
            payload = {"error": str(exc)}
            status = 400
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        if status == 200:
            verb = "wrote" if payload["written"] else "already had"
            print(f"[inbox] {verb} {payload['file']} ({payload['pending']} pending)")

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return  # quiet; the POST handler prints what matters


def serve(inbox: Path, port: int = DEFAULT_PORT, open_browser: bool = True) -> None:
    handler = type("InboxHandler", (_Handler,), {"inbox": inbox, "port": port})
    server = HTTPServer(("127.0.0.1", port), handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"[inbox] receiving at {url}, writing to {inbox}. Ctrl+C to stop.")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[inbox] stopped")
    finally:
        server.server_close()
