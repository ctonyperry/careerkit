# ruff: noqa: E501  (the bookmarklet and relay sources are long strings on purpose)
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

How the text gets here matters. A bookmarklet runs as a script of the page it
is clicked on, and job sites ship a Content Security Policy that blocks page
scripts from calling any origin the site did not list. The first version
fetched the receiver directly and LinkedIn refused it before it left the tab.
So the button opens a small window on the receiver and hands it the posting
with postMessage, which no CSP governs; the receiver's own page does the
write, same-origin. Nothing crosses an origin except a message.

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


# The bookmarklet. Plain ES5 so every browser runs it from a javascript: URL.
# It expands folded descriptions it knows about, reads title and company from
# the page's own elements (asking only when it finds nothing), takes the job
# container's text where the site has one and the body otherwise, opens the
# receiver's relay window, and hands it the posting by postMessage once the
# relay says it is ready.
BOOKMARKLET_JS = """
(function(){
  var port=%d;
  var origin='http://127.0.0.1:'+port;
  var host=location.hostname;
  var q=function(s){var el=document.querySelector(s);return el&&el.innerText?el.innerText.trim():'';};
  var first=function(list){for(var i=0;i<list.length;i++){var v=q(list[i]);if(v)return v;}return '';};
  var pane=function(){
    var sels=['.jobs-search__job-details--container','.scaffold-layout__detail','.job-view-layout',
              '.jobs-details','.jobs-description__content','#job-details','.jobs-description','.jobs-box__html-content',
              '.show-more-less-html__markup','.description__text',
              '#jobDescriptionText','.jobsearch-JobComponent','[data-testid="jobsearch-ViewJobLayout-jobDisplay"]',
              'main','article'];
    for(var i=0;i<sels.length;i++){var el=document.querySelector(sels[i]);if(el&&el.innerText&&el.innerText.length>400)return el;}
    return document.body;
  };
  var box=pane();
  var buttons=box.querySelectorAll('button');
  for(var i=0;i<buttons.length;i++){
    var t=(buttons[i].innerText||'').replace(/[^a-z ]/gi,'').trim().toLowerCase();
    if(t.length<24&&/(show|see) (more|full)/.test(t)){try{buttons[i].click();}catch(e){}}
  }
  var pick=function(){return pane().innerText;};
  var title=document.title||'';
  var company='',role='',m;
  if(/linkedin/.test(host)){
    role=first(['.job-details-jobs-unified-top-card__job-title h1','.job-details-jobs-unified-top-card__job-title','h1.top-card-layout__title','h1.t-24','h1']);
    company=first(['.job-details-jobs-unified-top-card__company-name a','.job-details-jobs-unified-top-card__company-name','.jobs-unified-top-card__company-name a','.jobs-unified-top-card__company-name','a.topcard__org-name-link','.topcard__flavor']);
    if(!company){m=title.match(/^\\(?\\d*\\)?\\s*(.+?)\\s*\\|\\s*(.+?)\\s*\\|\\s*LinkedIn/i); if(m){if(!role)role=m[1];company=m[2];}}
    if(!company){m=title.match(/^(.+?)\\s+hiring\\s+(.+?)\\s+in\\s/i); if(m){company=m[1];if(!role)role=m[2];}}
  } else if(/indeed/.test(host)){
    role=first(['h1[data-testid="jobsearch-JobInfoHeader-title"]','h1.jobsearch-JobInfoHeader-title','h1']).replace(/\\s*-\\s*job post$/i,'');
    company=first(['[data-testid="inlineHeader-companyName"] a','[data-testid="inlineHeader-companyName"]','div[data-company-name="true"]','[data-testid="jobsearch-CompanyInfoContainer"] a']);
    if(!company){m=title.match(/^(.+?)\\s+-\\s+.+?\\s+-\\s+(.+?)\\s*\\|/); if(m){if(!role)role=m[1];company=m[2];}}
  } else {
    role=first(['h1']);
    m=title.match(/(?:\\bat\\b|@|\\||-)\\s*([^|\\-]+?)\\s*$/); if(m)company=m[1].trim();
  }
  role=role.replace(/^\\(?\\d*\\)?\\s*/,'').trim();
  var url=location.href;
  m=url.match(/[?&]currentJobId=(\\d+)/); if(m&&/linkedin/.test(host))url='https://www.linkedin.com/jobs/view/'+m[1]+'/';
  m=url.match(/[?&](?:jk|vjk)=([a-f0-9]+)/); if(m&&/indeed/.test(host))url='https://www.indeed.com/viewjob?jk='+m[1];
  var done=false;
  var payload={url:url,title:title,company:company,role:role,text:pick(),source:'bookmarklet'};
  var send=function(){
    if(!payload.company){payload.company=prompt('Company (not found on the page)','');if(payload.company===null)return;}
    if(!payload.role){payload.role=prompt('Role (not found on the page)','');if(payload.role===null)return;}
    var w=window.open(origin+'/relay','careerkit-inbox','width=560,height=360');
    if(!w){alert('The browser blocked the popup. Allow popups for this site and click again.');return;}
    var onmsg=function(e){
      if(e.origin!==origin||e.data!=='careerkit-ready')return;
      done=true; window.removeEventListener('message',onmsg);
      e.source.postMessage(payload,origin);
    };
    window.addEventListener('message',onmsg);
    setTimeout(function(){if(!done){window.removeEventListener('message',onmsg);alert('careerkit inbox did not answer. Start it with: careerkit inbox --serve');}},4000);
  };
  setTimeout(send,400);
})();
"""

