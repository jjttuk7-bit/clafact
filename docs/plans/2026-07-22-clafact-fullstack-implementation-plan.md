# ClaFact Full-Stack Service Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `news_data → HCX → KOSIS → deterministic Verdict → human review`를 실제 팀용 웹서비스로 운영한다.

**Architecture:** 기존 Python ClaFact 엔진을 FastAPI의 도메인 서비스와 Python Worker에서 재사용한다. Next.js는 작업대·Claim·Evidence·Verdict·리뷰 화면을 제공하고, PostgreSQL은 서비스 상태를, Redis는 비동기 작업을, S3 호환 저장소는 원문·snapshot·리포트를 보존한다.

**Tech Stack:** Python 3.10+, FastAPI, Pydantic, PostgreSQL, Redis, Next.js, TypeScript, Docker, pytest, Playwright

---

### Task 1: Freeze current engine contract

**Files:**
- Inspect: `clafact/pipeline/run.py`
- Inspect: `clafact/pipeline/detect.py`
- Inspect: `clafact/pipeline/parse.py`
- Inspect: `clafact/pipeline/retrieve.py`
- Inspect: `clafact/pipeline/verdict.py`
- Inspect: `clafact/kosis.py`
- Inspect: `clafact/service/store.py`
- Test: `tests/test_run.py`, `tests/test_service.py`, `tests/test_verdict.py`

**Steps:**
1. Define typed boundaries for Article, Claim, Evidence, Verdict, Review, and Run.
2. Add contract tests proving deterministic Verdict output for identical inputs.
3. Add a contract test proving HCX output is never accepted as the final Verdict.
4. Commit: `test: freeze pipeline service contracts`.

### Task 2: Add production configuration and secrets boundary

**Files:**
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/secrets.py`
- Modify: `.env.example`
- Test: `tests/test_config.py`

**Steps:**
1. Define environment settings for HCX, KOSIS, PostgreSQL, Redis, object storage, and allowed origins.
2. Fail fast when production secrets are missing.
3. Ensure secrets are never included in structured logs or response models.
4. Run: `pytest tests/test_config.py -q`.

### Task 3: Create persistent service schema

**Files:**
- Create: `backend/app/db/models.py`
- Create: `backend/app/db/migrations/`
- Create: `backend/app/repositories/`
- Test: `tests/test_persistence.py`

**Steps:**
1. Model organizations, users, memberships, articles, claims, evidence, verdicts, reviews, runs, and audit events.
2. Add idempotency keys for article ingestion and run creation.
3. Add indexes for review queue, article status, run status, and organization scope.
4. Run persistence tests against a disposable PostgreSQL database.

### Task 4: Import `news_data` into the service

**Files:**
- Create: `backend/app/ingest/news_data_loader.py`
- Modify: `clafact/pipeline/ingest.py`
- Create: `scripts/import_news_data.py`
- Test: `tests/test_news_data_import.py`

**Steps:**
1. Parse the existing dataset without changing the original files.
2. Store stable article IDs using URL or content hash.
3. Make repeated imports idempotent.
4. Record an import Run with counts and failures.

### Task 5: Build HCX adapter and structured-output validation

**Files:**
- Create: `backend/app/integrations/hcx_client.py`
- Create: `backend/app/schemas/hcx.py`
- Modify: `clafact/llm.py`
- Test: `tests/test_hcx_adapter.py`

**Steps:**
1. Implement timeout, retry, request ID, budget, and error classification.
2. Validate HCX JSON against ClaimType and ClaimExtraction schemas.
3. Reject missing or extra critical fields instead of guessing.
4. Store only redacted request metadata and structured output.

### Task 6: Build KOSIS adapter for live evidence retrieval

**Files:**
- Modify: `clafact/kosis.py`
- Create: `backend/app/integrations/kosis_service.py`
- Create: `backend/app/cache/kosis_cache.py`
- Test: `tests/test_kosis_service.py`

**Steps:**
1. Wrap `HttpKosisClient` with rate limiting, budget, caching, and circuit-breaker behavior.
2. Store table candidates, selected table, query parameters, values, source citation, and retrieval time.
3. Return an explicit `NO_MATCH` or `DEFINITION_UNCLEAR` result when evidence is insufficient.
4. Run fixture tests before live API tests.

### Task 7: Implement Redis worker orchestration

**Files:**
- Create: `backend/worker/tasks.py`
- Create: `backend/worker/pipeline_job.py`
- Create: `backend/app/services/run_service.py`
- Test: `tests/test_worker_pipeline.py`

**Steps:**
1. Create a run state machine for the nine pipeline stages.
2. Execute one Claim as an isolated unit inside an Article Run.
3. Retry only transient HCX/KOSIS/network failures.
4. Persist stage progress and failure reasons.
5. Verify that one failed Claim does not fail the whole Article Run.

### Task 8: Expose FastAPI endpoints

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/api/v1/articles.py`
- Create: `backend/app/api/v1/runs.py`
- Create: `backend/app/api/v1/claims.py`
- Create: `backend/app/api/v1/reviews.py`
- Create: `backend/app/api/v1/reports.py`
- Test: `tests/api/test_api_contract.py`

