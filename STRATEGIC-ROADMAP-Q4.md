# TunaOS Strategic Roadmap — Q4 2026 Adoption Execution

**Last updated**: 2026-10-16  
**Maintained by**: strategist agent (ACMM L6)  
**Horizon**: Q4 2026 – Q1 2027

---

## Executive Summary

TunaOS enters Q4 with strong release momentum but blocked on five critical adoption-readiness decisions. This roadmap coordinates:

1. **Release-decision gates** (5 projects stalled 45–69 days)
2. **Infrastructure blockers** (workflows permission P0; merge queue clarification)
3. **Documentation & site reliability** (sync pipeline, metrics availability)
4. **Security hardening** (org-wide audit coordination)
5. **Distribution parity** (Flatpak, Homebrew, Scoop, native alignment)

---

## P0 Blockers (Unblock Immediately)

### 1. GitHub App Workflows Permission Missing (Infrastructure)

**Issue**: `tunaos#XXXX`

**Problem**: GitHub App has workflows:write in install config, but per-agent token (scanner tier) does NOT. Blocks 16+ agent-authored PRs touching `.github/workflows/`.

**Blocked PRs**:
- tunaos: security hardening (permissions blocks), lint gates, CI fixes
- flatpak-index: #144 (persist-credentials), #142 (ruff lint)
- xfce-linux: CI hardening

**Action**: Hive infrastructure team to regenerate scanner token OR define alternate merge path for workflow PRs.

**Owner**: infrastructure / hive-operator  
**Target**: ASAP (this week)

---

### 2. Five Release-Decision Gates (Adoption Blocker)

**Issue**: `tunaos#XXXX`

| Project | Gate | Stalled | Owner Decision |
|---------|------|---------|---|
| **wootc** | VM-first commitment + code-signing strategy | 5d | Maintainer (RC timing) |
| **bootc-installer-asahi** | Hardware capacity decision | 14d | Maintainer (alpha release) |
| **bootc-migrate** | Release owner + date (post-rename) | 69d | Maintainer (adoption unblocked) |
| **scoop-bucket** | Windows distribution launch gates | 45d | Maintainer (Windows onramp) |
| **finupdate** | v0.1.0 release timing | 14d | Maintainer (publication) |

**Impact**: All five are on the Q4 adoption-readiness critical path. Downstreams (flatpak-index, homebrew-tap, scoop-bucket) cannot version-lock or publish without these decisions.

**Action**: Maintainer responses in each issue (yes/no/defer). Strategist synthesizes into unified release timeline.

**Owner**: maintainers (decision), strategist (coordination)  
**Target**: end of Q4 week 1 (by Oct 20)

---

## P1 Near-term Blockers (Q4 Execution)

### 3. Documentation Sync Pipeline CI Failures

**Issue**: `docs#XXXX`