# The relay page. Same origin as the receiver, so its fetch is plain. It asks
# the opener for the posting, writes it, and shows what was recorded.
RELAY_HTML = """<!doctype html><meta charset="utf-8"><title>careerkit inbox</title>
<style>body{font:15px/1.5 system-ui,sans-serif;margin:2em}code{font-size:.9em}.ok{color:#176c2f}.warn{color:#8a5a00}.err{color:#a11}</style>
<p id="s">Waiting for the posting...</p>
<script>
(function(){
  var out=document.getElementById('s');
  window.addEventListener('message',function(e){
    if(!e.data||typeof e.data!=='object'||!('text' in e.data))return;
    fetch('/capture',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(e.data)})
      .then(function(r){return r.json();})
      .then(function(j){
        if(j.error){out.className='err';out.textContent='Not saved: '+j.error;return;}
        out.className=j.written?'ok':'warn';
        out.innerHTML=(j.written?'Saved ':'Already captured: ')+'<code>'+j.file+'</code><br>'
          +'company: '+j.company+'<br>role: '+j.role+'<br>'+j.pending+' pending. This window closes in a moment.';
        setTimeout(function(){window.close();},3500);
      })
      .catch(function(){out.className='err';out.textContent='The receiver did not answer.';});
  });
  if(window.opener){window.opener.postMessage('careerkit-ready','*');}
  else{out.textContent='Open this from the Save JD button.';}
})();
</script>
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
<p>Drag this to your bookmarks bar (drag it again if you had an older one):</p>
<p><a class="bm" href="{link}">Save JD</a></p>
<p>Then open a posting on LinkedIn, Indeed, or a company site and click it. It
reads the company and role off the page, opens a small window here that saves
the posting verbatim, and closes it. It never overwrites a file it already
wrote, and it asks for the company or role only when the page does not say.</p>
<h2>Pending</h2><ul>{rows}</ul>
"""


class _Handler(BaseHTTPRequestHandler):
    inbox: Path = Path("jd-inbox")
    port: int = DEFAULT_PORT

    def _send(self, status: int, body: bytes, ctype: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/relay"):
            self._send(200, RELAY_HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        body = install_page(self.inbox, self.port).encode("utf-8")
        self._send(200, body, "text/html; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            capture = json.loads(raw.decode("utf-8"))
            path, written = write_capture(self.inbox, capture)
            payload = {
                "file": path.name, "written": written, "pending": len(pending(self.inbox)),
                "company": str(capture.get("company") or ""), "role": str(capture.get("role") or ""),
            }
            status = 200
        except (ValueError, json.JSONDecodeError) as exc:
            payload = {"error": str(exc)}
            status = 400
        self._send(status, json.dumps(payload).encode("utf-8"), "application/json")
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
