#!/usr/bin/env python3
# Copyright 2026 Exabeam, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Generate the Exabeam Plug-in Forge front door (index.html) from the data the catalog already holds.

    python3 scripts/build_site.py            # (re)write index.html
    python3 scripts/build_site.py --check    # exit 1 if index.html differs from what the sources produce (CI)

Sources, nothing hand-written per plugin:
  .claude-plugin/marketplace.json     the entries: name, displayName, description, category, keywords
  vendor.lock.json                    the blessed build per entry: version, sha, release, date, who blessed it
  <entry>/identity.json               the payload's own identity: shortDescription, hostKeywords, license
  <entry>/skills/*/SKILL.md           each skill's frontmatter: name + description (the invocation phrases are
                                      the quoted "…" fragments the description lists)
  <entry>/README.md                   detected only, for the "documentation" link

The page is Exabeam-branded per https://www.exabeam.com/newsroom/styleguide/ (green #009D00 / blue #006BFF,
black and white grounds, Lausanne with Helvetica Neue fallback, the one-colour white logo on black) and is
served from `main` by GitHub Pages once the repository is public. Adding a plugin adds a card.
"""
import base64
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "index.html"
CATALOG = ROOT / ".claude-plugin" / "marketplace.json"
LOCK = ROOT / "vendor.lock.json"
LOGO = ROOT / "assets" / "exabeam-logo-white.svg"
TERMS_URL = "https://www.exabeam.com/legal/enterprise-agreement/"
COMMUNITY_URL = "https://open-agent-ai-security.github.io/"
REPO_URL = "https://github.com/Exabeam/plugins"

HOST_LABELS = {"claude": "Claude Code", "codex": "OpenAI Codex"}


def frontmatter(text):
    m = re.match(r"---\r?\n(.*?)\r?\n---", text, re.S)
    if not m:
        return {}
    fm, out, key, buf = m.group(1), {}, None, []
    for line in fm.splitlines():
        km = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if km and not line.startswith(" "):
            if key:
                out[key] = " ".join(x.strip() for x in buf).strip()
            key, first = km.group(1), km.group(2).strip()
            buf = [] if first in (">-", ">", "|", "|-") else [first]
        elif key is not None:
            buf.append(line)
    if key:
        out[key] = " ".join(x.strip() for x in buf).strip()
    return out


def first_sentence(text):
    m = re.match(r"(.+?[.!?])(\s|$)", text)
    return (m.group(1) if m else text).strip()


def invocations(description, limit=3):
    """The quoted phrases a skill's description lists as ways to ask for it."""
    seen, out = set(), []
    for q in re.findall(r'"([^"]{4,60})"', description):
        q = q.strip()
        if q.lower() not in seen:
            seen.add(q.lower()); out.append(q)
        if len(out) >= limit:
            break
    return out


def load():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    lock = json.loads(LOCK.read_text(encoding="utf-8")) if LOCK.exists() else {}
    entries = []
    for e in catalog["plugins"]:
        name = e["name"]
        src = e.get("source")
        pdir = ROOT / src[2:] if isinstance(src, str) and src.startswith("./") else None
        ident = json.loads((pdir / "identity.json").read_text(encoding="utf-8")) if pdir and (pdir / "identity.json").exists() else {}
        skills = []
        if pdir and (pdir / "skills").is_dir():
            for sk in sorted((pdir / "skills").glob("*/SKILL.md")):
                fm = frontmatter(sk.read_text(encoding="utf-8"))
                desc = fm.get("description", "")
                skills.append({"name": fm.get("name") or sk.parent.name, "summary": first_sentence(desc), "ask": invocations(desc)})
        hosts = []
        if pdir:
            if (pdir / ".claude-plugin" / "plugin.json").exists(): hosts.append("claude")
            if (pdir / ".codex-plugin" / "plugin.json").exists(): hosts.append("codex")
        # Order the skills the way the entry's own description introduces them; alphabetical for the rest.
        desc = e.get("description", "")
        def by_mention(s):                      # skills in the order the entry description names them
            i = desc.find(s["name"])
            return (i if i >= 0 else 10**6, s["name"])
        skills.sort(key=by_mention)
        rec = lock.get(name, {})
        entries.append({
            "name": name, "display": e.get("displayName") or name, "description": e.get("description", ""),
            "category": e.get("category", ""), "license": e.get("license", ""), "short": ident.get("shortDescription", ""),
            "version": rec.get("version") or ident.get("version", ""), "sha": (rec.get("sha") or "")[:7],
            "blessed": rec.get("vendored", ""), "blessed_by": rec.get("blessed_by", ""), "release": rec.get("release", ""),
            "upstream": rec.get("upstream", ""), "hosts": hosts, "skills": skills,
            "docs": f"{name}/README.md" if pdir and (pdir / "README.md").exists() else "",
            "setup": f"{name}/docs/installation.md" if pdir and (pdir / "docs" / "installation.md").exists() else "",
        })
    return catalog, entries


