# Flatpak index publishing secret

`FLATPAK_INDEX_TOKEN` authenticates writes to the central index in
`tuna-os/docs`. GHCR uploads use `GITHUB_TOKEN` separately. Org owners manage
this credential; contributors must never paste its value into issues, PRs,
workflow inputs, or logs.

## Provision and audit

1. An org owner creates a fine-grained PAT for a service identity with access
   to `tuna-os/docs`, restricted to that repository with **Contents: write**
   (and the automatically included Metadata: read). Set an expiry and record
   the owner and renewal date in the organisation's credential inventory.
2. In **tuna-os → Settings → Secrets and variables → Actions**, create the
   organization secret `FLATPAK_INDEX_TOKEN`. Grant access only to selected
   repositories that publish Flatpaks, rather than all repositories.
3. Audit that selected-repository list when adding or retiring a publisher.
   Remove repository-level secrets with the same name after migration has
   been verified: repository secrets override organization secrets and would
   otherwise continue using the old credential.

This document describes the required configuration; merging code does not
provision a secret or change its access policy.

## Reusable workflow callers

Same-org callers can forward the organization secret without repeating its
name at each workflow boundary:

```yaml
jobs:
  publish:
    permissions:
      contents: write
      packages: write
    uses: tuna-os/.github/.github/workflows/publish-flatpak.yml@main
    with:
      app-id: org.tunaos.finupdate
      manifest-path: build-aux/org.tunaos.finupdate.json
      repo-name: tuna-os/finupdate
    secrets: inherit
```

`secrets: inherit` forwards all secrets available to the caller, so use it only
with trusted workflows. An explicit mapping of `FLATPAK_INDEX_TOKEN` remains
supported for callers that need a narrower boundary. Each nested workflow must
forward secrets again; org secrets are not automatically visible in a called
workflow. Creating a secret only in `tuna-os/.github` does not expose it to
other caller repositories.

The workflow checks that the secret is nonempty in `arch-plan`, before any
build starts, when `publish: true`. Build-only calls (`publish: false`) need no
index credential, including fork PR validation. GitHub's `required: true`
checks that a secret is passed, not that its value is nonempty.

## Direct composite action callers

Composite actions cannot read the `secrets` context directly. Map the secret
into the action step's environment:

```yaml
- uses: tuna-os/.github/.github/actions/publish-flatpak-index@main
  env:
    FLATPAK_INDEX_TOKEN: ${{ secrets.FLATPAK_INDEX_TOKEN }}
  with:
    oci-dir: oci/mandelbrot-oci-x86_64
    repo-name: tuna-os/mandelbrot
```

The existing `with.token` input remains supported and takes precedence over
the environment variable. This preserves callers pinned to `@main`. The action
fails immediately if neither source is nonempty and registers the selected
value with `add-mask` before using it. Values sourced from Actions secrets
remain masked when passed through an environment variable; environment passing
does not remove GitHub's masking. Avoid shell tracing and printing credentials.
The action still checks push permission before cloning: a nonempty secret may
be expired, revoked, or scoped to the wrong repository.

## Rotate or revoke

1. The credential owner issues a replacement with the same restricted scope.
2. An org owner updates the existing organization secret, preserving its
   selected-repository access policy. Update any intentional repository
   overrides separately, or remove them to adopt the org secret.
3. Verify a publish from an authorized repository updates the central index.
   Secrets are read when a workflow run is queued, so already queued or running
   jobs may still hold the previous value. Account for those runs before
   revoking the old credential during routine rotation.
4. Revoke the old PAT and record the new expiry in the credential inventory.
   If compromise is suspected, revoke immediately and rerun failed publishes
   after the replacement is available.

References: [reuse workflows](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows),
[secrets reference](https://docs.github.com/en/actions/reference/security/secrets).
