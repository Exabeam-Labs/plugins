# Exabeam Plugin Marketplace

Exabeam's plugin marketplace for AI coding agents — [Claude Code](https://claude.com/claude-code)
and [OpenAI Codex](https://openai.com/codex/). Every entry is a **blessed build**: a payload
Exabeam has reviewed and pinned to an exact upstream commit. Nothing here moves until Exabeam
moves it.

> **Preview.** This channel is new and its first entry ships software that upstream still
> labels pre-release. Treat it as a supported *preview* — real, reviewed, reproducible — and
> expect the tier to be raised as a deliberate, dated act.

## Install

Add the marketplace once, then install what you need. Same commands, same plugin keys, on
either host.

**Claude Code**
```bash
claude plugin marketplace add Exabeam/plugins
claude plugin install soc@exabeam
```

**OpenAI Codex**
```bash
codex plugin marketplace add Exabeam/plugins
codex plugin add soc@exabeam
```

| Plugin | Shown as | What it does | Build | Upstream |
|---|---|---|---|---|
| **`soc`** | Exabeam Agentic SOC plugin | Agentic SOC skill suite for Exabeam New-Scale: investigates and triages alerts and cases end to end through the Exabeam MCP, sweeps the open queue, finds noisy detection rules. Containment is recommended for a human; dismiss/close is held behind the host agent's approval gate. | socxen **0.8.5** — see [`vendor.lock.json`](vendor.lock.json) for the exact commit | [open-agent-ai-security/socxen](https://github.com/open-agent-ai-security/socxen) |

After installing, follow the plugin's own setup guide — for the SOC plugin that is one
credentials file and (on Claude Code) one governance-gate merge:
[`soc/docs/installation.md`](soc/docs/installation.md).

## How this relates to the community catalog

The same skill is also published by the open-source community catalog,
[`open-agent-ai-security/plugins`](https://github.com/open-agent-ai-security/plugins), as
`socxen@open-agent-ai-security`. The two are the same code on two promises — Fedora and RHEL,
for the agent era:

| | `socxen@open-agent-ai-security` | `soc@exabeam` |
|---|---|---|
| Points at | upstream `main` — whatever is current when you install | an exact commit, vendored into this repo |
| Moves | every upstream release | only when Exabeam blesses a new build |
| For | contributors, researchers, evaluators | Exabeam customers and field teams |

**Byte-identical payloads.** The vendored tree under [`soc/`](soc/) is a
`git archive` export of upstream's `plugin/` directory at the commit named in
`vendor.lock.json` — no fork, no patches, nothing to drift — plus the one declared identity
overlay described below. CI proves this on every change
(`scripts/validate_catalog.py --verify-upstream`), and so can you:

```bash
python3 scripts/vendor_plugin.py soc --check
```

**`soc@exabeam` is the same payload as `socxen@open-agent-ai-security`, re-labelled.** Codex
requires an entry's name to equal the payload's `.codex-plugin/plugin.json` name, so the vendored
copy carries a declared **overlay** (see `vendor.lock.json`): that one manifest's `name` is `soc`
and its display name is *Exabeam Agentic SOC plugin*. Nothing else differs from upstream, and the
Claude manifest is never touched — its name (`socxen`) governs the skill and MCP namespaces
(`socxen:soc-investigate`, `plugin:socxen:exabeam`) and the permission rules that gate
dismiss/close. CI proves "byte-identical modulo the declared overlay".

**Known wart.** The payload's own docs and diagnostics (`soc/docs/installation.md`, `install.sh`,
`preflight.sh`) still name the community key, `socxen@open-agent-ai-security`, in their install
commands — they are upstream's files, unmodified. This README is authoritative for install
commands on this channel; the in-payload setup steps (credentials, the Claude Code gate merge)
apply unchanged.

**One socxen at a time.** Both entries deliver the same payload, whose Claude-side identity is `socxen`. If you
install from *both* catalogs, both show as enabled but only one copy of the skill and one MCP
server survive, and the client will not tell you which. Pick a channel. To switch, uninstall
the other entry first.

## For maintainers

**Blessing a build** is a vendoring PR, and the diff *is* the release review:

```bash
python3 scripts/vendor_plugin.py soc \
  --upstream https://github.com/open-agent-ai-security/socxen.git --path plugin \
  --sha <40-hex commit on upstream main> --blessed-by "<your name>"
git diff            # the payload change, file by file
```

The script refuses a commit that is not an ancestor of upstream's default branch — only code
that completed the upstream release process can be served here. It updates
`vendor.lock.json` (upstream, path, sha, version, release, date, who) and does not commit.

**Rev policy.** Two paths, decided in advance:
- *Feature builds* move at Exabeam's pace — bless a new upstream release when it has been
  evaluated against customer use, not merely when it exists.
- *Security fixes* take the fast path: an upstream security release is vendored and merged the
  same day, with the security note in the PR. "Frozen" must never quietly become "stale".

**Vendored or pinned.** Vendoring (the default, above) makes every payload change a reviewable
diff in this repo. The alternative — an object source carrying a 40-hex `sha` — is also accepted,
and both hosts honour it: a `git-subdir` entry pinned to socxen's 0.8.0 release commit installed
0.8.0 on Claude Code and on Codex while upstream `main` was at 0.8.5 (verified 2026-09-02; Codex
lists the sha it installed). Use it for a plugin whose payload you would rather point at than copy.

**The gate.** `scripts/validate_catalog.py` inverts the community validator's central rule:
upstream *requires* a floating `ref: main`; this catalog *rejects* anything unpinned. Sources are
either vendored with a `vendor.lock.json` record or an object source carrying a 40-hex `sha`
(a `ref` may accompany it for context; the sha is what installs). Upstream repos must be
`https://github.com/<allow-listed org>/<repo>.git`, parsed in full. Entry names must equal the
payload's Codex manifest name (Codex enforces it; Claude Code merely tolerates a mismatch) — a
rename is declared as a lock overlay, never applied to the Claude manifest — and are *not*
required to match the upstream repo name.

**Controls on `main`.** Changes land by PR with a required approval; CI validates with *main's*
copy of the validator; `.github/CODEOWNERS` covers the manifest, the payloads, the lock, the
validator and the workflow, and **"Require review from Code Owners"** is on — that, not the
workflow, is what stops a PR from editing the gate that grades it.

## License

The catalog is [Apache-2.0](LICENSE). Each vendored plugin carries its own license in its
directory (the SOC plugin: Apache-2.0, `soc/LICENSE`).