def logo_uri():
    return "data:image/svg+xml;base64," + base64.b64encode(LOGO.read_bytes()).decode()


CSS = """
:root{--green:#009D00;--green-l:#4CDB00;--green-d:#106D00;--blue:#006BFF;--blue-l:#27B2FF;--blue-d:#003FCC;
--ink:#111418;--mut:#5f6774;--line:#e1e5ea;--soft:#f5f7f9;}
*{box-sizing:border-box}html,body{margin:0;padding:0;background:#fff;color:var(--ink);
font:16px/1.55 "Lausanne","Helvetica Neue",Helvetica,Arial,sans-serif}
a{color:var(--blue-d)}a:hover{color:var(--blue)}
code,pre{font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace}
code{font-size:.92em;background:var(--soft);padding:.1em .35em;border-radius:4px}
pre{background:#0b0f14;color:#e8edf3;padding:14px 16px;border-radius:8px;overflow-x:auto;font-size:14px;line-height:1.5;margin:0}
pre .c{color:#8b98a8}
.wrap{max-width:1080px;margin:0 auto;padding:0 24px}
header{background:#000;color:#fff}
header .wrap{display:flex;align-items:center;justify-content:space-between;height:64px}
header img{height:26px;display:block}
header nav a{color:#fff;opacity:.85;text-decoration:none;margin-left:22px;font-size:15px}
header nav a:hover{opacity:1}
.hero{padding:56px 0 36px;border-bottom:1px solid var(--line)}
.kicker{font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:var(--green-d);font-weight:700;margin-bottom:10px}
h1{font-size:44px;line-height:1.1;margin:0 0 14px;font-weight:800;letter-spacing:-.02em}
.lead{font-size:20px;color:#2b3138;max-width:820px;margin:0 0 22px}
.hosts{display:flex;gap:10px;flex-wrap:wrap}
.pill{display:inline-block;font-size:13px;font-weight:700;padding:5px 12px;border-radius:999px;border:1px solid var(--line);background:#fff;color:var(--mut)}
.pill.g{color:var(--green-d);border-color:#bfe8bf;background:#eefbee}.pill.b{color:var(--blue-d);border-color:#bfd9ff;background:#eaf3ff}
h2{font-size:26px;margin:44px 0 16px;font-weight:800;letter-spacing:-.01em}
.grid{display:grid;grid-template-columns:1fr;gap:20px}
.card{border:1px solid var(--line);border-radius:12px;padding:26px 28px;background:#fff}
.card .top{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap}
.card h3{font-size:24px;margin:0 0 4px;font-weight:800}
.card .short{font-size:17px;color:#2b3138;margin:0 0 12px}
.card .desc{margin:12px 0 18px}
.skills{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;margin:8px 0 18px}
.skill{background:var(--soft);border-radius:10px;padding:14px 16px}
.skill b{display:block;font-size:15px;margin-bottom:4px}
.skill .ask{font-size:13.5px;color:var(--mut);font-style:italic;margin-bottom:6px}
.skill p{margin:0;font-size:14.5px}
.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:760px){.two{grid-template-columns:1fr}}
.install h4{margin:0 0 8px;font-size:14px;letter-spacing:.06em;text-transform:uppercase;color:var(--mut)}
.links{margin-top:16px;font-size:15px}
.links a{margin-right:18px}
.card.soon{border:2px dashed #c9d0d8;background:var(--soft);text-align:center;padding:30px 28px}
.card.soon h3{font-size:20px;margin:0 0 6px}.card.soon p{margin:0 auto;max-width:620px;color:#2b3138}
.terms{background:var(--soft);border-radius:12px;padding:22px 26px;margin-top:8px}
footer{margin-top:56px;padding:26px 0 40px;border-top:1px solid var(--line);font-size:14px;color:var(--mut)}
"""


