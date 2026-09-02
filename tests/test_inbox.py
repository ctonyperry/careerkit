"""careerkit inbox: one click on a posting, one verbatim file in jd-inbox."""

from __future__ import annotations

import datetime as dt
import json
import threading
import urllib.request
from http.server import HTTPServer
from pathlib import Path

import pytest

from careerkit.inbox import _Handler, bookmarklet, install_page, pending, slug, write_capture

TODAY = dt.date(2026, 9, 2)


def test_capture_is_written_verbatim_with_the_pipeline_frontmatter(tmp_path: Path) -> None:
    text = ("Solutions Engineer\n\nWhat you will do\n"
            "- Own the technical relationship: from day one.\n")
    path, written = write_capture(tmp_path, {
        "company": "Halcyon Robotics", "role": "Solutions Engineer",
        "url": "https://example.com/jobs/1", "text": text,
    }, today=TODAY)
    assert written and path.name == "2026-09-02-halcyon-robotics-solutions-engineer.md"
    body = path.read_text(encoding="utf-8")
    head, rest = body.split("---\n\n", 1)
    assert "company: Halcyon Robotics" in head
    assert "status: pending" in head
    assert "url: https://example.com/jobs/1" in head  # a colon: quoted, still one line
    assert rest == text  # nothing reordered, nothing summarised


def test_capture_never_overwrites(tmp_path: Path) -> None:
    cap = {"company": "A", "role": "B", "text": "first"}
    p1, w1 = write_capture(tmp_path, cap, today=TODAY)
    p2, w2 = write_capture(tmp_path, {**cap, "text": "second"}, today=TODAY)
    assert w1 and not w2 and p1 == p2
    assert "first" in p1.read_text(encoding="utf-8")


def test_empty_page_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        write_capture(tmp_path, {"company": "A", "role": "B", "text": "  "}, today=TODAY)


def test_pending_lists_only_pending(tmp_path: Path) -> None:
    write_capture(tmp_path, {"company": "A", "role": "SE", "text": "x"}, today=TODAY)
    p, _ = write_capture(tmp_path, {"company": "B", "role": "TA", "text": "y"}, today=TODAY)
    p.write_text(p.read_text(encoding="utf-8").replace("status: pending", "status: drafted"),
                 encoding="utf-8")
    assert [c for _, c, _ in pending(tmp_path)] == ["A"]


def test_slug_is_filename_safe() -> None:
    assert slug("Sr. Solutions Engineer (Pre-Sales) / West") == (
        "sr-solutions-engineer-pre-sales-west")
    assert slug("   ") == "untitled"


def test_bookmarklet_is_one_line_and_names_the_port() -> None:
    bm = bookmarklet(9999)
    assert bm.startswith("javascript:(function(){")
    assert "\n" not in bm
    assert "127.0.0.1:'+port+'/capture" in bm and "var port=9999" in bm


def test_receiver_round_trip(tmp_path: Path) -> None:
    handler = type("H", (_Handler,), {"inbox": tmp_path, "port": 0})
    server = HTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        body = json.dumps({"company": "Halcyon", "role": "SE", "url": "u", "text": "the posting"})
        req = urllib.request.Request(f"http://127.0.0.1:{port}/capture", data=body.encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req) as resp:
            assert resp.headers["Access-Control-Allow-Origin"] == "*"
            payload = json.loads(resp.read())
        assert payload["written"] is True and payload["pending"] == 1
        assert (tmp_path / payload["file"]).exists()
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as resp:
            page = resp.read().decode()
        assert "Save JD" in page and payload["file"] in page
    finally:
        server.shutdown()
        server.server_close()


def test_install_page_escapes_the_bookmarklet() -> None:
    page = install_page(Path("nowhere"), 8765)
    assert 'href="javascript:' in page and "&quot;" in page