**Problem**: sync-org-docs workflow fails daily on MDX placeholder imports (#359). Blocks:
- Org ROADMAP.md not synced to tunaos.org/docs (stale guidance)
- Adoption metrics API unavailable on failed runs
- No link-validation gate (broken assets ship silently)

**Action**:
1. Root-cause and fix #359 (MDX imports)
2. Add pre-merge link-validation gate
3. Document sync model in CONTRIBUTING.md

**Owner**: guide / docs maintainers  
**Target**: by Oct 25 (adoption metrics needed for Q4 reporting)

---

### 4. Release Channel Parity (Tavern)

**Issue**: `Tavern#XXXX`

**Problem**: Tavern versions split across channels:
- Git tags: v0.1.57
- GitHub Releases: v0.1.9 (stale by 48 versions)
- Flatpak: v0.1.57+ (independent)
- Homebrew: v0.1.9 (cask stale by 55 versions)

**Impact**: Homebrew users stuck on old version; no single "current release" exists.

**Action**:
1. Backfill GitHub Release for v0.1.57
2. Update homebrew-tap cask to v0.1.57
3. Define release coordination contract (git tag → Releases → Flatpak → Homebrew)

**Owner**: maintainer (release decision) + release-engineering  
**Target**: by Oct 25

---

### 5. Security Hardening Coordination

**Issue**: `tunaos#XXXX`

**Gaps**:
- 20+ workflows without top-level permissions blocks
- 415 actions/checkout missing `persist-credentials: false`
- GITHUB_TOKEN piped to mutable 3rd-party actions
- No CI enforcement gate (hardening added after-the-fact)

**Action**:
1. Unblock workflows permission (P0 above)
2. Establish CI linting gate (fail if no permissions block)
3. Audit all workflows; apply principle of least privilege
4. Consolidate security scanning (semgrep + custom duplication)

**Owner**: sec-check + architect lanes (coordination)  
**Target**: Q4 (gate ready by Dec 1)

---

## Q4 Strategic Goals

### Goal 1: Unblock Q4 Adoption Execution
- [ ] Five release-decision gates resolved (wootc, bootc-installer-asahi, bootc-migrate, scoop-bucket, finupdate)
- [ ] Release coordination contract published (git tag → multi-channel publish pipeline)
- [ ] Homebrew/Flatpak/Scoop distribution parity confirmed

**Owner**: maintainers + release-engineering  
**Success measure**: All five projects have published releases; channel versions match

---

### Goal 2: Make Adoption Visible & Measurable
- [ ] Sync-org-docs CI green; canonical ROADMAP published at tunaos.org
- [ ] Adoption metrics API available (/api/adoption)
- [ ] Q4 adoption dashboard reports: download trends, variant distribution, channel parity
- [ ] Variant lifecycle status reflected in docs (EOL dates, support SLAs)

**Owner**: guide + observability team  
**Success measure**: adoption metrics dashboard live; historical trend available

---

### Goal 3: Security Hardening Baseline
- [ ] CI linting gate prevents workflows without top-level permissions blocks
- [ ] 20+ workflows audited and hardened (least-privilege permissions)
- [ ] Org-wide hardening policy published in root ROADMAP
- [ ] 415 actions/checkout references updated with `persist-credentials: false`

**Owner**: sec-check + architect lanes  
**Success measure**: 100% of workflows have top-level permissions; policy documented

---

### Goal 4: Foundation for Q1 Release Automation
- [ ] Release coordination contract finalized (git tag → all channels)
- [ ] Conventional Commits adopted (preparation for automated release notes)
- [ ] Multi-channel publication workflow validated (Tavern case study)
- [ ] Org ROADMAP includes versioning strategy + release SLA

**Owner**: release-engineering + strategist  
**Success measure**: Release contract template drafted; first project using automated pipeline

---

## Decision Points

### Q4 Week 1 (Oct 16–22)
- [ ] Five release-decision gates decided (wootc, bootc-installer-asahi, bootc-migrate, scoop-bucket, finupdate)
- [ ] Workflows permission blocker escalated and resolved
- [ ] Release coordination contract drafted

### Q4 Week 2–3 (Oct 23–Nov 5)
- [ ] sync-org-docs CI green; ROADMAP published
- [ ] Homebrew/Flatpak/Scoop parity confirmed
- [ ] Q4 adoption metrics dashboard published

### Q4 Week 4+ (Nov 6–Dec 31)
- [ ] Security hardening CI gate live
- [ ] Conventional Commits adoption pilot (1 project)
- [ ] Q4 exit review: adoption numbers, retention signals, Q1 planning

---

## Governance & Escalation

**Strategist role**: Coordinate across owners, synthesize decisions, flag stalls. This roadmap is the coordination checkpoint.

**Escalation path**: If an issue remains stalled > 48h without update:
1. Post a maintainer question with options (A/B/C)
2. If still stalled after 48h more, escalate to infrastructure/ownership team
3. If stalled > 7 days, file `needs-human` and defer to next quarter

**Review cadence**: Updated weekly (Friday EOD) through Q4. Monthly full review with maintainers.

---

## Related Issues & Tracking

**P0 Blockers**:
- `tunaos#XXXX` — Workflows permission missing
- `tunaos#XXXX` — Q4 adoption blocker: five release-decision gates

**P1 Execution**:
- `docs#XXXX` — Sync pipeline blocker (CI, metrics, ROADMAP)
- `Tavern#XXXX` — Release channel parity
- `tunaos#XXXX` — Security hardening coordination

**Related Roadmaps**:
- `.github#ROADMAP.md` — org-wide planning architecture
- `docs#ROADMAP.md` — documentation site Q4 goals
- `tunaos#ROADMAP.md` — primary project goals

---

*Maintained by strategist agent (ACMM L6). This artifact serves as the strategic coordination checkpoint for Q4 adoption execution across the TunaOS organization.*
