# TunaOS project starter

A curated, copyable baseline for TunaOS projects. It distils the practices that recur across the organisation while keeping heavy integrations opt-in.

## Start a project

1. Create the repository and copy this directory's contents to its root.
2. Replace every `<…>` placeholder.
3. Fill in `ROADMAP.md` with your current quarter's goals and priorities — link each goal to a GitHub issue.
4. Keep the targets you implement in `Justfile`; remove unused workflow templates.
5. Enable branch protection with `CI / required-checks` as the required check.
6. Enable Renovate for the repository.
7. Keep a visible [Hive donation link](https://hub.tunaos.org/#contribute) in
   the project's README and community guidance. Repositories without their own
   contributor guide inherit the
   [organization guide](https://github.com/tuna-os/.github/blob/main/CONTRIBUTING.md).
   If you add a local guide, retain the donation link alongside code and docs
   contribution instructions; link to the hub instead of copying its setup command.

## What is included

| Component | Purpose | Source pattern |
| --- | --- | --- |
| `ROADMAP.md` | Quarterly goals, priorities, and strategic direction — every project should plan in the open | tunaOS, tromso, tacklebox |
| `Justfile` | One discoverable local command surface | tunaOS, bootc-migrate, wootc |
| `renovate.json` | Automated dependency, action, digest, and pin updates | organisation default, tunaOS |
| `ci.yml` | Least-privilege checks, cancellation, and a branch-protection sentinel | bootc-migrate |
| `scripts/check-workflow-permissions.py` | CI gate: fails the build if any workflow omits a top-level `permissions:` block, so jobs inherit the least-privilege scope (tuna-os/.github#155) | tuna-os/.github#155 |
| `scripts/check-workflow-action-pins.py` | CI gate: rejects mutable action and reusable workflow references | tuna-os/.github#285 |
| `scripts/check-renovate-automerge-policy.py` | CI gate: fails the build if `renovate.json` would automerge a major/minor update, even via rule layering (tuna-os/.github#12) | tuna-os/tunaOS#1636 |
| `flatpak-remote.yml` | Build an OCI Flatpak and update a hosted remote index | tuna-os/docs |
| `docs-artifacts.yml` | Turn validated screenshots or walkthroughs into versioned docs | tunaOS → docs |
| `release.yml` + `release-artifacts.json` | Publish a release, then fail closed unless its tag and integrity evidence verify | organisation release policy |

 The `scripts/check-*.py` gates are byte-identical copies of the canonical
 scripts in [`tuna-os/.github/scripts/`](https://github.com/tuna-os/.github/tree/main/scripts).
 Update the canonical scripts first. Copy them here in the same commit.
 See the [sync process](../CONTRIBUTING.md#shared-scripts-and-their-canonical-sources).

## Release verification profile

Before enabling `release.yml`:

1. Replace `<owner>/<repository>`. Keep the reusable workflow pinned to a
   reviewed, complete 40-character commit SHA from `tuna-os/.github`; never
   replace it with `main`, a tag, or a shortened SHA.
2. Make the release tool append `RELEASE_TAG=<published-tag>` to `GITHUB_ENV`.
3. Replace the example entries in `.github/release-artifacts.json`. Each
   published payload declares five distinct release asset names: the payload,
   its SHA-256 checksum file, detached signature, provenance, and SBOM. Add one
   object per payload.
4. Keep `verify-release` dependent on the publishing job. It verifies that the
   tag resolves to the publishing commit, requires every declared evidence
   asset to be non-empty, downloads each payload, and checks its SHA-256 entry.
   Missing assets, malformed contracts, checksum mismatches, and GitHub API
   failures all fail the release workflow.

The verifier has only `contents: read`; publication credentials remain confined
to the publishing job. The release job is intentionally incomplete until a
project replaces its tooling placeholders.

## Principles

- Make the normal path obvious: `just check` should reproduce CI locally.
- Prefer narrow, independently observable jobs. Add a single required sentinel only after it depends on every real gate.
- Pin build inputs where reproducibility matters; let Renovate maintain pins. Debounce fast-moving image digests rather than burning CI on every upstream change.
- Treat generated documentation as a release artifact: capture it from the real product, preserve artifacts on failures, and commit only after validation.
- Use least privilege by default. Never expose secrets or privileged runners to untrusted fork pull requests.
- Make automation idempotent and explain its operational constraints beside the code.
- Keep heavyweight E2E scheduled or explicitly dispatched; make PR gates proportional to risk.

Read [ADOPTING.md](docs/ADOPTING.md) before enabling a profile. These are templates, not a mandate: remove anything that does not serve the project.
