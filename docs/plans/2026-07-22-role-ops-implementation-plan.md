# ClaFact Role Operations Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** PDF 기준의 역할별 Daily Log·Backlog·특수 문서 운영체계를 `ops/10_roles/`에 구축한다.

**Architecture:** 역할별 폴더를 독립적인 책임 경계로 두고, 공통 문서 템플릿과 역할별 정책 문서를 함께 둔다. `PROJECT_STATE.md`와 `DOCUMENT_INDEX.md`는 전체 상태와 공식 문서 색인의 기준으로 유지한다.

**Tech Stack:** Markdown, Git

---

### Task 1: Create role directories and templates

**Files:**
- Create: `ops/10_roles/R1_PM_Evaluation/{README.md,backlog.md,decisions.md,daily/2026-07-22.md}`
- Create: `ops/10_roles/R2_Claim/{README.md,backlog.md,rules.md,daily/2026-07-22.md}`
- Create: `ops/10_roles/R3_Evidence/{README.md,backlog.md,mappings.md,daily/2026-07-22.md}`
- Create: `ops/10_roles/R4_Verdict_Service/{README.md,backlog.md,verdict_policy.md,daily/2026-07-22.md}`
- Create: `ops/10_roles/R5_Hermes_Agent/{README.md,backlog.md,automation.md,daily/2026-07-22.md}`

**Steps:**
1. Add the five role charters, five backlog files, five daily templates, and five special documents.
2. Keep sensitive values out of all templates and state that Daily Logs do not make official decisions.

### Task 2: Register the workflow

**Files:**
- Create: `ops/DECISION_LOG.md`
- Modify: `ops/DOCUMENT_INDEX.md`
- Modify: `ops/PROJECT_STATE.md`

**Steps:**
1. Record the approved introduction of `ops/10_roles/` as a decision.
2. Register the role documents and update next actions.

### Task 3: Verify and publish

**Steps:**
1. Check that all required paths exist and every Markdown document has metadata.
2. Inspect `git diff --check` and the complete diff.
3. Commit with `docs(ops): add role-based daily log workflow`.
4. Push `main` to `origin/main`.
