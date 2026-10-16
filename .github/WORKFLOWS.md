# Reusable Workflows — Integration Guide

This repository maintains a set of reusable GitHub Actions workflows that implement Hive practices across the TunaOS organization. These workflows are available to every repo via `workflow_call` and enforce consistency around CI contract, permissions, linting, and contributor engagement.

## Quick Reference

| Workflow | Purpose | Use when | Epic/Issue |
|----------|---------|----------|-----------|
| **ste-lint** | Simplified Technical English prose linting | Every PR touches docs or README | [#2250](https://github.com/tuna-os/tunaOS/issues/2250), [.github#142](https://github.com/tuna-os/.github/issues/142) |
| **reusable-lint** | Multi-format static analysis (shell, YAML, JSON, Justfile, Actions) | Every PR | [#2250](https://github.com/tuna-os/tunaOS/issues/2250), [.github#14](https://github.com/tuna-os/.github/issues/14) |
| **reusable-ci-contract** | Verify CI green criteria match real workflows | Every PR | [#2250](https://github.com/tuna-os/tunaOS/issues/2250), [.github#1](https://github.com/tuna-os/.github/issues/1) |
| **reusable-fork-safety** | Enforce permissions and secret handling in fork-safe jobs | Every PR | [#2250](https://github.com/tuna-os/tunaOS/issues/2250), [.github#13](https://github.com/tuna-os/.github/issues/13) |
| **reusable-scorecard** | OpenSSF supply-chain security analysis | Weekly or on-demand | [#2250](https://github.com/tuna-os/tunaOS/issues/2250), [.github#10](https://github.com/tuna-os/.github/issues/10) |
| **reusable-first-contributor** | Welcome message for first-time contributors | issue/PR events | [#2250](https://github.com/tuna-os/tunaOS/issues/2250) |
| **reusable-add-help-wanted** | Auto-label unassigned issues | issue events | [#2250](https://github.com/tuna-os/tunaOS/issues/2250) |
| **reusable-pr-nudges** | Context-aware reminders for PR reviewers/authors | Pull request events | [#2250](https://github.com/tuna-os/tunaOS/issues/2250), [.github#11](https://github.com/tuna-os/.github/issues/11) |
| **reusable-release-verification** | Verify release tag integrity and artifacts | release events | Release governance |
| **publish-flatpak** | Build OCI, push to GHCR, update central Flatpak index | flatpak app release | [tunaOS#1183](https://github.com/tuna-os/tunaOS/issues/1183), [.github#139](https://github.com/tuna-os/.github/issues/139) |

## Detailed Workflows

### ste-lint — Simplified Technical English Linting

**Purpose:** Enforce consistent, accessible prose quality across all TunaOS documentation by checking README.md, CONTRIBUTING.md, and other prose files against Simplified Technical English (STE) rules.

**When to use:** Every repository with documentation that users will read.

**Integration:**

```yaml
name: Lint Prose

on:
  pull_request:
    paths:
      - "**.md"
      - "docs/**"
  workflow_dispatch:

permissions:
  contents: read

jobs:
  ste:
    uses: tuna-os/.github/.github/workflows/ste-lint.yml@main
    with:
      budget-file: .ste-budget
      budget: "0"  # Seed with 0; run once, commit the output
```

**Inputs:**

- `budget-file` (string, default: `.ste-budget`) — Path to file containing the maximum tolerated findings count.
- `budget` (string, default: empty) — Fallback budget if file does not exist. Seed a repo by running once and committing the count.

**Expected outputs:**

- Step annotations on violations
- PR comment with findings (if permissions allow)
- Exit code 0 if findings ≤ budget, 1 otherwise

**Ratchet pattern:** The budget can only go down, never up. This prevents regressions and incentivizes incremental prose improvements.

**Learn more:** [`.github/STE-LINTING.md`](STE-LINTING.md) (planned)

---

### reusable-lint — Multi-Format Static Analysis

**Purpose:** Unified lint workflow for shell scripts, YAML, JSON, Justfiles, and GitHub Actions workflows.

**When to use:** Every repo as part of CI, especially those with infrastructure-as-code or shell utilities.

**Integration:**

```yaml
name: Lint

on:
  pull_request:
  push:
    branches: [main, dev]  # Or your repo's default
  workflow_dispatch:

permissions:
  contents: read

jobs:
  lint:
    uses: tuna-os/.github/.github/workflows/reusable-lint.yml@main
    with:
      checks: '["shellcheck", "yamllint", "json-validate", "actionlint", "justfmt"]'
```

**Inputs:**

- `checks` (string, default: `["shellcheck", "yamllint", "json-validate", "actionlint", "justfmt"]`) — JSON array of linters to run. Omit any you don't use.

**Checks:**

- `shellcheck` — Shell script analysis (bash, sh, etc.)
- `yamllint` — YAML lint (workflows, configs)
- `json-validate` — JSON syntax validation
- `actionlint` — GitHub Actions workflow validation
- `justfmt` — Justfile format check

**Expected outputs:**

- Inline step annotations for each violation
- Exit code 1 if any check fails, 0 otherwise

---

### reusable-ci-contract — CI Contract Verification

**Purpose:** Verify that every CI green criterion in `.github/green-criteria.yml` is asserted by real, reachable workflows and satisfies freshness SLAs.

**When to use:** Repos implementing [Hive practice #1](https://github.com/tuna-os/tunaOS/issues/2250) (CI contract enforcement). Runs as part of PR checks to prevent criteria drift.

**Integration:**

```yaml
name: CI Contract

on:
  pull_request:
    paths:
      - .github/green-criteria.yml
      - .github/workflows/**
  workflow_dispatch:

permissions:
  contents: read

jobs:
  contract:
    uses: tuna-os/.github/.github/workflows/reusable-ci-contract.yml@main
    with:
      criteria-path: .github/green-criteria.yml
      workflows-dir: .github/workflows
      python-version: "3.11"
```

**Inputs:**

- `criteria-path` (string, default: `.github/green-criteria.yml`) — Path to the criteria file.
- `workflows-dir` (string, default: `.github/workflows`) — Directory containing workflow YAML files.
- `python-version` (string, default: `"3.11"`) — Python version for the verification script.

**Expected outputs:**

- Verifies each criterion has an `id`, `gates`, `freshness_sla_days`, `enforcement`, and `asserted_by` field.
- Checks that every `gates` job exists in a workflow.
- Fails if any criterion is unmeetable or stale.

**Learn more:** [`.github/GREEN-CRITERIA.md`](GREEN-CRITERIA.md) (planned)

---

### reusable-fork-safety — Fork Safety Checks

**Purpose:** Enforce that pull_request workflows are safe when run from forks (with read-only GITHUB_TOKEN and no secrets).

**When to use:** Repos that accept community PRs from forks. Verify workflow defensiveness against limited token scope.

**Integration:**

```yaml
name: Fork Safety

on:
  pull_request:
    paths:
      - .github/workflows/**
  workflow_dispatch:

permissions:
  contents: read

jobs:
  fork-safety:
    uses: tuna-os/.github/.github/workflows/reusable-fork-safety.yml@main
    with:
      workflows-dir: .github/workflows
      python-version: "3.11"
```

**Inputs:**

- `workflows-dir` (string, default: `.github/workflows`) — Directory containing workflow YAML files.
- `python-version` (string, default: `"3.11"`) — Python version for the verification script.

**Checks:**

- All `pull_request` workflows declare explicit `permissions:` blocks.
- `pull_request_target` is not used without an explicit exception.
- Steps performing write operations or referencing secrets are guarded (e.g., `if: github.event_name != 'pull_request'`).

**Expected outputs:**

- Exit code 1 if any check fails, 0 otherwise.

---

### reusable-scorecard — OpenSSF Supply-Chain Security

**Purpose:** Run OpenSSF Scorecard to assess supply-chain security posture and detect common vulnerabilities in dependencies and CI.

**When to use:** Weekly or on-demand security assessment. Especially valuable for projects shipping binaries or libraries.

**Integration:**

```yaml
name: Scorecard

on:
  schedule:
    - cron: '0 6 * * 0'  # Weekly, Sundays at 6 AM UTC
  workflow_dispatch:

permissions:
  contents: read

jobs:
  scorecard:
    uses: tuna-os/.github/.github/workflows/reusable-scorecard.yml@main
    with:
      publish-results: false  # Set true to upload to OpenSSF REST API
```

**Inputs:**

- `publish-results` (boolean, default: `false`) — Whether to publish results to OpenSSF REST API. Requires identity token federation setup.

**Expected outputs:**

- SARIF file with supply-chain security findings (viewable in GitHub Security tab).
- If `publish-results: true`, results posted to OpenSSF dashboard.

---

### reusable-first-contributor — Welcome Message

**Purpose:** Post a friendly welcome message to first-time contributors opening issues or PRs.

**When to use:** Repos that encourage community participation.

**Integration:**

```yaml
name: Welcome

on:
  pull_request:
    types: [opened]
  issues:
    types: [opened]

permissions:
  contents: read
  issues: write
  pull-requests: write

jobs:
  welcome:
    uses: tuna-os/.github/.github/workflows/reusable-first-contributor.yml@main
    with:
      pr_message: |
        👋 Welcome to the TunaOS community! 🐟
        ...
      issue_message: |
        👋 Welcome to the TunaOS community! 🐟
        ...
```

**Inputs:**

- `pr_message` (string) — Custom message for first-time PR contributors. Default includes DCO sign-off reminder.
- `issue_message` (string) — Custom message for first-time issue authors.

**Expected outputs:**

- PR comment or issue comment greeting the contributor (first-time only).

---

### reusable-add-help-wanted — Auto-Label

**Purpose:** Automatically add `help wanted` label to unassigned issues when a maintainer labels them.

**When to use:** Repos using the `help wanted` → unassigned workflow for community issue discovery.

**Integration:**

```yaml
name: Label

on:
  issues:
    types: [labeled]

permissions:
  issues: write

jobs:
  label:
    uses: tuna-os/.github/.github/workflows/reusable-add-help-wanted.yml@main
```

**Expected outputs:**

- Adds `help wanted` label to unassigned issues.

---

### reusable-pr-nudges — Context-Aware Reminders

**Purpose:** Post advisory reminders derived from the files a PR touches (e.g., "This PR touches workflows; please verify permissions blocks").

**When to use:** Repos with governance-sensitive files (workflows, security configs, APIs).

**Integration:**

```yaml
name: PR Nudges

on:
  pull_request:
    types: [opened, synchronize]

permissions:
  contents: read
  pull-requests: write

jobs:
  nudges:
    uses: tuna-os/.github/.github/workflows/reusable-pr-nudges.yml@main
    with:
      script-path: .github/scripts/pr-nudges.sh
```

**Inputs:**

- `script-path` (string, default: `.github/scripts/pr-nudges.sh`) — Path to the nudge script in your repo. Can run custom checks per repo.

**Secrets:**

- `token` (optional) — GitHub token. Defaults to `${{ github.token }}` (GITHUB_TOKEN).

**Expected outputs:**

- Step summary with reminders.
- PR comment (if permissions allow).
- Never fails the workflow.

**Learn more:** [`.github/scripts/pr-nudges.sh`](scripts/pr-nudges.sh) template (planned)

---

### reusable-release-verification — Release Integrity

**Purpose:** Verify that a GitHub release tag resolves to the expected commit and includes expected artifacts with correct checksums and signatures.

**When to use:** Repos shipping releases with provenance verification, SBOM, and signed artifacts.

**Integration:**

```yaml
name: Verify Release

on:
  workflow_dispatch:
    inputs:
      release-tag:
        description: Release tag to verify (e.g., v1.2.3)
        required: true

permissions:
  contents: read

jobs:
  verify:
    uses: tuna-os/.github/.github/workflows/reusable-release-verification.yml@main
    with:
      release-tag: ${{ github.event.inputs.release-tag }}
      expected-commit: abc123def456...  # Full SHA
      expected-artifacts: |
        [
          {"name": "app.tar.gz", "checksum": "sha256:..."},
          {"name": "app.tar.gz.sig", "signature": "..."},
          {"name": "app.sbom.json", "sbom": "..."}
        ]
```

**Inputs:**

- `release-tag` (string, required) — GitHub release tag (e.g., `v1.2.3`).
- `expected-commit` (string, required) — Full commit SHA the tag must resolve to.
- `expected-artifacts` (string, required) — JSON array of artifact objects with `name`, `checksum`, `signature`, `provenance`, `sbom`.
- `repository` (string, default: current repo) — Repository containing the release (`owner/name`).

**Expected outputs:**

- Exit code 0 if release verified; 1 otherwise.

---

### publish-flatpak — Flatpak Build & Publish

**Purpose:** Canonical reusable workflow for building OCI images, pushing to GHCR, and updating the central TunaOS Flatpak index.

**When to use:** Flatpak application repositories in the TunaOS org.

**Integration:**

```yaml
name: Publish Flatpak

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: read

jobs:
  publish:
    uses: tuna-os/.github/.github/workflows/publish-flatpak.yml@main
    with:
      app-id: org.tunaos.app
      manifest: flatpak/org.tunaos.app.json
      upload-to-flathub: false
    secrets:
      FLATPAK_INDEX_TOKEN: ${{ secrets.FLATPAK_INDEX_TOKEN }}
```

**Inputs:**

- `app-id` (string, required) — Flatpak application ID (e.g., `org.tunaos.gtk-office-suite`).
- `manifest` (string) — Path to Flatpak manifest JSON file.
- `generate-cargo-sources` (boolean, default: `false`) — Generate offline Cargo sources (Rust apps only).
- `upload-to-flathub` (boolean, default: `false`) — Upload to Flathub (separate from TunaOS index).
- `source-repo` (string, optional) — Clone this repo instead of using caller source (for republished upstream projects).

**Secrets:**

- `FLATPAK_INDEX_TOKEN` (required) — Token for publishing to the central TunaOS Flatpak index.

**Expected outputs:**

- OCI image pushed to GHCR.
- Central Flatpak index updated.
- Release notes with build metadata.

**Learn more:** [`.github/actions/update-flatpak-index/README.md`](actions/update-flatpak-index/README.md)

---

## Security Considerations

All reusable workflows declare explicit `permissions:` blocks to enforce least privilege. Review the top-level `permissions` and any job-level overrides when integrating a workflow into your repo.

## Cross-Repo Links

- **Hive practices:** Epic [#2250](https://github.com/tuna-os/tunaOS/issues/2250)
- **AGENTS.md:** [High-level overview](AGENTS.md)
- **CONTRIBUTING.md:** [How to contribute](../CONTRIBUTING.md)
- **STE linting:** [`.github/STE-LINTING.md`](STE-LINTING.md) (planned)
- **CI contract:** [`.github/GREEN-CRITERIA.md`](GREEN-CRITERIA.md) (planned)

## Troubleshooting

**Workflow won't run:** Check that your repo's branch has the caller workflow that uses the reusable one. Reusable workflows defined here are not automatically called; the caller initiates them.

**Permission denied:** Verify top-level `permissions:` in your caller workflow. The reusable workflow cannot request permissions beyond what the caller grants.

**Input validation error:** Ensure JSON inputs (e.g., `checks`, `expected-artifacts`) are properly escaped. Use `|` for multiline strings in YAML.

**Action version errors:** All GitHub Actions in these workflows are pinned to commit SHAs. If you see a mismatch, verify the main branch is up to date.

## Contributing

To add a new reusable workflow or update an existing one, open an issue in [tuna-os/.github](https://github.com/tuna-os/.github) and link it to [epic #2250](https://github.com/tuna-os/tunaOS/issues/2250).
