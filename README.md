# Exabeam Plugin Marketplace

Exabeam's plugin channel for AI coding agents — [Claude Code](https://claude.com/claude-code) and
[OpenAI Codex](https://openai.com/codex/).

One plugin today: **an agentic SOC assistant for Exabeam New-Scale.** It works your alerts and cases
through the Exabeam MCP — gathering evidence, reaching a verdict, and writing it up — with the
consequential actions held behind your explicit approval.

## The three skills

| Skill | Whose work it is | What it does |
|---|---|---|
| **`soc-investigate`** | the analyst | One alert or case, first look to written verdict: gathers evidence, pivots on entities, weighs competing hypotheses, maps to MITRE ATT&CK, reaches a threat / false-positive verdict, and acts. |
| **`triage-cases`** | the shift lead | The open queue rather than one case: clusters by attack shape, ranks by corroborated signal (risk score is one input, not the answer), returns a "start here" list plus the noise worth tuning. Read-only across the sweep — never closes in bulk. |
| **`rule-tuning`** | the detection engineer | Finds rules that are *noisy*, not merely loud (volume × low precision), and proposes the specific change mapped to real Exabeam mechanics — context table, exclusion rule, filter/scope/maturity. Propose-only. |

Each hands off to the others: a single case to `soc-investigate`, a noise cluster to `rule-tuning`.

## Install

Add the marketplace once, then install the plugin. Same commands and same plugin key on either host.

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

> **Use the commands above, not the ones in the plugin's in-package guides.** Those guides carry the
> install, update and uninstall commands for the plugin's upstream distribution, under a different
> marketplace and a different plugin key. On this channel the key is `soc@exabeam`. Everything else
> in those guides — credentials, the gate, troubleshooting — applies unchanged.

> **Already have this plugin from another marketplace?** Uninstall it first. The two carry different
> plugin keys, so installing this one does not replace it — you would get two enabled plugins, two
> copies of all three skills, and two Exabeam MCP servers each minting its own token against the
> same tenant. Nothing breaks, but your tool surface doubles and every permission rule has to be
> written twice.

## Then set it up

Two one-time steps, both covered by **[the setup guide](soc/docs/installation.md)**:

1. **Connect Exabeam** — put your New-Scale API key and secret in `~/.exabeam-mcp.env`. The bridge
   mints and refreshes the OAuth token itself, so you never handle an expiring token.
2. **Optionally merge the permission pack** — a second lock, independent of the shipped gate. Nothing
   merges by default; `install.sh --merge-permissions`, run from the installed plugin's directory, will do it for you.

On Claude Code the safety gate is a hook that is **active the moment the plugin is enabled** — there
is nothing you must merge to be safe. On Codex the same tiers ship inside the package as
tool-approval policy, so there is no merge step at all.

## Using it

Ask for the job, and the host agent routes to the right skill:

```
investigate alert <id>
triage the queue
find noisy rules
```

## What it will and won't do

- **Containment is never executed.** Host isolation, account disable, IP blocks and the rest are
  *recommended* for you to perform in EDR/IAM. The gate denies them outright — and that denial holds
  even under `--dangerously-skip-permissions`.
- **Dismiss and close always ask.** Closing an alert or case, and sending mail, require an explicit
  human yes every time — and are refused outright when no human is present (headless runs included).
- **Reads and escalation run freely.** Evidence gathering, opening a case and writing case notes need
  no prompt, so a fresh install is useful immediately without weakening anything.
- **Detection content is read-only.** `rule-tuning` proposes; the MCP's rule-write tools are denied on
  both hosts. Detection engineering applies the change.
- **It treats your telemetry as hostile.** Log data is attacker-influenced by construction, so hidden
  character smuggling is stripped from what it reads, and active content (formulas, clickable links)
  plus credentials and structured identifiers are neutralized in anything it writes back.
- **It keeps a local audit trail.** Every gate decision — including refused attempts — and every time
  a guardrail fired is recorded under `~/.socxen/`, on by default, bounded, and local: no network
  egress.

## Requirements

- **A host agent** — the `claude` or `codex` CLI.
- **A supported model.** On Claude Code, **Sonnet 4.6+ or Opus**; smaller models such as Haiku are
  **not supported** for this skill, which reasons over attacker-influenced log data. The full tier
  table is in the [prerequisites](soc/docs/installation.md#prerequisites).
- **An Exabeam New-Scale API key + secret** (OAuth client-credentials). The MCP inherits the key's
  access level, so scope it to what you want the agent to reach.
- **[`uv`](https://docs.astral.sh/uv/)** — runs the connector; it installs its own Python
  dependencies, so there is nothing to `pip install`.

> **On Codex,** the plugin's adversarial-input gate has passed at the floor tier (GPT-5.6 Terra at
> medium reasoning effort), and the safety gate is enforced on both hosts. The skills' *routing*
> evaluations have not yet been run against an OpenAI model. Prefer Claude Code where you have the
> choice.

## Provenance

Every entry is a **blessed build**: a payload Exabeam has reviewed and pinned to an exact commit.
Two analysts installing a month apart get identical bytes, and nothing changes under them until
Exabeam moves it — which happens as a reviewed pull request here, not a ref moving elsewhere. CI
proves on every change that the vendored tree is byte-identical to its reviewed source at the pinned
commit.

[`vendor.lock.json`](vendor.lock.json) names the source repository, subdirectory, commit, version,
release date and who blessed it. Current build: **0.8.6**, pinned at `4cc6a1c`, blessed 2026-09-08.

Maintainers: see **[MAINTAINERS.md](MAINTAINERS.md)** for how builds get blessed, the rev policy,
and what protects `main`.

## License

**Apache-2.0, Copyright 2026 Exabeam, Inc.** — both this catalog ([`LICENSE`](LICENSE)) and the
plugin it serves ([`soc/LICENSE`](soc/LICENSE), [`soc/NOTICE`](soc/NOTICE)). The plugin is
Exabeam's own open-source project, developed in the open and served here at a pinned commit — not
third-party code redistributed under Exabeam's name. Contributions to it are accepted under the
same license with a required DCO sign-off.

The connector's Python dependencies are resolved and fetched by [`uv`](https://docs.astral.sh/uv/)
on the machine that runs it; they are not redistributed by this repository. The exact pinned set is
in [`soc/connector/exabeam-mcp-bridge.py.lock`](soc/connector/exabeam-mcp-bridge.py.lock).
