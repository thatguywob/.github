# CI Contract Verification — Green Criteria Pattern

TunaOS uses a CI contract pattern to ensure that every criterion used to mark a PR as "green" (ready to merge) is backed by real, reachable workflows and jobs. This prevents criteria drift and makes CI expectations transparent.

## What is a CI Contract?

A CI contract is a machine-readable specification that says: "This repo's 'ready to merge' status is checked by these specific jobs, from these specific workflows, and the results stay fresh (less than N days old)."

The contract guards against two failure modes:

1. **Criteria drift** — A criterion is documented but not actually checked by any workflow, or the named job no longer exists
2. **Stale results** — A job passes, but its results are old enough that the code may have changed significantly

## Why This Matters

When a maintainer says "all checks pass," they should be confident that means:
- Every check they declared is actually running
- Every check is backed by a real job in a real workflow
- Results are fresh (within the SLA, e.g., rerun daily)

Without a contract, a repo can accidentally declare a criterion that no workflow enforces. New contributors and reviewers then rely on a check that isn't actually happening.

## Quick Start: Adding a CI Contract to Your Repo

### Step 1: Create `.github/green-criteria.yml`

In your repository's `.github/` directory, create a `green-criteria.yml` file that lists your CI green criteria:

```yaml
green-criteria:
  - id: lint
    description: All linting checks pass (shell, YAML, JSON, Justfile, Actions)
    gates:
      - workflow: lint.yml
        job: lint
    freshness_sla_days: 1
    enforcement: required
    asserted_by: tuna-os/.github/.github/workflows/reusable-lint.yml

  - id: tests
    description: Unit and integration tests pass
    gates:
      - workflow: test.yml
        job: unit-tests
      - workflow: test.yml
        job: integration-tests
    freshness_sla_days: 1
    enforcement: required
    asserted_by: Your repo's test.yml

  - id: ste-linting
    description: Prose passes Simplified Technical English checks
    gates:
      - workflow: ste.yml
        job: ste
    freshness_sla_days: 3
    enforcement: optional
    asserted_by: tuna-os/.github/.github/workflows/ste-lint.yml
```

### Step 2: Add the Reusable CI Contract Workflow

Create `.github/workflows/ci-contract.yml` in your repo:

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

### Step 3: Run It

Push your branch. The workflow will:
1. Parse `.github/green-criteria.yml`
2. Scan `.github/workflows/` for matching jobs
3. Verify each criterion has a backing job that can be reached
4. Check freshness SLA constraints
5. Report any mismatches

## Understanding the Schema

### `green-criteria` (array)

A list of CI criteria that define "ready to merge" for your repo.

### Each Criterion

#### `id` (string, required)

Unique identifier for this criterion. Use lowercase alphanumeric + hyphens. Example: `unit-tests`, `lint`, `security-scan`.

#### `description` (string, required)

Human-readable description of what this criterion checks. Example: `"All unit and integration tests pass"`.

#### `gates` (array of objects, required)

One or more workflow/job pairs that assert this criterion. A criterion is satisfied if **any one** of its gates is passing (OR logic).

Each gate has:

- **`workflow`** (string, required) — Filename of the workflow in `.github/workflows/` (e.g., `test.yml`)
- **`job`** (string, required) — The job name within that workflow (must match the top-level job key)

Example with multiple gates:

```yaml
gates:
  - workflow: test.yml
    job: unit-tests
  - workflow: test.yml
    job: integration-tests
```

This criterion passes if **either** `unit-tests` or `integration-tests` passes.

#### `freshness_sla_days` (integer, required)

How old can a passing result be before it's considered stale? In days.

- `1` — Results must be less than 24 hours old
- `7` — Results can be up to 7 days old
- `30` — Results stay valid for a month

This prevents relying on test results from before a recent commit landed.

#### `enforcement` (string, required)

Whether this criterion blocks merging:

- `required` — PR cannot merge unless this criterion passes. GitHub branch protection rules should require this job's status.
- `optional` — This criterion is tracked but not required. Useful for advisory checks (e.g., "code coverage improved") that don't block merge.

#### `asserted_by` (string, required)

The **source** of this job. Either:

