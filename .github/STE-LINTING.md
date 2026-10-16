# STE Linting — Simplified Technical English for TunaOS Documentation

TunaOS uses [ASD-STE100](https://asd-ste100.org/) (Simplified Technical English) linting to ensure documentation is clear, concise, and accessible to a global audience.

## What is Simplified Technical English?

Simplified Technical English is an international technical writing standard that emphasizes clarity and consistency through controlled language rules. Key principles:

- **Short sentences** — 20 words maximum for procedural text, 25 for descriptive
- **Active voice** — preferred over passive ("we recommend" vs. "it is recommended")
- **Approved vocabulary** — common, unambiguous words; industry-specific terms when necessary
- **No complex noun clusters** — no more than three words strung together without hyphens or conjunctions
- **Bounded paragraphs** — no more than 6 sentences per paragraph

These rules reduce cognitive load for non-native English readers and improve clarity for everyone.

## Why TunaOS uses STE

TunaOS documentation reaches a global audience: users, contributors, and maintainers across many countries and language backgrounds. STE linting:

- Catches clarity issues early in the review process
- Prevents the most common sources of confusion (ambiguous pronouns, passive voice, jargon)
- Serves as a style guide without requiring maintainers to be professional editors
- Catches issues automatically, freeing reviewers to focus on substance

## Getting Started: Adding STE Linting to Your Repo

### Step 1: Add the Reusable Workflow

Create `.github/workflows/ste.yml` in your repository:

```yaml
name: STE Lint

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
      budget: "0"
```

### Step 2: Seed the Budget

The first time you run STE linting, your repo likely has many existing findings. Rather than fail the workflow on day one, you "seed" the budget with the current count and then ratchet it down over time.

**Option A: Seed from existing prose**

Clone the `.github` repo (if you haven't already) and run the linter on your repo:

```bash
# From within your repo's checkout:
node /path/to/tuna-os/.github/.github/actions/ste-lint/ste-lint.mjs --summary
```

This prints the total finding count. Commit that number as `.ste-budget`:

```bash
echo "247" > .ste-budget
git add .ste-budget
git commit -s -m "chore: seed STE prose linting budget"
git push
```

**Option B: Start fresh**

If your repo has minimal prose, seed with `0` in `.ste-budget` and improve over time.

### Step 3: Understanding Findings

When the linter reports violations, each one has:

- **File and line number** — where the issue is
- **Rule number** — a reference to ASD-STE100 (e.g., rule 6: "Prefer active voice")
- **Message** — what is wrong
- **Approved replacement** — where applicable (e.g., "use 'you' instead of 'one'")

Example output:

```
docs/README.md:12 [rule 6] Use active voice instead of passive.
Suggestion: "We check your prose against STE rules." instead of "Your prose is checked against STE rules."
```

### Step 4: Files Checked by Default

The linter checks these files automatically (if they exist):

- `README.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `CODE_OF_CONDUCT.md`
- `docs/` directory (all `.md` files)
- `blog/` directory (all `.md` files)

If your repo doesn't have these files, the linter still passes (it has nothing to check).

## Understanding the Ratchet Pattern

The budget is a "ratchet" — it only goes down, never up:

- **Today's budget:** 247 findings
- **You fix 5 findings** in a PR
- **New budget:** 242 findings
- **You cannot merge a PR that increases findings** — if your branch has 250 findings, it fails the check until you fix 8 more

This prevents regressions and incentivizes steady improvement without requiring perfection from day one.

### Example: Ratcheting Down

```
Week 1: Budget = 250, PRs = "good to land, under budget"
Week 2: Budget = 248, PR says "you added findings (now 252), fix them first"
  → Author fixes 4 findings → 248 findings → PR passes ✓
Week 3: Budget = 248, another PR fixes 3 → Budget = 245
...eventually → Budget = 0, all prose passing STE checks
```

## Common STE Violations and How to Fix Them

### Rule 1: Sentence Length

**Violation:** Sentence exceeds 20 words (procedural) or 25 words (descriptive).

**Offending text:** 
> "In order to configure the bootc system for a new installation, you will need to first understand the image selection process and then make a choice from the available options."

**Fix (split into multiple sentences):**
> "Configure the bootc system for a new installation. First, understand the image selection process. Then choose from the available options."

### Rule 2: Only Use Approved Words

**Violation:** Word is not on the STE approved list or is ambiguous.

**Offending text:** 
> "The system provides flexibility in choosing deployments."

**Fix (use simpler word):**
> "The system lets you choose deployments."

### Rule 3: Use Active Voice

**Violation:** Passive voice when active voice is clearer.

**Offending text:** 
> "Pull requests are reviewed by maintainers within 48 hours."

**Fix:**
> "Maintainers review pull requests within 48 hours."

### Rule 4: Avoid `-ing` Forms at Sentence Start

**Violation:** Gerund (verb + ing) at the start of a sentence.

**Offending text:** 
> "Installing the bootc image requires an EFI system."

**Fix:**
> "To install the bootc image, you need an EFI system."

### Rule 5: Limit Noun Clusters

**Violation:** More than three nouns in a row without conjunction or hyphen.

**Offending text:** 
> "The bootc system disk image verification script runs automatically."

**Fix (add hyphens or restructure):**
> "The bootc system disk-image verification script runs automatically."
>
> Or: "The verification script for bootc disk images runs automatically."

### Rule 6: Limit Paragraph Length

**Violation:** Paragraph exceeds 6 sentences.

**Fix:** Break into multiple paragraphs.

## Opting Files Out of STE Checks

In rare cases, a file must opt out of STE checks — for example, a published blog post (editing it to pass the linter rewrites the historical record), a quoted license (like the Contributor Covenant), or a bibliography.

**Opt out in the file itself** using an HTML comment with a reason:

```markdown
<!-- ste-exclude-reason: This is a verbatim quote from the Contributor Covenant -->

# Code of Conduct

> Contributor Covenant Code of Conduct...
```

A reason is required: it documents **why** the file is exempt, which prevents the opt-out list from becoming a place prose goes to be forgotten.

## Local Development: Running STE Locally

To check your prose locally before opening a PR:

```bash
# From your repo checkout, using the tuna-os/.github action:
node /path/to/tuna-os/.github/.github/actions/ste-lint/ste-lint.mjs --summary

# To see only findings you introduced (compared to origin/main):
node /path/to/tuna-os/.github/.github/actions/ste-lint/ste-lint.mjs --changed-only --base origin/main

# To see the budget and check if you're under it:
cat .ste-budget
```

If your repo uses `just` for task automation:

```bash
just ste         # Run local STE check
just ste-fix     # Fix STE issues (where auto-fix is available)
```

## Troubleshooting

### "STE budget exceeded: 251 > 250"

Your branch has more STE findings than the budget allows. To fix:

1. Run the linter locally to see which findings are new to your branch
2. Edit the offending sentences to comply with STE rules (see examples above)
3. Commit and push; the workflow re-runs and checks again

### "I disagree with this finding"

STE rules can sometimes conflict with clarity or style preferences. If a rule seems wrong:

1. Open an issue in [tuna-os/.github](https://github.com/tuna-os/.github) describing why
2. Temporarily opt out the file with a reason comment (see "Opting Files Out" above)
3. Work with maintainers to decide whether the rule should be reconsidered org-wide

### "How do I see what changed in my PR?"

On a pull request, the STE linter posts an advisory annotation showing **only the findings introduced by your branch**. This helps you focus on what you added, not historical debt. The budget gate is based on the total, but the PR comment shows your delta.

## Improving Your Repo's STE Score

1. **Start with the easiest wins** — sentence length violations are quick to fix by splitting sentences
2. **Use active voice** — almost always clearer; make it a habit
3. **Read prose aloud** — catches awkward phrasing that the linter might not flag
4. **Involve contributors** — make STE improvements a good-first-issue or community contribution (link to this guide)
5. **Batch fixes** — group STE-only PRs together to avoid review fatigue

## Reference

- **ASD-STE100:** https://asd-ste100.org/
- **STE Linting Action:** `.github/actions/ste-lint/README.md` in [tuna-os/.github](https://github.com/tuna-os/.github)
- **Reusable Workflow:** `.github/workflows/ste-lint.yml` in [tuna-os/.github](https://github.com/tuna-os/.github)
- **Examples:** Most TunaOS application READMEs pass STE checks; see [gtk-office-suite](https://github.com/tuna-os/gtk-office-suite/blob/main/README.md), [mariner](https://github.com/tuna-os/mariner/blob/main/README.md), or [Tavern](https://github.com/tuna-os/Tavern/blob/main/README.md)

## Questions?

Ask in the [tuna-os/.github](https://github.com/tuna-os/.github) repository or in the TunaOS community channels.
