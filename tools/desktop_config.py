"""Register careerkit with Claude Desktop, with the app CLOSED.

    python tools/desktop_config.py --corpus <dir> --runs <dir> [--remove NAME ...]

Claude Desktop keeps its own copy of the MCP server list and writes it over
claude_desktop_config.json when it quits. An edit made while the app is
running is lost at the next quit, which is how two careful edits vanished in
an afternoon. So: quit the app completely (the tray icon too), run this,
start the app. The file is backed up beside itself first.

What it cannot see: whether the app is actually closed. It warns if a
claude.exe is running and carries on, because you may know better.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def config_path() -> Path:
    if sys.platform == "win32":
        return Path(os.environ["APPDATA"]) / "Claude" / "claude_desktop_config.json"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def app_running() -> bool:
    if sys.platform != "win32":
        return False
    out = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
    return "claude.exe" in out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--corpus", required=True, help="CAREERKIT_CORPUS directory")
    ap.add_argument("--runs", required=True, help="CAREERKIT_RUNS directory")
    ap.add_argument("--python", default=None, help="interpreter with careerkit installed "
                    "(default: this repo's .venv, else the running one)")
    ap.add_argument("--remove", nargs="*", default=[], metavar="NAME",
                    help="server entries to drop, e.g. a dead one that shadows this")
    ap.add_argument("--config", default=None, help="config file (default: the platform's)")
    args = ap.parse_args(argv)

    path = Path(args.config) if args.config else config_path()
    venv = ROOT / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    python = args.python or (str(venv) if venv.exists() else sys.executable)

    if app_running():
        print("warning: claude.exe is running. The app rewrites this file when it quits, "
              "so this edit may not survive. Quit it fully first.", file=sys.stderr)

    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    backup = path.with_name(path.name + ".bak-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    if path.exists():
        shutil.copy(path, backup)
    servers = data.setdefault("mcpServers", {})
    for name in args.remove:
        if servers.pop(name, None) is not None:
            print(f"removed {name}")
    servers["careerkit"] = {
        "command": python.replace("\\", "/"),
        "args": ["-m", "careerkit.cli", "mcp"],
        "env": {
            "CAREERKIT_CORPUS": str(Path(args.corpus).resolve()).replace("\\", "/"),
            "CAREERKIT_RUNS": str(Path(args.runs).resolve()).replace("\\", "/"),
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path}")
    print(f"servers: {', '.join(servers) or 'none'}")
    if path.exists() and backup.exists():
        print(f"backup: {backup.name}")
    print("Now start Claude Desktop. In a new chat, the careerkit tools should be listed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
