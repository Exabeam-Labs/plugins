#!/usr/bin/env python3
# Copyright 2026 Exabeam, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Bless a build: vendor a plugin payload into this catalog at an exact upstream commit.

    python3 scripts/vendor_plugin.py socxen \
        --upstream https://github.com/open-agent-ai-security/socxen.git --path plugin --sha <40-hex>

Clones upstream (blobless, no checkout), proves the commit exists and is an ancestor of the
default branch, exports `<path>` at that commit with `git archive` (so the vendored tree is the
committed tree — no working-copy drift, no symlinks resolved), replaces ./<entry>/ with it, and
records provenance in vendor.lock.json. It does NOT commit: review the diff — that diff IS the
release review — and open a PR.

    python3 scripts/vendor_plugin.py socxen --check

re-exports at the locked sha and reports whether ./<entry>/ still matches (no files touched).
"""
import argparse
import datetime
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "vendor.lock.json"


def git(*args, cwd=None, binary=False):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=not binary or True, text=not binary)
    if r.returncode != 0:
        err = r.stderr if isinstance(r.stderr, str) else r.stderr.decode(errors="replace")
        sys.exit(f"error: git {' '.join(args)}: {err.strip()[:300]}")
    return r.stdout


def apply_overlay(root, overlay):
    """A declared, reviewable identity patch on top of the byte-identical export — today only the
    Codex manifest's `name` (Codex refuses an install whose entry name differs from it) and its
    display name. The Claude manifest is never touched: its name governs the skill/MCP namespaces
    the permission gate matches on. The validator re-applies the same overlay to a fresh upstream
    export before diffing, so 'byte-identical modulo the declared overlay' is what CI proves."""
    for rel, patch in (overlay or {}).items():
        f = root / rel
        d = json.loads(f.read_text())
        for dotted, val in patch.items():
            cur = d
            parts = dotted.split(".")
            for k in parts[:-1]:
                cur = cur.setdefault(k, {})
            cur[parts[-1]] = val
        f.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")


def export(upstream, sha, path, dest):
    tmp = Path(tempfile.mkdtemp(prefix="vendor-"))
    try:
        repo = tmp / "repo"
        git("clone", "--quiet", "--filter=blob:none", "--no-checkout", upstream, str(repo))
        default = git("symbolic-ref", "refs/remotes/origin/HEAD", cwd=repo).strip().rsplit("/", 1)[-1]
        git("cat-file", "-e", f"{sha}^{{commit}}", cwd=repo)
        r = subprocess.run(["git", "merge-base", "--is-ancestor", sha, f"origin/{default}"], cwd=repo)
        if r.returncode != 0:
            sys.exit(f"error: {sha[:12]} is not an ancestor of upstream {default!r} — only released code is blessed here")
        subject = git("show", "-s", "--format=%s", sha, cwd=repo).strip()
        date = git("show", "-s", "--format=%cs", sha, cwd=repo).strip()
        tar = subprocess.run(["git", "archive", f"{sha}:{path}"], cwd=repo, capture_output=True, check=True)
        dest.mkdir(parents=True)
        subprocess.run(["tar", "-x", "-C", str(dest)], input=tar.stdout, check=True)
        return subject, date
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("entry", help="catalog entry name; the payload lives in ./<entry>/")
    ap.add_argument("--upstream"); ap.add_argument("--path", default="plugin"); ap.add_argument("--sha")
    ap.add_argument("--blessed-by", default="")
    ap.add_argument("--check", action="store_true", help="verify ./<entry>/ matches the locked sha; change nothing")
    a = ap.parse_args()
    lock = json.loads(LOCK.read_text()) if LOCK.exists() else {}
    rec = lock.get(a.entry, {})
    upstream, path, sha = a.upstream or rec.get("upstream"), a.path or rec.get("path"), a.sha or rec.get("sha")
    if not (upstream and path and sha):
        sys.exit("error: need --upstream/--path/--sha (or an existing vendor.lock.json record)")
    if len(sha) != 40:
        sys.exit("error: --sha must be the full 40-hex commit (a short sha is not a pin)")
    target = ROOT / a.entry
    stage = Path(tempfile.mkdtemp(prefix="vendor-stage-")) / a.entry
    subject, date = export(upstream, sha, path, stage)
    overlay = rec.get("overlay") or {}
    apply_overlay(stage, overlay)
    version = json.loads((stage / ".claude-plugin" / "plugin.json").read_text())["version"]

    if a.check:
        diff = subprocess.run(["diff", "-r", "--brief", str(stage), str(target)], capture_output=True, text=True)
        shutil.rmtree(stage.parent, ignore_errors=True)
        if diff.returncode == 0:
            print(f"OK — ./{a.entry}/ is byte-identical to {upstream} {path}/ @ {sha[:12]} ({version})"
                  + (f", modulo the declared overlay on {sorted(overlay)}" if overlay else "")); return 0
        print(f"DRIFT — ./{a.entry}/ differs from upstream @ {sha[:12]}:\n" + diff.stdout); return 1

    if target.exists():
        shutil.rmtree(target)
    shutil.move(str(stage), str(target))
    shutil.rmtree(stage.parent, ignore_errors=True)
    lock[a.entry] = {
        "upstream": upstream, "path": path, "sha": sha, "version": version,
        "release": f"{subject} ({date})",
        "vendored": datetime.date.today().isoformat(),
        "blessed_by": a.blessed_by or rec.get("blessed_by", ""),
        **({"overlay": overlay} if overlay else {}),
    }
    LOCK.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n")
    print(f"vendored ./{a.entry}/ <- {upstream} {path}/ @ {sha[:12]} — version {version}\n"
          f"  release: {subject} ({date})\n"
          f"  next: review `git diff` (that diff is the release review), then open a PR.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
