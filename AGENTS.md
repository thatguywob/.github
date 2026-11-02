# AGENTS.md — agent guide for tuna-os/.github

The **org defaults repo**. Nothing here builds a product; everything here
applies to other repositories.

## How changes propagate

Four different mechanisms, with different blast radii:

| Path | Reaches |
|---|---|
| `.github/ISSUE_TEMPLATE/`, `PULL_REQUEST_TEMPLATE.md`, `DISCUSSION_TEMPLATE/`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md` | Every org repo that does not ship its own copy — immediately, with no merge in that repo |
| `profile/README.md` | The organisation's public landing page |
| `.github/workflows/*.yml` with `on: workflow_call`, and `.github/actions/*` | Cross-repository callers pin a complete commit SHA and adopt changes through reviewed pin updates; legacy `@main` callers still receive merges immediately |
| `project-starter/` | A template **copied** into new repos; not used by this repo |

Cross-repository workflow and action references must use complete commit SHAs
(#285/#288/#335; migration tracker #152), with Renovate keeping pins current.
The existing `--self-repo` checker exception applies only to references into
the repository being checked, not to every first-party repository. It remains
unchanged. A pinned workflow can still contain mutable nested references;
pinning its caller alone does not make the entire execution graph immutable.

Some existing callers still track `@main` until migrated, so a merge can affect
them immediately. SHA-pinned callers receive the workflow revision when their
pin update lands and can roll it back by restoring a reviewed prior SHA.
`publish-flatpak.yml`'s inputs and each action's `inputs:` block remain public
APIs: check callers before renaming an input or changing what a default means.

## Don't put an input back into a script body

`update-flatpak-index/action.yml` routes every input through `env:` rather
than `${{ }}` interpolation, and that is load-bearing. **Actions substitutes
expressions into the script TEXT before bash parses it**, so an interpolated
value is parsed as shell. Quoting narrows it and does not close it — a value
containing a double quote ends the quoted region — and `--tags` was unquoted
outright, deliberately, so word-splitting would spread a multi-tag list into
argparse's `nargs="+"`.

Demonstrated against the rendered script: `tags: latest; touch /tmp/PWNED` ran
the `touch`, created the file, and still **exited 0**, so the step looked
clean. As an env var the value is data, and `read -ra` does the splitting the
multi-tag case actually needs. No caller was exploitable — the only one passes
a literal `latest` — but this action is the migration target for eight repos
whose jobs hold `packages: write` and `FLATPAK_INDEX_TOKEN`.

## The drift check, and what it does not cover

[`flatpak-tooling-drift-check.yml`](.github/workflows/flatpak-tooling-drift-check.yml)
is an interim guard for
[tuna-os/tunaOS#1183](https://github.com/tuna-os/tunaOS/issues/1183). Its canonical
source is `tuna-os/flatpak-index/scripts/update-index.py`. The action copy here,
`.github/actions/update-flatpak-index/update-index.py`, must match it byte for
byte; the workflow checks that link before classifying application repos.

### Current status

As verified on 2026-11-02, the workflow is **manually disabled**
(`disabled_manually`); the Monday 06:00 UTC schedule in YAML is not running.
The [last scheduled run, 2026-10-12](https://github.com/tuna-os/.github/actions/runs/38267777559),
failed with two drifted repos: `blueshell` and `docs`. The other six configured
repos were migrated. Both canonical and action copies currently have blob
`564262b2473e41a049593852c7a5cee0df23d3d3`.

Re-enable the workflow once the two remaining migrations land:
[tuna-os/blueshell#85](https://github.com/tuna-os/blueshell/issues/85) and
[tuna-os/docs#448](https://github.com/tuna-os/docs/issues/448). Track migration
progress in [#271](https://github.com/tuna-os/.github/issues/271); this dated
snapshot documents the status requested in
[#292](https://github.com/tuna-os/.github/issues/292).

### Coverage and limits

The configured repo list is `Tavern bootc-installer blueshell docs dualcut
finupdate gtk-office-suite mandelbrot`. For each repo's default branch, the
workflow compares `.github/scripts/update-index.py` with canonical. Without a
local copy, it looks for a workflow using the shared `publish-flatpak.yml`,
`publish-flatpak-index`, or `update-flatpak-index` tooling before calling the
repo migrated. A missing copy alone is an error, as is a divergent copy.

`flatpak-index/scripts/update-index.py` is checked as the canonical source,
and `docs` and `Tavern` are in the application list. Coverage is limited to
that explicit list and the `.github/scripts/update-index.py` path; the check
does not discover copies elsewhere (for example `scripts/update-index.py`
in an app repo) or new publishers automatically. Add new flatpak publishers
to `REPOS` when they adopt the remote.

### Remediation

Migrate app repos to the reusable `publish-flatpak.yml` workflow or the shared
`publish-flatpak-index` / `update-flatpak-index` composite actions, then delete
their vendored script. Manually copying the canonical script into each app
leaves the duplication in place. If a local change is needed, port it to
`tuna-os/flatpak-index/scripts/update-index.py` first and sync the action copy
here byte for byte.

## Default branches are not all `main`

`ROADMAP-INDEX.md` is the org-wide inventory, and it exists because the
TunaOS ROADMAP drifted against a guess. The lesson is written into it:
**`bootc-installer`, `fisherman`, `changelog-action`, `kde-build-meta` and
`mariner` default to something other than `main`.** Hardcoding `main` is how a
roadmap got stranded on the wrong branch while `dev` stayed unplanned. Resolve
the default branch per repo rather than assuming.

## Checks

```bash
python3 scripts/check-renovate-automerge-policy.py renovate.json
```

`renovate-policy-check.yml` enforces [#12](https://github.com/tuna-os/.github/issues/12)
against this repo's own `renovate.json`: a syntactically valid config can still
automerge major and minor updates once `packageRules` are layered
(tuna-os/tunaOS#1612, tuna-os/tunaOS#1636), which a schema validator alone would not catch.

`scripts/check-renovate-automerge-policy.py` and
`project-starter/scripts/check-renovate-automerge-policy.py` are byte-identical
copies. `scripts/test-renovate-automerge-policy.py` asserts that, so a
divergence fails the `Policy checker self-test` step rather than going
unnoticed.

**But the gate does not fire for the copy that drifts.**
`renovate-policy-check.yml` triggers on a `paths:` filter that lists
`scripts/check-renovate-automerge-policy.py` and does **not** list
`project-starter/scripts/check-renovate-automerge-policy.py`. Editing the
canonical copy runs the sync check; editing the starter copy matches no path,
so the workflow never runs and the assertion never executes. The starter copy
is the one that matters most — `project-starter/` is copied verbatim into
scaffolded repos, which never run this workflow — and it is the one the filter
omits. See [#189](https://github.com/tuna-os/.github/issues/189) for the exact
line to add.

For the reusable workflows these checks operate on — what each input does, its
defaults, and how a repo calls one — see [`docs/WORKFLOWS.md`](docs/WORKFLOWS.md).
For the reusable composite actions hosted in `.github/actions/`, see
[`.github/actions/ACTIONS.md`](.github/actions/ACTIONS.md).
For the validation scripts enforcing these policies — purpose, usage, exit codes, and project-starter sync — see [`docs/SCRIPTS.md`](docs/SCRIPTS.md).

## Workflow permissions check

```bash
python3 scripts/check-workflow-permissions.py .github/workflows
```

`workflow-permissions-check.yml` enforces [tuna-os/.github#155](https://github.com/tuna-os/.github/issues/155): every workflow must declare a top-level `permissions:` block. A workflow with none inherits the repository's configured default token scope, which is almost always broader than the jobs actually need. The check is dependency-free — it parses only top-level mapping keys and their indentation, so it runs on the ubuntu runner without a `pip install`.

`scripts/check-workflow-permissions.py` and `project-starter/scripts/check-workflow-permissions.py` are byte-identical copies today; copy the script into any repo that ships its own copy, the way the renovate check does.

`publish-flatpak.yml` and `ste-lint.yml` were the two workflows that lacked the block; `publish-flatpak.yml` takes `contents: write` (checkout + `gh release upload`) and `packages: write` (GHCR push + index update), `ste-lint.yml` takes `contents: read`.

## `.claude/skills/hive-contribute/`

A skill that works the hive's ready-work queue **without registering a relay**,
because every route under `/api/contribute` is an unconditional public path in
the hive's own `isPublicPath`. It holds no task lease, so it does soft
deconfliction only — treat a race as possible on every run. It lives here so
any agent with this org checked out picks it up.
