# Safe environment variables in GitHub Actions

When writing a workflow or composite action, pass input and context values into
`env:`, then use quoted shell variables in `run:`. This keeps data out of the
shell source. The examples below use Bash (`shell: bash`); other interpreters
need their own variable syntax.

## Why expression interpolation can execute code

Actions evaluates `${{ }}` expressions and substitutes their results into the
script text **before Bash parses it**. An interpolated value can therefore
become shell syntax. This is unsafe even with double quotes:

```yaml
# Unsafe: the input becomes part of the script source.
- shell: bash
  run: |
    printf '%s\n' "${{ inputs.repo-name }}"
```

Quoting narrows the risk but does not remove it: a double quote in the value can
end the quoted region, and command substitutions such as `$(command)` can run
inside double quotes. Single quotes also fail if the value contains a single
quote. Do not try to escape arbitrary input by wrapping an expression in quotes.

With unquoted interpolation, a value such as `latest; touch /tmp/PWNED` can
introduce a second command. A successful final command can even make the step
exit successfully. See [GitHub's script injection explanation](https://docs.github.com/en/actions/concepts/security/script-injections).

## Keep values in environment variables

Map the expression into a step's `env:` and expand the variable with `"$VAR"`:

```yaml
- shell: bash
  env:
    REPO_NAME: ${{ inputs.repo-name }}
    PR_TITLE: ${{ github.event.pull_request.title }}
  run: |
    printf '%s\n' "$REPO_NAME" "$PR_TITLE"
```

Bash parses the fixed script and then expands the variables. Quotes, semicolons,
and `$(...)` inside their values remain data; Bash does not parse them again as
commands. Do not use `${{ env.REPO_NAME }}` in `run:`: that puts the value back
into the script source. Do not pass the value to `eval` or build a `bash -c`
command string from it, which would parse the data as code again.

### Index action: individual arguments

[update-flatpak-index/action.yml](../.github/actions/update-flatpak-index/action.yml)
maps each input into `env:`. This excerpt shows how paths and repository names
reach Python as individual arguments, even when they contain spaces:

```yaml
env:
  ACTION_PATH: ${{ github.action_path }}
  OCI_DIR: ${{ inputs.oci-dir }}
  INDEX_FILE: ${{ inputs.index-file }}
  REPO_NAME: ${{ inputs.repo-name }}
run: |
  python3 "$ACTION_PATH/update-index.py" \
    --oci-dir "$OCI_DIR" \
    --index-file "$INDEX_FILE" \
    --repo-name "$REPO_NAME"
```

### Cargo sources: input paths in a reusable workflow

The `Generate offline cargo sources` step in
[publish-flatpak.yml](../.github/workflows/publish-flatpak.yml) uses the same
pattern. Its environment mapping and final command are:

```yaml
env:
  CARGO_LOCK_PATH: ${{ inputs.cargo-lock-path }}
  CARGO_SOURCES_OUTPUT: ${{ inputs.cargo-sources-output }}
run: |
  python3 /tmp/flatpak-cargo-generator.py "$CARGO_LOCK_PATH" \
    -o "$CARGO_SOURCES_OUTPUT"
```

This is an excerpt, not a replacement for the full step: keep its pinned
source download and SHA-256 verification before executing the generator.
Those controls address the dependency risk from [#97](https://github.com/tuna-os/.github/issues/97);
[merged PR #346](https://github.com/tuna-os/.github/pull/346) added them and the
environment mappings. Passing paths through `env:` prevents script injection;
it does not establish trust in downloaded code.

## Quote single values; split lists into arrays

Use `"$VAR"` for one argument. An unquoted `$VAR` undergoes word splitting and
pathname expansion: spaces can create extra arguments, and `*` can expand to
filenames. Although expansion does not turn a semicolon in a variable into a
shell command, it can still change the arguments the program receives.

For an input that deliberately contains multiple items, define its format and
split it explicitly. The index action's `tags` input is a space-separated list
on one line. It uses Bash's `read -ra` and validates each item:

```yaml
env:
  TAGS: ${{ inputs.tags }}
run: |
  set -euo pipefail
  read -ra tag_args <<<"$TAGS"
  if [ "${#tag_args[@]}" -eq 0 ]; then
    echo "::error::tags input is empty" >&2
    exit 1
  fi
  for tag in "${tag_args[@]}"; do
    if ! [[ "$tag" =~ ^[A-Za-z0-9_][A-Za-z0-9._-]{0,127}$ ]]; then
      echo "::error::invalid OCI tag: $tag" >&2
      exit 1
    fi
  done
  # Demonstrate argument boundaries; the action passes these to update-index.py.
  printf '<%s>\n' --tags "${tag_args[@]}"
```

`read -r` preserves backslashes and `-a` creates an array. The quoted
`"${tag_args[@]}"` expands to one argument per element without pathname
expansion. In the action, `--tags "${tag_args[@]}"` supplies the multiple
arguments expected by argparse's `nargs="+"`. `--tags "$TAGS"` would pass one
combined string; `--tags $TAGS` would also allow pathname expansion. The
space-separated format does not support items containing spaces or shell quote
syntax, and `read` reads only one line. Use a structured format for richer lists.

Environment mapping also does not prevent a program from treating a value as an
option, path, or query. Validate values against the command's expected format
(as with the OCI tag check), and use `--` to end options where supported.

## Decide which values are trusted

Judge the source of a value, rather than the name of its context:

| Value | Treatment in a shell script |
|---|---|
| PR titles and bodies; issue or comment text | Attacker-controlled text. Always pass through `env:`. |
| Branch names, including PR head branches (`github.head_ref`) | An attacker can choose a branch name. Git's naming restrictions do not make it safe shell source. Use `env:`. |
| `workflow_call` and `workflow_dispatch` inputs | Caller-supplied data. Use `env:` even if today's caller passes a literal. |
| A `matrix` value selected from a fixed, reviewed list in the workflow | Safe to interpolate when every possible value is shell-safe (for example, `x86_64` and `aarch64`). A matrix built from inputs or job outputs does not inherit this trust. |
| `github.sha` | A GitHub-provided hexadecimal commit ID is safe to interpolate as a shell argument. This says nothing about whether that commit's code is trusted. |
| `runner.*` | GitHub-provided runner metadata is safe from attacker-supplied expression injection on a trusted runner. Still quote paths such as `runner.temp`; use `env:` for consistent argument handling. |

Prefer `env:` for data even when direct interpolation is safe today. A later
change to a caller or matrix source should not silently turn data into code.
For GitHub's recommended environment-variable pattern, see the
[secure use reference](https://docs.github.com/en/actions/reference/security/secure-use#use-an-intermediate-environment-variable).