**Steps:**
1. Add organization-scoped article, run, claim, review, report, and operations endpoints.
2. Return stable status codes and typed error responses.
3. Add polling endpoint first; add WebSocket/SSE only after polling works.
4. Publish OpenAPI schema for the frontend.

### Task 9: Add authentication and role authorization

**Files:**
- Create: `backend/app/auth/`
- Create: `backend/app/permissions.py`
- Test: `tests/api/test_authorization.py`

**Steps:**
1. Add organization membership and roles: admin, reviewer, analyst, viewer.
2. Restrict reviews and release actions to reviewers/admins.
3. Restrict data and reports by organization ID.
4. Add audit events for login, review, release, and data export.

### Task 10: Build Next.js workbench

**Files:**
- Create: `web/`
- Create: `web/app/articles/page.tsx`
- Create: `web/app/articles/[id]/page.tsx`
- Create: `web/app/runs/[id]/page.tsx`
- Create: `web/app/review/page.tsx`
- Create: `web/app/reports/[id]/page.tsx`
- Test: `web/e2e/workbench.spec.ts`

**Steps:**
1. Build the article workbench and run launcher.
2. Build a nine-stage progress timeline.
3. Build Claim, KOSIS Evidence, Verdict, and Review panels.
4. Add reviewer approve/correct/reject actions with confirmation and optimistic UI disabled until API success.
5. Add responsive and keyboard-accessible navigation.

### Task 11: Add Agent operations dashboard

**Files:**
- Create: `backend/app/api/v1/ops.py`
- Create: `web/app/ops/page.tsx`
- Modify: `ops/ROLE_CHECKLIST.md`
- Test: `tests/api/test_ops_summary.py`, `web/e2e/ops.spec.ts`

**Steps:**
1. Show run failures, API budgets, review queue, Daily Logs, Backlogs, and release gate state.
2. Generate a morning briefing from official GitHub documents and persisted run data.
3. Never let the Agent change human golden labels or publish an unreviewed high-risk Verdict.

### Task 12: Add observability and production safeguards

**Files:**
- Create: `backend/app/observability/`
- Modify: `Dockerfile`
- Modify: `render.yaml`
- Create: `.github/workflows/service.yml`
- Test: `tests/test_observability.py`

**Steps:**
1. Add structured logs keyed by organization, run, claim, and request ID.
2. Add health, readiness, worker heartbeat, and dependency checks.
3. Add secret scanning, migration checks, unit tests, API contract tests, and E2E tests to CI.
4. Add database backup and object-storage retention policies.

### Task 13: Validate Phase 1 with real data

**Files:**
- Create: `docs/operations/phase-1-live-validation.md`
- Create: `reports/live_service/`
- Test: `tests/live/` (explicit opt-in only)

**Steps:**
1. Run a small approved sample from `news_data` with HCX and KOSIS keys server-side.
2. Record latency, API calls, cache hits, failures, Claim coverage, mapping coverage, Verdict distribution, and review workload.
3. Confirm no secret appears in logs, database, reports, or browser responses.
4. Gate expansion to larger batches on R1 approval.

### Task 14: Commit and release incrementally

**Steps:**
1. Commit each task after its tests pass.
2. Deploy a staging environment before production.
3. Run a reviewer-only pilot with a small team.
4. Promote only after Phase 1 completion criteria in the design document are met.
