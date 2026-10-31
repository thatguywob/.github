# Workflow security baseline

Use `ci.yml` as a baseline for an existing repository. New repositories
can copy `project-starter/`. These are copies: changes here reach a consumer
only after a pull request in that repository.

This checklist supports the rollout in
[tunaOS#3152](https://github.com/tuna-os/tunaos/issues/3152).

## Review a new or changed workflow

- Declare a top-level `permissions: { contents: read }` baseline. Use an empty
  map when no job needs a token, and declare each job's grants explicitly.
  Avoid `read-all` and `write-all`; list only required scopes.
- Put write grants on the job that needs them. For example, a GHCR publisher
  needs `packages: write`; a release uploader needs `contents: write`.
  A job's map replaces the workflow map, so repeat needed read scopes there.
- Pin remote actions and reusable workflows to complete SHAs of commits.
  Keep a version comment for updates. Local `./` actions use the checkout's
  commit. Review the source repository and commit before adding a pin.
- Use `persist-credentials: false` for checkout unless a later Git operation
  needs those credentials. Give that operation only its required scope.
- Keep uploads and secrets on trusted events. A fork pull request must not
  receive upload credentials. Do not execute code from pull requests in a
  privileged `pull_request_target` job.
- Pass untrusted values through `env:`. Do not insert issue titles, branch
  names, or other event text into the body of a shell script.
- Adapt trigger branches to the repository's required PR base. Check its local
  contribution guide before using the example `main` branch.

Resolve a reviewed version to its commit with the GitHub API. Annotated tags
need another lookup: a tag object's SHA is not a commit SHA.

```bash
gh api repos/actions/checkout/git/ref/tags/v7 --jq '.object'
# If type is "tag", query repos/OWNER/REPO/git/tags/OBJECT_SHA until
# the object type is "commit". Use that commit in the uses reference.
```

Keep pins current through Renovate. A pin fixes the code revision that runs;
it does not prove that the code is safe.

## Validate adoption

Copy `scripts/check-workflow-permissions.py` and
`scripts/check-workflow-action-pins.py` from this repository. Run:

```bash
python3 scripts/check-workflow-permissions.py .github/workflows
python3 scripts/check-workflow-action-pins.py .github/workflows
```

The checker reads declarations. It does not verify that each job needs every grant.
It now rejects `permissions: {}`. Review that valid form separately
until the checker supports it. Do not grant token
access to satisfy that limitation. Review write scopes and event trust by job.

Keep both checks in CI. The starter includes both jobs in the `required-checks`
dependencies. Existing repositories can add them to their own CI gate. The
checks here also scan the distributed templates, so a tag added to a template
fails before a consumer copies it.

Include the check results, changed workflow paths, reviewed action revisions,
and any runtime permission evidence in the consumer PR. Close each security
issue only after the fix merges into that repository's required branch and
the affected workflow passes. Template publication alone does not fix it.

App-level workflow write permission is separate from runtime `GITHUB_TOKEN`
permissions. If GitHub rejects a push, use the
[publication runbook](https://github.com/tuna-os/tunaos/blob/main/docs/CI-WORKFLOW-PUBLISHING.md).
