# Adopting TunaOS project patterns

## Baseline

Use a Justfile as the public local interface. `just check` must run the same fast checks that CI runs. Keep `e2e`, releases, and screenshot capture explicit or scheduled when they require privileged hardware, long execution, or secrets.

The CI template uses full commit pins. Keep these pins when you install the project's tools. Run both workflow checks before you enable CI; see the [security checklist](https://github.com/tuna-os/.github/blob/main/workflow-templates/README.md). Configure branch protection with **only** `CI / required-checks` as the required check. Update its `needs` list for each new required job.

## Dependency updates

The organisation baseline automerges **only** `patch`/`pin`/`pinDigest`/`digest` Renovate updates, after branch protection passes — `major` and `minor` updates always need human review before merge (tuna-os/.github#12). Do not widen `renovate.json`'s automerge `matchUpdateTypes` to include `major`/`minor`, and do not set top-level `automerge`/`platformAutomerge` to `true` — that reintroduces exactly the org-gate bypass tracked in tuna-os/tunaOS#1612. The tuned OS configuration adds custom managers for image digests and pinned workflow SHAs. Copy those custom managers only when those file formats exist. For an upstream that moves several times a day, use `minimumReleaseAge` to coalesce updates.

Validate any hand-edited `renovate.json` with `npx -p renovate renovate-config-validator` before committing — a syntactically invalid config (e.g. a stray `"ignore": true` key, which isn't valid Renovate schema) silently halts *all* Renovate PRs for the repo, not just the one broken rule. That only catches schema errors, not policy violations: a config can be perfectly valid JSON and still automerge major/minor (that's exactly how tuna-os/tunaOS#1612 happened). `ci.yml`'s `renovate-policy` job runs `scripts/check-renovate-automerge-policy.py` against `renovate.json` on every push and PR, resolving the same rule-layering Renovate itself does (top-level `automerge`, overridden in order by each `packageRule`) and failing the build if any path leaves `major`/`minor` automerging — keep that job in `required-checks`' `needs` list.

## Flatpak remote

The central remote pattern in `tuna-os/docs` is intentionally two-stage:

1. Build each manifest in a known Flatpak builder environment and export OCI.
2. Publish the OCI and update the central static index only after a successful build.
3. Deploy the site when `static/flatpak/**` changes.
4. Run a remote sanity check that consumes the generated `.flatpakrepo`.

Do not grant cross-repository credentials to pull-request runs. Put index mutation behind trusted events and use a dedicated, minimally scoped token.

## Documentation evidence

TunaOS captures installer/desktop screens from QEMU, uploads artifacts even on failure, validates that capture meaningfully succeeded, and then a docs-side workflow imports the newest successful artifacts and regenerates the guide. This avoids hand-maintained product tours going stale.

The reusable rule is: **test the product, retain the evidence, publish only validated evidence.**

## Release and operational guardrails

- Serialize semantic releases on the protected default branch; queue rather than cancel releases.
- Use concurrency cancellation for superseded CI, but not for releases or remote mutations.
- Retain logs and artifacts on failure. Give each long-running stage its own timeout.
- For fork PRs, never run privileged QEMU/KVM jobs or expose secrets. Guard with a same-repository condition.
- Prefer containerized development/test environments where host toolchain drift is costly.
- Commit generated assets only when changed and mark generated-doc commits to avoid recursive CI where appropriate.
