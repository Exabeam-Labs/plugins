#!/usr/bin/env python3
# Copyright 2026 Exabeam, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Gate .claude-plugin/marketplace.json — Exabeam's commercial plugin catalog.

Adapted from the community catalog's validator (open-agent-ai-security/plugins) with its central
rule INVERTED: upstream requires a floating `ref: main` (each product repo's release channel);
this catalog is the blessed-build channel, so nothing here may move on its own.

  - A plugin is served one of two ways, both immutable:
      * VENDORED — `"source": "./<dir>"`, the plugin's payload copied into THIS repo at a named
        upstream commit, so every payload change is a reviewable diff here and the installed tree
        is byte-for-byte what was reviewed. Provenance lives in vendor.lock.json (upstream URL,
        subdirectory, 40-hex sha, version), and `--verify-upstream` proves the vendored tree
        equals upstream at that sha and that the sha is an ancestor of upstream's default branch —
        i.e. it completed the upstream release process.
      * PINNED — an object source ('url' or 'git-subdir') that carries a 40-hex `sha`. A floating
        ref alone is rejected. `ref` may accompany `sha` (branch/tag context, as the official
        Anthropic catalog does), but `sha` is what installs.
  - Upstream repositories must be https://github.com/<org>/<repo>.git for an allow-listed org,
    parsed and matched in full (never prefix-matched).
  - An entry's name MUST equal the payload's `.codex-plugin/plugin.json` `name`: OpenAI Codex
    refuses the install otherwise ("plugin.json name `socxen` does not match marketplace plugin
    name `soc-analyst`" — verified 2026-09-02). Claude Code tolerates a mismatch and namespaces
    by `.claude-plugin/plugin.json`'s name, which is what the permission gate matches on — so
    that manifest is never renamed. The bridge between the two is a declared OVERLAY in
    vendor.lock.json: a per-file field patch (today: the Codex manifest's name and display name)
    that the vendor script applies after export and `--verify-upstream` re-applies to a fresh
    upstream export before the byte-identity diff. Anything not declared there is drift.
  - No entry-level version metadata; the payload's plugin.json is the version authority, and
    vendor.lock.json must agree with it.

Stdlib only. `--verify-upstream` needs git and network; CI runs it, local runs may skip it.
Exit 0 clean, 1 with findings (always a findings list, never a traceback).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(os.environ.get("CATALOG_ROOT") or Path(__file__).resolve().parents[1]).resolve()
MANIFEST = ROOT / ".claude-plugin" / "marketplace.json"
LOCK = ROOT / "vendor.lock.json"

MARKETPLACE_NAME = "exabeam"
ALLOWED_ORGS = {"open-agent-ai-security", "exabeam"}          # compared lowercase
REPO_PATH_RE = re.compile(r"^/([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+)\.git$")
PLUGIN_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SUBDIR_RE = re.compile(r"^[A-Za-z0-9._-]+(/[A-Za-z0-9._-]+)*$")
ALLOWED_SOURCE_KEYS_BY_TYPE = {
    "url": {"source", "url", "sha", "ref"},
    "git-subdir": {"source", "url", "sha", "ref", "path"},
}


def _clean_path(label, what, value, problems):
    """Relative, traversal-free directory path. Returns True if acceptable."""
    if not isinstance(value, str) or not value:
        problems.append(f"{label}: {what} must be a non-empty string, got {value!r}")
        return False
    if any(c.isspace() or ord(c) < 0x20 for c in value) or "\\" in value:
        problems.append(f"{label}: {what} contains whitespace, control characters or backslashes: {value!r}")
        return False
    if not SUBDIR_RE.match(value) or any(seg in (".", "..") for seg in value.split("/")):
        problems.append(f"{label}: {what} must be [A-Za-z0-9._-] segments, no '.'/'..' (traversal), got {value!r}")
        return False
    return True


def _check_upstream_url(label, url, problems):
    """https://github.com/<allow-listed org>/<repo>.git, parsed in full. Returns (org, repo) or None."""
    if not isinstance(url, str) or not url:
        problems.append(f"{label}: upstream url must be a non-empty string, got {url!r}")
        return None
    if any(c.isspace() or ord(c) < 0x20 for c in url):
        problems.append(f"{label}: upstream url contains whitespace or control characters: {url!r}")
        return None
    p = urlsplit(url)
    ok = True
    if p.scheme != "https":
        problems.append(f"{label}: upstream url must use https, got {p.scheme!r}"); ok = False
    if p.netloc != "github.com":
        problems.append(f"{label}: upstream url host must be exactly 'github.com', got {p.netloc!r}"); ok = False
    if p.query or p.fragment:
        problems.append(f"{label}: upstream url must have no query string or fragment"); ok = False
    m = REPO_PATH_RE.match(p.path)
    if not m:
        problems.append(f"{label}: upstream url path must be '/<org>/<repo>.git', got {p.path!r}"); return None
    if m.group(1).lower() not in ALLOWED_ORGS:
        problems.append(f"{label}: upstream org {m.group(1)!r} is not allow-listed ({sorted(ALLOWED_ORGS)})"); ok = False
    return (m.group(1), m.group(2)) if ok else None


def check_vendored(label, src, name, lock, problems):
    """A payload copied into this repo. Returns the lock record (for --verify-upstream) or None."""
    if not src.startswith("./"):
        problems.append(f"{label}: a string source must be './<dir>' (a vendored plugin directory), got {src!r}")
        return None
    rel = src[2:]
    if not _clean_path(label, "vendored source path", rel, problems):
        return None
    d = ROOT / rel
    if not d.is_dir():
        problems.append(f"{label}: vendored directory {src!r} does not exist"); return None
    if d.is_symlink() or not d.resolve().is_relative_to(ROOT):
        problems.append(f"{label}: vendored directory {src!r} is a symlink or escapes the repo root"); return None
    links = sorted(str(p.relative_to(ROOT)) for p in d.rglob("*") if p.is_symlink())
    if links:
        problems.append(f"{label}: vendored payload contains symlink(s) ({', '.join(links[:3])}) — reviewed tree must equal installed tree")
        return None
    try:
        pj = json.loads((d / ".claude-plugin" / "plugin.json").read_text())
    except FileNotFoundError:
        problems.append(f"{label}: vendored plugin is missing .claude-plugin/plugin.json"); return None
    except Exception as e:
        problems.append(f"{label}: vendored plugin.json does not parse: {e}"); return None
    version = pj.get("version") if isinstance(pj, dict) else None
    if not (isinstance(version, str) and version.strip()):
        problems.append(f"{label}: vendored plugin.json must declare a non-empty version"); return None
    codex = d / ".codex-plugin" / "plugin.json"
    codex_name = None
    if codex.exists():
        try:
            codex_name = json.loads(codex.read_text()).get("name")
        except Exception:
            pass
    generator = (d / "gen_identity.py").is_file()
    if generator:
        # A self-regenerating payload (socxen >= 0.8.6): ONE name everywhere. Claude Code namespaces the
        # skills and the bundled MCP by the Claude manifest's name (which the permission gate matches on),
        # Codex refuses an install whose entry name differs from its manifest, and identity.sh is what the
        # payload's own installer reads — so entry, both manifests and identity.json must agree, or the
        # operator ends up with a different plugin than the catalog named (Exabeam/plugins#3 review).
        try:
            ident_name = json.loads((d / "identity.json").read_text()).get("name")
        except Exception as e:
            problems.append(f"{label}: the payload ships gen_identity.py but identity.json is unreadable ({e})"); return None
        names = {"catalog entry": name, ".claude-plugin/plugin.json": pj.get("name"), "identity.json": ident_name}
        if codex.exists():                       # a host manifest that is absent is not a name that disagrees
            names[".codex-plugin/plugin.json"] = codex_name
        if len({v for v in names.values()}) != 1:
            problems.append(f"{label}: the plugin must have ONE name — " + ", ".join(f"{k}={v!r}" for k, v in names.items())
                            + " — re-key through identity.json + gen_identity.py, never by hand")
            return None
        r = subprocess.run([sys.executable, "gen_identity.py", "--check"], cwd=d, capture_output=True, text=True)
        if r.returncode != 0:
            problems.append(f"{label}: the payload's own gen_identity.py --check fails: {(r.stdout or r.stderr).strip()[:200]}")
            return None
    elif name and (codex_name or pj.get("name")) != name:
        problems.append(f"{label}: entry name {name!r} != payload's Codex manifest name {codex_name or pj.get('name')!r} — "
                        f"Codex refuses the install on a mismatch; declare the rename as a vendor.lock overlay")
        return None
    codex = d / ".codex-plugin" / "plugin.json"
    if codex.exists():
        try:
            cv = json.loads(codex.read_text()).get("version")
            if cv != version:
                problems.append(f"{label}: .codex-plugin/plugin.json version {cv!r} != .claude-plugin version {version!r}")
        except Exception as e:
            problems.append(f"{label}: vendored .codex-plugin/plugin.json does not parse: {e}")
    rec = lock.get(name) if isinstance(lock, dict) else None
    if not isinstance(rec, dict):
        problems.append(f"{label}: no vendor.lock.json record for {name!r} — a vendored payload must state where it came from")
        return None
    if _check_upstream_url(label, rec.get("upstream"), problems) is None:
        return None
    if not _clean_path(label, "vendor.lock path", rec.get("path"), problems):
        return None
    sha = rec.get("sha")
    if not (isinstance(sha, str) and SHA_RE.match(sha)):
        problems.append(f"{label}: vendor.lock sha must be a 40-hex commit, got {sha!r}"); return None
    if rec.get("version") != version:
        problems.append(f"{label}: vendor.lock version {rec.get('version')!r} != vendored plugin.json version {version!r}")
    overlay = rec.get("overlay") or {}
    if not isinstance(overlay, dict) or any(not isinstance(v, dict) or not _clean_path(label, "overlay file", k, [])
                                            for k, v in overlay.items()):
        problems.append(f"{label}: overlay must map payload-relative JSON files to {{dotted.field: value}} patches, got {overlay!r}")
        return None
    if generator and set(overlay) - {"identity.json"}:
        problems.append(f"{label}: this payload regenerates its identity — the overlay may patch identity.json only "
                        f"(the manifests, the permission snippet and identity.sh are derived from it), got {sorted(overlay)}")
        return None
    if not generator and any(".claude-plugin/" in k for k in overlay):
        problems.append(f"{label}: overlay must never patch the Claude manifest (its name governs the namespaces the "
                        f"permission gate matches on), got {sorted(overlay)}")
        return None
    # The license files: whole-file replacements or additions, LICENSE / NOTICE / LICENSE-APACHE only,
    # sourced from this repository. The payload's own license stays as upstream ships it; the
    # distribution terms and the Apache-2.0 text travel beside it (Exabeam/plugins#28).
    files = rec.get("overlay_files") or {}
    if not isinstance(files, dict) or any(not isinstance(v, str) for v in files.values()):
        problems.append(f"{label}: overlay_files must map a payload file name to a catalog-relative source path, got {files!r}")
        return None
    home = (ROOT / "overlays" / name).resolve()
    for rel, src in files.items():
        if rel not in FILE_OVERLAY_ALLOWED:
            problems.append(f"{label}: overlay_files may replace only {FILE_OVERLAY_ALLOWED}, got {rel!r}"); return None
        if not _clean_path(label, "overlay_files source", src, problems):
            return None                                        # _clean_path already said why
        if not src.startswith(f"overlays/{name}/"):
            problems.append(f"{label}: overlay_files source must live under overlays/{name}/, got {src!r}"); return None
        p = ROOT / src
        if not p.is_file() or p.is_symlink() or not p.resolve().is_relative_to(home):
            problems.append(f"{label}: overlay_files source {src!r} must be a regular file under overlays/{name}/ "
                            f"(missing, a symlink, or resolving outside it)"); return None
    return {"dir": d, **rec}


def check_pinned(label, src, problems):
    """An object source pinned to a commit. Returns {'url','sha'} or None."""
    stype = src.get("source")
    if stype not in ALLOWED_SOURCE_KEYS_BY_TYPE:
        problems.append(f"{label}: source.source must be 'url' or 'git-subdir', got {stype!r}"); return None
    extra = sorted(set(src) - ALLOWED_SOURCE_KEYS_BY_TYPE[stype])
    if extra:
        problems.append(f"{label}: unexpected source key(s) {extra} for {stype!r}")
    if stype == "git-subdir" and not _clean_path(label, "source.path", src.get("path"), problems):
        return None
    if _check_upstream_url(label, src.get("url"), problems) is None:
        return None
    sha = src.get("sha")
    if not (isinstance(sha, str) and SHA_RE.match(sha)):
        problems.append(f"{label}: source.sha must be a 40-hex commit — this catalog serves blessed builds only; "
                        f"a floating ref (got sha={sha!r}, ref={src.get('ref')!r}) is not one")
        return None
    ref = src.get("ref")
    if ref is not None and (not isinstance(ref, str) or not ref or any(c.isspace() for c in ref)):
        problems.append(f"{label}: source.ref, if present, must be a non-empty branch/tag string, got {ref!r}")
    return {"url": src["url"], "sha": sha}


# ---------- network verification ----------

def _git(*args, cwd=None):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip()[:300])
    return r.stdout


FILE_OVERLAY_ALLOWED = ("LICENSE", "NOTICE", "LICENSE-APACHE", "LICENSE.md", "NOTICE.md")


def _apply_file_overlays(root, files):
    for rel, src in (files or {}).items():
        (root / rel).write_bytes((ROOT / src).read_bytes())


def _apply_overlay(root, overlay):
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


def verify_upstream(label, url, sha, vendored_dir, path, problems, overlay=None, overlay_files=None):
    """Prove: sha exists upstream, is an ancestor of upstream's default branch, and (if vendored)
    the vendored tree is byte-identical to upstream's `path` at sha. Fails closed on any error."""
    tmp = Path(tempfile.mkdtemp(prefix="catalog-verify-"))
    try:
        repo = tmp / "repo"
        _git("clone", "--quiet", "--filter=blob:none", "--no-checkout", url, str(repo))
        head = _git("symbolic-ref", "refs/remotes/origin/HEAD", cwd=repo).strip()   # refs/remotes/origin/<default>
        default = head.rsplit("/", 1)[-1]
        try:
            _git("cat-file", "-e", f"{sha}^{{commit}}", cwd=repo)
        except RuntimeError:
            problems.append(f"{label}: commit {sha[:12]} does not exist in {url}"); return
        try:
            _git("merge-base", "--is-ancestor", sha, f"origin/{default}", cwd=repo)
        except RuntimeError:
            problems.append(f"{label}: commit {sha[:12]} is NOT an ancestor of upstream {default!r} — "
                            f"only code that completed the upstream release process may be served here")
            return
        if vendored_dir is None:
            return
        export = tmp / "export"; export.mkdir()
        tar = subprocess.run(["git", "archive", f"{sha}:{path}"], cwd=repo, capture_output=True)
        if tar.returncode != 0:
            problems.append(f"{label}: cannot export {path!r} at {sha[:12]}: {tar.stderr.decode(errors='replace')[:200]}"); return
        subprocess.run(["tar", "-x", "-C", str(export)], input=tar.stdout, check=True)
        _apply_overlay(export, overlay)   # the declared identity patch; everything else must match exactly
        if (export / "gen_identity.py").is_file():          # ...after the payload's own generator has run on it
            r = subprocess.run([sys.executable, "gen_identity.py"], cwd=export, capture_output=True, text=True)
            if r.returncode != 0:
                problems.append(f"{label}: gen_identity.py failed on the upstream export after the overlay: {(r.stderr or r.stdout).strip()[:200]}"); return
        _apply_file_overlays(export, overlay_files)   # the declared license files, last
        diff = subprocess.run(["diff", "-r", "--brief", str(export), str(vendored_dir)], capture_output=True, text=True)
        if diff.returncode != 0:
            lines = [ln for ln in diff.stdout.splitlines() if ln.strip()][:6]
            problems.append(f"{label}: vendored tree differs from upstream {path!r} @ {sha[:12]}: " + " | ".join(lines))
    except Exception as e:  # noqa: BLE001 — a verification that can't run must not pass
        problems.append(f"{label}: upstream verification failed to run ({e}) — refusing to pass unverified")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv) -> int:
    verify = "--verify-upstream" in argv
    problems = []
    try:
        m = json.loads(MANIFEST.read_text())
    except FileNotFoundError:
        print(f"{MANIFEST} not found", file=sys.stderr); return 1
    except Exception as e:
        print(f"marketplace.json does not parse: {e}", file=sys.stderr); return 1
    if not isinstance(m, dict):
        print("marketplace.json must be a JSON object", file=sys.stderr); return 1
    lock = {}
    if LOCK.exists():
        try:
            lock = json.loads(LOCK.read_text())
        except Exception as e:
            problems.append(f"vendor.lock.json does not parse: {e}")

    if m.get("name") != MARKETPLACE_NAME:
        problems.append(f"marketplace name must be {MARKETPLACE_NAME!r}, got {m.get('name')!r}")
    owner = m.get("owner")
    if not isinstance(owner, dict):
        problems.append(f"owner must be an object, got {type(owner).__name__}")
    else:
        for k in ("name", "url"):
            if not isinstance(owner.get(k), str) or not owner[k].strip():
                problems.append(f"owner.{k} must be a non-empty string, got {owner.get(k)!r}")
    plugins = m.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        problems.append("plugins must be a non-empty list"); plugins = []

    seen, to_verify = set(), []
    for i, e in enumerate(plugins):
        label = f"plugins[{i}]"
        if not isinstance(e, dict):
            problems.append(f"{label}: not an object"); continue
        name = e.get("name"); label = f"plugins[{i}] ({name!r})"
        if not isinstance(name, str) or not PLUGIN_NAME_RE.match(name):
            problems.append(f"{label}: name must match {PLUGIN_NAME_RE.pattern}"); name = None
        elif name in seen:
            problems.append(f"{label}: duplicate name — a duplicate silently shadows the other entry")
        else:
            seen.add(name)
        if "displayName" in e and (not isinstance(e["displayName"], str) or not e["displayName"].strip()):
            problems.append(f"{label}: displayName, if present, must be a non-empty string")
        if not isinstance(e.get("description"), str) or not e["description"].strip():
            problems.append(f"{label}: description must be a non-empty string")
        if "version" in e:
            problems.append(f"{label}: carries a version — the payload's plugin.json is the version authority")
        src = e.get("source")
        if isinstance(src, str):
            rec = check_vendored(label, src, name, lock, problems)
            if rec:
                to_verify.append((label, rec["upstream"], rec["sha"], rec["dir"], rec["path"], rec.get("overlay"), rec.get("overlay_files")))
        elif isinstance(src, dict):
            rec = check_pinned(label, src, problems)
            if rec:
                to_verify.append((label, rec["url"], rec["sha"], None, None, None, None))
        else:
            problems.append(f"{label}: source must be a './<dir>' string (vendored) or an object (pinned), got {type(src).__name__}")

    if isinstance(lock, dict):
        for k in lock:
            if k not in seen:
                problems.append(f"vendor.lock.json: record {k!r} has no catalog entry — stale lock")

    if verify and not problems:
        for label, url, sha, vdir, vpath, overlay, overlay_files in to_verify:
            verify_upstream(label, url, sha, vdir, vpath, problems, overlay, overlay_files)

    if problems:
        print("catalog manifest problems:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"catalog manifest OK — {len(plugins)} plugin(s), every source vendored-with-provenance or sha-pinned"
          + (", upstream verified (commit exists, is an ancestor of the default branch, vendored tree byte-identical modulo the declared identity overlay + the payload's own regeneration + the declared license files)"
             if verify else " (structural only; add --verify-upstream to check against upstream)"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
