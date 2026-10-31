# Experimental repository policy enrollment

This is a **read-only prototype**, not a fleet registry, actual enrollment,
policy adoption, or a GitHub settings controller. It applies existing checks to
three illustrative repositories: Tavern (app), tunaOS (image), and .github
(org infrastructure). The example choices do not assert maintainer consent or
conformance. Unlisted repositories and unselected profiles are **not evaluated**.

## Authority and scope

| Field or fact | Canonical source |
|---|---|
| Active repository names | GitHub, snapshotted in the generated `ROADMAP-INDEX.md` table by `scripts/roadmap-index.py`. The report checks exact spelling against that snapshot; refresh it before interpreting unknown names. |
| `schema_version` and allowed profile names | `organization/enrollment.schema.json` and the report implementation in this repository. Only version 1 is supported. |
| `name` and `profiles` in the example | `organization/enrollment.example.json` is an illustrative opt-in selection for this prototype only, not a second list of all repositories or a governance decision. |
| Workflow permissions | Each selected checkout's `.github/workflows`; interpreted by the existing `scripts/check-workflow-permissions.py`. |
| CI criteria, jobs, reachability | Each selected checkout's `.github/green-criteria.yml` and workflows; interpreted by the existing `.github/scripts/ci_contract.py` and `workflow_introspector.py`. |

The declaration does not duplicate owners, default branches, lifecycle state,
release channels, or publisher configuration. It adds only a selection of which
existing checks to run. `workflow-permissions` checks for a nonempty top-level
permissions declaration on every workflow; it does not verify least privilege.
`ci-contract` checks the shared validator's reachability and gate rules, and
additionally requires at least one criterion with a gate: missing/empty criteria
must not turn this opted-in check into a successful skip. Neither profile proves
that builds, releases, or publishers actually work. Policy ownership and
release/publisher surface declarations remain outside this bounded experiment.

## Run

Use Python 3.11+, PyYAML 6.x and jsonschema 4.x. For example, from this checkout:

```sh
python3 -m venv /tmp/enrollment-venv
/tmp/enrollment-venv/bin/pip install 'jsonschema>=4,<5' 'PyYAML>=6,<7'
/tmp/enrollment-venv/bin/python scripts/enrollment-report.py --workspace /path/to/tuna-os
```

The workspace must contain locally prepared checkouts named `Tavern`, `tunaOS`,
and `.github` (or the names in a custom `--declaration`). Select the intended
revision of each repo first; the tool does not fetch, verify remotes, or infer
branch identity. Symlinks to local checkouts are allowed. `--inventory` selects
an alternative ROADMAP-INDEX snapshot. Results are JSON on stdout; declaration
errors are on stderr. Exit 0 means every selected check passed, 1 means a check
failed or a checkout was unavailable, and 2 means the declaration or inventory
was rejected. The tool does not write to any checkout or GitHub.

The schema rejects extra fields, unknown profiles, unsupported versions and
invalid types; validation also rejects duplicate JSON keys, duplicate repository
references and names absent from the inventory. JSON inputs are capped at 64 KiB.
The table parser fails closed on missing, duplicate or malformed table rows.
This is a snapshot check, not a live GitHub membership or authorization check.

## Reference evaluation and observed example

Frostyard core's v1 schema uses closed versioned declarations; its validator
also checks cross-references and fixtures with expected rejections. Those ideas
are useful here, but its repository IDs, owner/governance models, settings
contracts and fleet machinery are not required for this experiment. This is an
independent implementation, not copied Frostyard code (no root license was
detected during the source audit). It reuses TunaOS checks rather than changing
their callers or making a second inventory.

One local run used Tavern `846b548`, tunaOS `e2ffd4d`, and this repository at
`f835d4a` plus the prototype. The permissions check passed for Tavern and
.github, and reported nine tunaOS workflow files lacking a top-level block.
The CI contract reported four criteria whose `reusable-build-image.yml` gate
was not reachable according to the shared local-workflow graph. These are
observations of the checkers at those revisions, not verified production
failures; in particular the reachability analysis does not establish behavior
through external callers. Rerunning after updating any checkout can differ.

Verification, including valid/invalid examples and a three-repository offline
integration scenario:

```sh
python -m unittest scripts.test_enrollment_report scripts.test_check_workflow_permissions
python scripts/test-roadmap-index.py
python .github/scripts/test_ci_contract.py
python .github/scripts/test_workflow_introspector.py
```
