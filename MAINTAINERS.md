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

## Controls on `main`

Changes land by PR with a required approval; CI validates with *main's* copy of the validator, so a
PR cannot change the rules and the payload together; `.github/CODEOWNERS` covers the manifest, the
payloads, the lock, the validator and the workflow, and "Require review from Code Owners" is on.

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
| _pending_ | `soc@exabeam` installs on both hosts (the key this catalog now publishes — re-verify before the repo goes public) |
