# Exabeam Plug-in Forge

The Exabeam Plug-in Forge is Exabeam's marketplace of **commercially licensed plugins for AI
agents**. Each plugin adds Exabeam's knowledge and capabilities to the agent you already run — your
choice of model, agent harness and data sovereignty — and every one of them is a stable, reviewed
build that Exabeam has pinned to an exact release. Today's plugins run in
[Claude Code](https://claude.com/claude-code) and [OpenAI Codex](https://openai.com/codex/).

The customer-facing front door, with every plugin and its skills, is the
[Forge site](https://exabeam.github.io/plugins/) (generated from this repository).
This page is the repository's own guide: what the Forge vends, how to add it, and — for maintainers,
reviewers and anyone who needs to know — what is where and how a build gets here.

Everything in this repository is governed by the
[Exabeam Enterprise Agreement](https://www.exabeam.com/legal/enterprise-agreement/) unless a file or
directory specifies otherwise — see [License](#license).

## Plugins

| Plugin | Install as | What it does | Skills | Documentation |
|---|---|---|---|---|
| **Exabeam Agentic SOC plugin** | `soc@exabeam` | An agentic SOC analyst for Exabeam New-Scale: hand it an alert or a case and it gathers the evidence, reaches a verdict and acts in the SIEM — with dismiss and close always behind your approval and containment recommended, never executed. | `soc-investigate` · `triage-cases` · `rule-tuning` | [README](soc/README.md) · [Setup guide](soc/docs/installation.md) · [License](soc/LICENSE) |

More plugins are added as rows here and as cards on the front door. A plugin's documentation ships
inside the plugin — its `README.md` and `docs/` — and is the same documentation its source
distribution carries; install with the commands on this page and the plugin key in the table.

## Add the Forge once

Add the marketplace once on either host, then install what you need. The plugin key is the same on
both hosts: `<plugin>@exabeam`.

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

Each plugin's own documentation covers what comes next — credentials, supported models, tooling,
and what it will and will not do.

> **Already have the same plugin from another marketplace?** Uninstall it first. A plugin vended
> here and its community distribution carry different plugin keys, so installing this one does not
> replace the other — you would end up with two enabled copies of the same skills and two connectors
> against the same tenant. Nothing breaks, but the tool surface doubles.

## What is where

This repository will be public by its nature, so the layout is documented here rather than assumed.

| Path | What it is |
|---|---|
| [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) | The catalog manifest both hosts read: the marketplace name (`exabeam`), and one entry per plugin — name, display name, description, source directory, license. |
| `soc/` (one directory per plugin) | The **vendored payload**: a `git archive` of the plugin's source repository at the pinned commit, byte-identical to that source apart from the declared identity and license overlays. Never edited by hand — see [Fixing something in the payload](MAINTAINERS.md#fixing-something-in-the-payload). |
| [`vendor.lock.json`](vendor.lock.json) | Provenance per entry: source repository, subdirectory, commit, version, release notes, blessing date, who blessed it, and the overlays applied. The current pins live here, not in prose. |
| `overlays/<entry>/` | The `LICENSE` and `NOTICE` served with each plugin from this marketplace — the commercial terms, by reference. |
| [`scripts/vendor_plugin.py`](scripts/vendor_plugin.py) | Blesses or re-vendors an entry: exports the source at a commit, applies the identity overlay, runs the plugin's own generator, applies the license files, writes the lock record. |
| [`scripts/validate_catalog.py`](scripts/validate_catalog.py) | The CI gate. Validates the manifest and the lock, and with `--verify-upstream` proves each vendored tree is byte-identical to a fresh export of its source at the pinned commit, modulo the declared overlays. |
| [`scripts/build_site.py`](scripts/build_site.py) | Renders the front door, [`index.html`](index.html), from the manifest, the lock, each payload's identity and its skills' metadata. `--check` fails CI if the page drifts from the catalog. |
| `index.html`, `assets/` | The generated front door and its logo, served by GitHub Pages from `main`. |
| [`.github/workflows/validate.yml`](.github/workflows/validate.yml) | Two jobs on every PR and push to `main`: `catalog` (the validator, with upstream verification) and `site` (the front door is current). |
| [`.github/CODEOWNERS`](.github/CODEOWNERS) | Review from code owners is required on the manifest, the payloads, the lock, the validator and the workflow. |
| [`MAINTAINERS.md`](MAINTAINERS.md) | How a build is blessed, the rev policy, the gate, the license overlay, what protects `main`, and the verification log. |
| [`LICENSE`](LICENSE) | The terms for this repository, and where a file or directory specifies otherwise. |

## How a build gets here

1. The plugin's source project cuts a release.
2. A maintainer runs `scripts/vendor_plugin.py`, which exports the source at that commit, re-keys it
   to this marketplace through the plugin's own identity generator, applies the commercial license
   files, and records the provenance in `vendor.lock.json`.
3. That change is a pull request. CI proves the vendored tree is byte-identical to the source at the
   pinned commit, modulo the declared overlays, and that the front door still matches the catalog.
4. A code owner reviews and it merges. From then on, two people installing a month apart get the
   same bytes, and nothing changes under them until the next blessed build lands the same way.

The rules and the payloads never change in the same pull request, and CI validates every change with
`main`'s copy of the validator, so a change cannot loosen the gate and slip a payload through it
together. The details, and the record of what was verified when, are in
[MAINTAINERS.md](MAINTAINERS.md).

## License

The plugins distributed here are **commercially licensed** under the
[Exabeam Enterprise Agreement](https://www.exabeam.com/legal/enterprise-agreement/) and are subject to
the same terms of use as the Exabeam products they work with. This repository is governed by the same
agreement unless a file or directory specifies otherwise — see [`LICENSE`](LICENSE). Each plugin carries
its own `LICENSE` and `NOTICE` in its directory.

Some plugins are built on open-source projects whose source is also available under open-source terms
through the [Open Agent and AI Security community](https://open-agent-ai-security.github.io/). Those
distributions are governed by their own licenses, not by this one.
