# Contributing to TunaOS

Thanks for wanting to contribute! TunaOS is a set of organizations-spanning
repositories that build bootable, immutable Linux desktop images from a matrix
of base OS × desktop × kernel × drivers, plus installer and migration tooling.

<!-- hive-contribute-plea: donated-compute appeal, keep in sync across repos -->
## Contribute compute — no code needed

**[Donate time with your AI CLI](https://hub.tunaos.org/#contribute).**

Your machine runs one task at a time using your signed-in AI coding CLI.
The relay alternates between eligible **School** (OS) and **Reef** (apps)
hives after each task. If one hive has no work, the other can continue.

The guide covers prerequisites, verified `just` setup, credentials, provider
costs, and how to stop with Ctrl+C. Your subscription quota or API charges apply.
Never post account credentials or API keys in issues or pull requests.

## Where things live

| Area | Repos |
|---|---|
| Image build factory | `tuna-os/tunaOS`, `tuna-os/tunaos-packages`, `tuna-os/tromso` |
| Installers | `tuna-os/bootc-installer`, `tuna-os/tuna-installer-{cosmic,kde,niri,xfce}` |
| Migration | `tuna-os/wootc`, `tuna-os/bootc-migrate` |
| Apps | `tuna-os/gtk-office-suite` (Letters, Tables, Decks), `tuna-os/Tavern` |
| Docs | `tuna-os/docs` (index lives in `docs/static/flatpak/index/static`) |

For the complete, authoritative inventory of active repositories, their default
branches, and which already have a `ROADMAP.md`, see [`ROADMAP-INDEX.md`](ROADMAP-INDEX.md)
before picking a repo. Several `tuna-os` repos do **not** default to `main` — that
document lists each repo's real default branch. This table lags, because new
repositories are added regularly; [`ROADMAP-INDEX.md`](ROADMAP-INDEX.md) is kept current.

## Getting started

1. **Pick a repository and open an issue first** — describe the change and
   why before writing code. Small fixes (typos, docs) can skip this.
2. **Fork the repo** (or ask a maintainer for push access) and create a
   branch off the repository's actual default branch — not an assumed `main`.
   We use the `arch/`, `fix/`, `feat/`, `chore/` prefix convention.
3. **Check the repo's `AGENTS.md` / `justfile`** — most repos standardize
   build/test/lint behind `just` recipes (`just build`, `just test`, `just fix`).
4. **Sign your commits** — every commit must be DCO-signed-off
   (`git commit -s`). This certifies you wrote the change and can license it.

## Working on this repository

For `tuna-os/.github` itself, use a Linux environment with Git, Bash, Python
3.11+, and Node.js 24 (for `ste-lint`). Install `actionlint` and `shellcheck`
with your package manager; use the GitHub CLI (`gh`) to inspect failed runs
and open PRs. Run checks from the repository root; there is no root `justfile`.

```bash
actionlint .github/workflows/*.yml
python3 scripts/check-renovate-automerge-policy.py renovate.json
python3 scripts/check-workflow-permissions.py .github/workflows
python3 scripts/test-renovate-automerge-policy.py
node .github/actions/ste-lint/ste-lint.test.mjs
```

For a changed shell script, run `bash -n path/to/script.sh` and
`shellcheck path/to/script.sh`. `actionlint` checks workflows, not composite
`action.yml` files: copy a changed Bash `run: |` body to a temporary `.sh` file
(without YAML indentation), replace GitHub expressions with test values, and
run the same checks. Supply inputs as environment variables, including empty,
space-containing, and quoted values. Run the action's underlying script tests
where available; static checks alone do not exercise GitHub's runner context.

- **New reusable workflow:** declare `workflow_call` and explicit permissions,
  run `actionlint`, then test a caller against your fork's branch as described
  in [Testing changes before merge](docs/WORKFLOWS.md#testing-changes-before-merge).
- **Action input change:** check existing callers and defaults, test both
  omitted and explicit inputs, and exercise a caller against the changed
  action ref. See the [action reference](.github/actions/ACTIONS.md). Keep
  shell inputs in `env:`, rather than interpolating them into script text.
- **Shared PR template:** preview `.github/PULL_REQUEST_TEMPLATE.md` as
  Markdown and check links and checkboxes before opening the PR.

For other script checks, see [docs/SCRIPTS.md](docs/SCRIPTS.md). Read
[AGENTS.md](AGENTS.md) before editing shared defaults: templates are inherited
across the org, and workflow/action callers using `@main` receive changes on
merge.

## PR checklist

- [ ] Commit messages are signed off (`git commit -s`)
- [ ] `just fix` passes (format + lint) where the repo defines it
- [ ] Tests pass (`just test` or the relevant CI workflow)
- [ ] No secrets or machine-specific paths are committed
- [ ] Docs/changelog updated if behavior changed

## Architecture expectations

- **This is an image factory, not a distro.** Changes that alter built images
  must show evidence (build + boot + smoke test) in the PR.
- **One source of truth per artifact.** Before adding a new copy of a script,
  workflow, or spec, check whether a canonical version exists (e.g. the flatpak
  publish tooling, `update-index.py`). Prefer reusing it over copying.
- **Deliberate duplication is flagged.** Some frontends intentionally
  reimplement a shared contract per language (see
  `tuna-os/docs/docs/bootc-installer-asahi/UNIFIED-INSTALL-CONTRACT.md` —
  the `recipe.json` contract shared by the installer frontends). Match the
  contract; don't fork it.
- **Agents file `[architect]`/`[sec-check]`/`[strategist]` issues.** These are
  structural findings — treat them as prioritized backlog, not noise.

## Shared scripts and their canonical sources

Several utilities ship byte-identical copies across the organisation. Each has
one canonical location where a fix must land first, plus copies regenerated
from it.

| Utility | Canonical source | Copied to | Drift enforced |
|---|---|---|---|
| `check-renovate-automerge-policy.py` | `tuna-os/.github/scripts/` | `project-starter/scripts/` (shipped to new repos) | No — byte-identical today, but nothing enforces it |
| `check-workflow-permissions.py` | `tuna-os/.github/scripts/` | `project-starter/scripts/` (shipped to new repos) | No — byte-identical today, but nothing enforces it |
| `update-index.py` | `tuna-os/flatpak-index/scripts/` | `.github/actions/update-flatpak-index/` here; `.github/scripts/` in the flatpak-publishing app repos | Yes — weekly `flatpak-tooling-drift-check.yml` |

**Keeping copies in sync.** Fix `check-renovate-automerge-policy.py` and
`check-workflow-permissions.py` in `tuna-os/.github/scripts/`, then re-copy both
into `project-starter/scripts/` in the same commit so new repos start from the
corrected version. There is no automated gate — verify the two blobs are
byte-identical whenever you touch either. Fix `update-index.py` first in
`tuna-os/flatpak-index/scripts/` (the canonical source), update the synced copy
in `tuna-os/.github/.github/actions/update-flatpak-index/` to match, and get app
repos off their own copies by migrating them onto the reusable
`publish-flatpak.yml` workflow (or the `publish-flatpak-index` action) rather
than re-copying the script; the weekly drift check flags any repo that still
carries a divergent local copy.

**Verification cadence.** `update-index.py` is checked continuously by
`flatpak-tooling-drift-check.yml` (scheduled Mondays 06:00 UTC, and on
`workflow_dispatch`), which opens or comments on an issue whenever a repo has
drifted. The `check-*` scripts have no drift check today; add a byte-comparison
 in CI if you want the project-starter copy enforced rather than trusted.

## CI/CD security

Every workflow in a TunaOS repository must declare an explicit top-level
`permissions:` block, following the principle of least privilege:

```yaml
permissions:
  contents: read
```

A workflow with no block inherits the repository's configured default token
scope, which is almost always broader than the jobs actually need. This is the
baseline called for by
[tuna-os/.github#155](https://github.com/tuna-os/.github/issues/155).

- **New repos** inherit it for free: `project-starter/` ships a `ci.yml` with
  the block and a `workflow-permissions` job that runs the check.
- **Existing repos** should adopt it with the shared tooling from
  `tuna-os/.github`: copy `workflow-templates/ci.yml` (a compliant starting
  point) and run the check — `python3 scripts/check-workflow-permissions.py
  .github/workflows`. The script and a ready-to-run workflow ship there and are
  copied in.

## Getting help

- Ask in the relevant issue or PR.
- See the [architecture guide](https://github.com/tuna-os/docs/blob/main/docs/architecture.md) in `tuna-os/docs` — architecture overview, per-repository map, and the image/ISO build-pipeline reference.
- For reusable composite actions available to org workflows, see [`.github/actions/ACTIONS.md`](.github/actions/ACTIONS.md).
- For validation scripts and policy checks, see [`docs/SCRIPTS.md`](docs/SCRIPTS.md).
- For security issues, use the private channel described in `SECURITY.md` —
  never paste secrets or exploit details into a public issue.