def render(catalog, entries):
    h = html.escape
    parts = []
    parts.append(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Exabeam Plug-in Forge</title>
<meta name="description" content="{h(catalog.get('metadata', {}).get('description', ''))}">
<style>{CSS}</style>
</head>
<body>
<header><div class="wrap">
  <a href="./" aria-label="Exabeam"><img src="{logo_uri()}" alt="Exabeam"></a>
  <nav><a href="#install">Install</a><a href="#plugins">Plugins</a><a href="#terms">Terms</a><a href="{REPO_URL}">GitHub</a></nav>
</div></header>

<section class="hero"><div class="wrap">
  <div class="kicker">Exabeam Plug-in Forge</div>
  <h1>Exabeam plugins for AI agents.</h1>
  <p class="lead">Add Exabeam's knowledge and capabilities to the AI agent of your choice, on your terms. Bring your own AI — your choice of model, agent harness and data sovereignty — and put Exabeam's products to work inside it.</p>
  <div class="hosts"><span class="pill g">Stable, reviewed plug-ins</span><span class="pill">Governed by the Exabeam Enterprise Agreement</span></div>
</div></section>

<main class="wrap">
<h2 id="install" style="margin-top:36px">Add the Plug-in Forge once</h2>
<p>Add it once on either host, then install what you need. The plugin key is the same on both hosts: <code>&lt;plugin&gt;@{h(catalog['name'])}</code>.</p>
<div class="two">
  <div class="install"><h4>Claude Code</h4><pre>claude plugin marketplace add Exabeam/plugins</pre></div>
  <div class="install"><h4>OpenAI Codex</h4><pre>codex plugin marketplace add Exabeam/plugins</pre></div>
</div>

<h2 id="plugins">Plugins</h2>
<div class="grid">""")
    for e in entries:
        hosts = "".join(f'<span class="pill">{h(HOST_LABELS.get(x, x))}</span>' for x in e["hosts"])
        skills = ""
        for s in e["skills"]:
            ask = " · ".join(f"“{h(a)}”" for a in s["ask"])
            skills += f'<div class="skill"><b><code>{h(s["name"])}</code></b>' + (f'<div class="ask">{ask}</div>' if ask else "") + f'<p>{h(s["summary"])}</p></div>'
        links = []
        if e["docs"]: links.append(f'<a href="{REPO_URL}/blob/main/{h(e["docs"])}">Documentation</a>')
        if e["setup"]: links.append(f'<a href="{REPO_URL}/blob/main/{h(e["setup"])}">Setup guide</a>')
        links.append(f'<a href="{REPO_URL}/blob/main/{h(e["name"])}/LICENSE">License</a>')
        parts.append(f"""
<article class="card" id="{h(e['name'])}">
  <div class="top">
    <div><h3>{h(e['display'])}</h3><p class="short">{h(e['short'] or e['description'])}</p></div>
    <div class="hosts">{hosts}<span class="pill b">{h(e['category'].title() if e['category'] else 'Plugin')}</span></div>
  </div>
  <p class="desc">{h(e['description'])}</p>
  <div class="skills">{skills}</div>
  <div class="two">
    <div class="install"><h4>Claude Code</h4><pre>claude plugin marketplace add Exabeam/plugins   <span class="c"># once</span>
claude plugin install {h(e['name'])}@{h(catalog['name'])}</pre></div>
    <div class="install"><h4>OpenAI Codex</h4><pre>codex plugin marketplace add Exabeam/plugins    <span class="c"># once</span>
codex plugin add {h(e['name'])}@{h(catalog['name'])}</pre></div>
  </div>
  <div class="links">{' '.join(links)}</div>
</article>""")
    parts.append(f"""
<article class="card soon" id="coming-soon">
  <h3>More plugins coming soon</h3>
  <p>The Agentic SOC plugin is the first of a family. More Exabeam plugins for third-party agent frameworks will land here as stable, reviewed plug-ins under the same terms — <a href="{REPO_URL}">watch the repository</a> to see them arrive.</p>
</article>
</div>

<h2 id="terms">Terms and licensing</h2>
<div class="terms">
  <p>The plugins distributed here are <b>distributed under</b> the <a href="{TERMS_URL}">Exabeam Enterprise Agreement</a> and are subject to the same terms of use as the Exabeam products they work with. This marketplace is governed by the same agreement unless specified otherwise; each plugin carries its own <code>LICENSE</code> and <code>NOTICE</code>.</p>
  <p style="margin-bottom:0">A plugin may include open-source software. That software stays under its own license inside the distribution, its license text ships with the plugin, and the plugin's <code>LICENSE</code> names what it includes and where the source is also available (for the plugins here, through the <a href="{COMMUNITY_URL}">Open Agent and AI Security community</a>). The Enterprise Agreement governs the distribution; it adds nothing to, and takes nothing from, what the open-source license grants on the software.</p>
</div>
</main>

<footer><div class="wrap">© 2026 Exabeam, Inc. · <a href="{REPO_URL}">Exabeam/plugins on GitHub</a> · Every entry is a stable, reviewed build with provenance in <a href="{REPO_URL}/blob/main/vendor.lock.json">vendor.lock.json</a>. Generated from the catalog by <code>scripts/build_site.py</code>.</div></footer>
</body>
</html>
""")
    return "".join(parts)


def main(argv):
    catalog, entries = load()
    page = render(catalog, entries)
    if "--check" in argv:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != page:
            print("index.html is STALE — regenerate with: python3 scripts/build_site.py"); return 1
        print("index.html is current with the catalog sources"); return 0
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:   # the same bytes on every platform
        f.write(page)
    print(f"wrote {OUT.relative_to(ROOT)} — {len(entries)} plugin(s): " + ", ".join(e["name"] for e in entries))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
