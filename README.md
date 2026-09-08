# Exabeam Plugin Marketplace

Exabeam's plugin marketplace for AI coding agents — [Claude Code](https://claude.com/claude-code)
and [OpenAI Codex](https://openai.com/codex/). Every entry is a **blessed build**: a payload
Exabeam has reviewed and pinned to an exact commit. Nothing here moves until Exabeam moves it.

> **Preview.** This channel is new. Treat its entries as a supported *preview* — real, reviewed,
> reproducible — and expect the tier to be raised as a deliberate, dated act.

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

| Plugin | Shown as | What it does | Build |
|---|---|---|---|
| **`soc`** | Exabeam Agentic SOC plugin | Agentic SOC skill suite for Exabeam New-Scale. Three skills over one guarded Exabeam MCP bridge: **soc-investigate** takes an alert or case from first look to a written verdict; **triage-cases** prioritises the open queue; **rule-tuning** finds the detection rules wasting analyst attention. Containment is recommended for a human, never executed; dismiss/close is held behind the host agent's approval gate. | **0.8.5** (2026-08-30) — pinned; see [`vendor.lock.json`](vendor.lock.json) |

After installing, complete the plugin's own setup — one credentials file and, on Claude Code, one
governance-gate merge: [`soc/docs/installation.md`](soc/docs/installation.md). On Codex the gate
ships inside the package, so there is no merge step.

> The plugin's in-package documentation names its open-source distribution key in some install
> commands. On this channel the commands above are authoritative; the setup steps themselves
> (credentials, the Claude Code gate merge) apply unchanged.

## What "blessed build" means

- **It does not move.** Two analysts installing a month apart get identical bytes. Nothing changes
  under them until Exabeam decides it should — and when it does, that is a reviewed pull request
  in this repository, not a ref moving elsewhere.
- **It is reproducible.** The payload is a `git archive` export of the source at the commit named
  in `vendor.lock.json`, plus one declared identity overlay (the plugin's name and display name on
  Codex). CI proves both on every change: `scripts/validate_catalog.py --verify-upstream`.
- **Provenance is on record.** `vendor.lock.json` names the source repository, subdirectory,
  commit, version, release, date, and who blessed it.

## For maintainers

**Blessing a build** is a vendoring PR, and the diff *is* the release review:

```bash
python3 scripts/vendor_plugin.py soc --sha <40-hex commit on the source's default branch> --blessed-by "<name>"
git diff            # the payload change, file by file
```

The script refuses a commit that is not an ancestor of the source's default branch — only code
that completed the source project's release process can be served here. It re-applies the
declared overlay, updates `vendor.lock.json`, and does not commit.

**Rev policy.** Two paths, decided in advance:
- *Feature builds* move at Exabeam's pace — bless a new release when it has been evaluated against
  customer use, not merely when it exists.
- *Security fixes* take the fast path: a source security release is vendored and merged the same
  day, with the security note in the PR. "Frozen" must never quietly become "stale".

**The gate.** `scripts/validate_catalog.py` requires every source to be either vendored with a
`vendor.lock.json` record or an object source carrying a 40-hex `sha`; a floating ref alone is
rejected. Source repositories must be `https://github.com/<allow-listed org>/<repo>.git`, parsed
in full. **The plugin has one name.** For a payload that ships its own identity generator
(socxen ≥ 0.8.6, `gen_identity.py`), the catalog entry, both host manifests and `identity.json` must
agree, and the payload's own `gen_identity.py --check` must pass — a rename is declared as a lock
**overlay** on `identity.json` only, which the vendor script applies after export and then runs the
generator, so both manifests, the permission snippet's `mcp__plugin_<name>_<server>__` prefix and
`identity.sh` (what the payload's installer and preflight read) all follow from that one file. The
validator re-applies the same overlay and regeneration to a fresh upstream export before its
byte-identity diff. A hand-edited re-key — one manifest patched, the rest left upstream — shipped a
payload named `soc` on Codex and `socxen` on Claude Code whose own installer would have installed the
community plugin (#3 review); the generator path is what upstream built to make that impossible. A
payload without a generator (socxen 0.8.5) may carry only the legacy Codex-manifest patch, never one
on the Claude manifest. Both vendored and sha-pinned sources were verified to install on both hosts
(2026-09-02).

**Controls on `main`.** Changes land by PR with a required approval; CI validates with *main's*
copy of the validator, so a PR cannot change the rules and the payload together;
`.github/CODEOWNERS` covers the manifest, the payloads, the lock, the validator and the workflow,
and "Require review from Code Owners" is on.

## Open-source upstream

The `soc` payload is the Apache-2.0 open-source project **socxen**
([open-agent-ai-security/socxen](https://github.com/open-agent-ai-security/socxen)), which the
community catalog `open-agent-ai-security/plugins` publishes as `socxen@open-agent-ai-security`,
following that project's `main`. This channel serves the same code at a pinned, reviewed commit
under Exabeam's name — Fedora and RHEL, for the agent era. Because both entries carry the same
payload, whose Claude-side identity is `socxen`, install from **one** catalog: with both installed,
both show as enabled but only one copy of the skills and one MCP server survive, and the client
will not say which.

## License

The catalog is [Apache-2.0](LICENSE). Each vendored plugin carries its own license in its
directory (`soc/LICENSE`, Apache-2.0).