- A URL to the reusable workflow that provides it (e.g., `tuna-os/.github/.github/workflows/reusable-lint.yml`) if this is a shared workflow
- A note about where it's defined (e.g., `"Your repo's Makefile target \`make test\`") if it's repo-specific

This documents why the job exists and where to find its implementation.

## Worked Example

A Rust project with linting, unit tests, security checks, and optional coverage:

```yaml
green-criteria:
  - id: format
    description: Code is formatted with `cargo fmt`
    gates:
      - workflow: ci.yml
        job: format
    freshness_sla_days: 1
    enforcement: required
    asserted_by: tuna-os/.github/.github/workflows/reusable-lint.yml

  - id: clippy
    description: No Clippy lints (Rust code analysis)
    gates:
      - workflow: ci.yml
        job: clippy
    freshness_sla_days: 1
    enforcement: required
    asserted_by: tuna-os/.github/.github/workflows/reusable-lint.yml

  - id: unit-tests
    description: Unit tests pass
    gates:
      - workflow: ci.yml
        job: test
    freshness_sla_days: 1
    enforcement: required
    asserted_by: Cargo test suite (ci.yml)

  - id: security
    description: No known vulnerabilities in dependencies
    gates:
      - workflow: security.yml
        job: audit
    freshness_sla_days: 7
    enforcement: required
    asserted_by: `cargo audit` (security.yml)

  - id: coverage
    description: Unit test code coverage above 70%
    gates:
      - workflow: ci.yml
        job: coverage
    freshness_sla_days: 3
    enforcement: optional
    asserted_by: Code coverage tool (ci.yml)
```

## Common Patterns

### Multiple Jobs for One Criterion

Use multiple gates when a criterion requires **any one** of several checks to pass:

```yaml
gates:
  - workflow: test.yml
    job: test-linux
  - workflow: test.yml
    job: test-macos
  - workflow: test.yml
    job: test-windows
```

This criterion passes if tests pass on any supported OS.

### Reusable Workflows

When your repo uses a reusable workflow from another repo:

```yaml
gates:
  - workflow: ci.yml
    job: lint
asserted_by: tuna-os/.github/.github/workflows/reusable-lint.yml
```

This documents that the job is provided by a shared workflow, not implemented locally.

### Optional vs. Required

Use `optional` for advisory checks:

```yaml
- id: performance
  description: Performance benchmarks don't regress
  gates:
    - workflow: bench.yml
      job: benchmark
  freshness_sla_days: 7
  enforcement: optional
  asserted_by: Performance benchmark (bench.yml)
```

Maintainers can review this before merge, but it won't block if it fails.

## Troubleshooting

### "Criterion lint: no matching job found"

The workflow or job name doesn't exist or doesn't match.

**Fix:**
1. Check the spelling of the workflow file (must match `.github/workflows/filename.yml`)
2. Verify the job name matches the top-level `jobs:` key in that workflow
3. Run the contract check locally to see the error detail

### "Criterion tests: SLA breach (results 10 days old)"

The job passed, but the results are older than `freshness_sla_days`.

**Fix:**
1. Rerun the job (manually or by pushing a new commit)
2. Or increase `freshness_sla_days` if you're OK with older results

### "Criterion coverage: job exists but is skipped/skipped on all runs"

A job exists but has a condition (`if:`) that prevents it from running.

**Fix:**
1. Ensure the job runs on pull_request events (check the `on:` trigger)
2. Check if the job's `if:` condition is too restrictive

## Common Mistakes

### ❌ Documenting a criterion that no workflow runs

```yaml
- id: integration-tests
  gates:
    - workflow: test.yml
      job: integration
  # ERROR: test.yml has no job named "integration"
```

**Fix:** Either add the job to test.yml, or remove the criterion.

### ❌ Workflow names that don't match files

```yaml
gates:
  - workflow: tests  # ERROR: should be "tests.yml"
    job: test
```

**Fix:** Include `.yml` extension to match the actual filename.

### ❌ Forgetting to update the contract when changing workflow structure

You rename `test.yml` → `ci.yml`, but forget to update green-criteria.yml.

**Fix:** Update both files in the same commit. The contract check will catch mismatches on the next PR.

## Integrating with Branch Protection

Once your green-criteria.yml is solid, configure GitHub branch protection to require the criteria:

1. Go to repository Settings → Branches → Branch Protection Rules
2. Enable "Require status checks to pass before merging"
3. Add each `required` criterion by its workflow job name

Example: For the Rust project above, require:
- `ci.yml / format`
- `ci.yml / clippy`
- `ci.yml / test`
- `security.yml / audit`

This ensures the contract is enforced by GitHub, not just verified locally.

## Reference

- **Hive Practice #1:** [epic #2250](https://github.com/tuna-os/tunaOS/issues/2250)
- **Reusable Workflow:** `.github/workflows/reusable-ci-contract.yml` in [tuna-os/.github](https://github.com/tuna-os/.github)
- **CI Contract Action:** `.github/actions/ci-contract-check/` in [tuna-os/.github](https://github.com/tuna-os/.github)
- **WORKFLOWS.md:** [Reusable workflows index](WORKFLOWS.md)

## Questions?

Ask in the [tuna-os/.github](https://github.com/tuna-os/.github) repository or in the TunaOS community channels.
