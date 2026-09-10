<!--
  Copyright 2026 Exabeam, Inc.
  SPDX-License-Identifier: Apache-2.0
-->

# Maintaining this catalog

How builds get blessed, how the gate works, and what protects `main`. If you are here to *install*
a plugin, you want [`README.md`](README.md) instead.

## What "blessed build" means

- **It does not move.** Two analysts installing a month apart get identical bytes. Nothing changes
  under them until Exabeam decides it should — and when it does, that is a reviewed pull request
  in this repository, not a ref moving elsewhere.
- **It is reproducible.** The payload is a `git archive` export of the source at the commit named
  in `vendor.lock.json`, plus one declared identity overlay (the plugin's name and display name on
  Codex). CI proves both on every change: `scripts/validate_catalog.py --verify-upstream`.
- **Provenance is on record.** `vendor.lock.json` names the source repository, subdirectory,
  commit, version, release, date, and who blessed it.

## Blessing a build

A vendoring PR, where the diff *is* the release review:

```bash
python3 scripts/vendor_plugin.py soc --sha <40-hex commit on the source's default branch> --blessed-by "<name>"
git diff            # the payload change, file by file
```

The script refuses a commit that is not an ancestor of the source's default branch — only code
that completed the source project's release process can be served here. It re-applies the
declared overlay, updates `vendor.lock.json`, and does not commit.

**Bless a new tree only under a new version string.** Vendoring a different commit under a version
already blessed makes that version name two different payloads, which defeats the point of a pin.
If upstream has unreleased changes you want, ask upstream to cut a release first.

## Rev policy

Two paths, decided in advance:

- *Feature builds* move at Exabeam's pace — bless a new release when it has been evaluated against
  customer use, not merely when it exists.
- *Security fixes* take the fast path: a source security release is vendored and merged the same
  day, with the security note in the PR. "Frozen" must never quietly become "stale".

## The gate

`scripts/validate_catalog.py` requires every source to be either vendored with a
`vendor.lock.json` record or an object source carrying a 40-hex `sha`; a floating ref alone is
rejected. Source repositories must be `https://github.com/<allow-listed org>/<repo>.git`, parsed
in full.

**The plugin has one name.** For a payload that ships its own identity generator
(socxen ≥ 0.8.6, `gen_identity.py`), the catalog entry, both host manifests and `identity.json` must
agree, and the payload's own `gen_identity.py --check` must pass — a rename is declared as a lock
**overlay** on `identity.json` only, which the vendor script applies after export and then runs the
generator, so both manifests, the permission snippet's `mcp__plugin_<name>_<server>__` prefix and
`identity.sh` (what the payload's installer and preflight read) all follow from that one file. The
validator re-applies the same overlay and regeneration to a fresh upstream export before its
byte-identity diff.

A hand-edited re-key — one manifest patched, the rest left upstream — shipped a
payload named `soc` on Codex and `socxen` on Claude Code whose own installer would have installed the
community plugin (#3 review); the generator path is what upstream built to make that impossible. A
payload without a generator (socxen 0.8.5) may carry only the legacy Codex-manifest patch, never one
on the Claude manifest.

## The license overlay

The community distribution of a payload is Apache-2.0. This catalog vends the same code under
Exabeam's commercial terms, so the copy served here has to say so *inside the tree* — an installed
plugin whose `LICENSE` file contradicts its manifest is worse than either alone. Two declared overlays
carry that, both re-applied by the validator before its byte-identity diff:

- **`license` in the identity overlay** — one more field patched into `identity.json`; the payload's
  generator writes it into both host manifests.
- **`overlay_files`** in the lock record — whole-file replacement of `LICENSE` and/or `NOTICE` (nothing
  else is accepted) from files kept under `overlays/<entry>/`. The replacement `LICENSE` is a short
  pointer to the agreement by URL, never a copy of its text.

Everything else in the tree stays byte-identical to upstream: the gate now proves *identical modulo the
declared identity and license*. `vendor_plugin.py` applies both on bless and on `--check`.

## Controls on `main`

Changes land by PR with a required approval; CI validates with *main's* copy of the validator, so a
PR cannot change the rules and the payload together; `.github/CODEOWNERS` covers the manifest, the
payloads, the lock, the validator and the workflow, and "Require review from Code Owners" is on.

While the repository is private and no customer has installed from it, the maintainer may merge
with admin privilege to move quickly — every such merge is still a PR with green checks, and the
rules-then-payload ordering above still applies. That allowance ends at the public flip or the first
customer install, whichever comes first; from then on every PR takes a human approval and the
required checks, with no admin bypass.

## Fixing something in the payload

You can't fix it here. The vendored tree under `soc/` must stay byte-identical to upstream at the
pinned commit (modulo the declared identity overlay) or `--verify-upstream` fails — that is the gate
working, not a bug. Payload changes go upstream to
[open-agent-ai-security/socxen](https://github.com/open-agent-ai-security/socxen) first, then arrive
here as a new blessed build.

## Verification log

| Date | What was verified |
|---|---|
| 2026-09-02 | Both vendored and sha-pinned sources install on Claude Code and Codex — **as `socxen@open-agent-ai-security`, before the 0.8.6 re-key** |
| 2026-09-08 | `soc@exabeam` 0.8.6 installs from `github.com/Exabeam/plugins` on **both hosts**, after the re-key merged (#3, `f9d357b`): Claude Code — `claude plugin list` shows `soc@exabeam 0.8.6 enabled`, the Claude manifest and `identity.sh` read `soc` / `exabeam`, the bundled hook answers *allow* for a read, *ask* for `update_alert`, *allow* for `create_case` under `mcp__plugin_soc_exabeam__`, and `preflight.sh --platform claude` reports the gate ON with no environment overrides; Codex — `codex plugin list` shows `soc@exabeam installed, enabled 0.8.6`, the Codex manifest reads `soc`, `preflight.sh --platform codex` reports the gate ON. Run in fresh, empty `CLAUDE_CONFIG_DIR` / `CODEX_HOME` directories on a maintainer's machine — clean config, not a clean machine; the dev copy installed in the real config was not in play. |
