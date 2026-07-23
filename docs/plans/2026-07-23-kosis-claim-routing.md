# KOSIS Claim Routing Implementation Plan

| 항목 | 내용 |
|---|---|
| Author | ClaFact Hermes Agent |
| Reviewed by | Human Team |
| Managed by | ClaFact Hermes Agent |
| Status | Draft |
| Version | v0.1 |
| Last Updated | 2026-07-23 |

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 업로드된 수치 Claim을 출처·검증 가능성으로 분류해 KOSIS 가능 Claim만 검증 큐로 보내고, 나머지는 분류 결과로 보존한다.

**Architecture:** `source_classify.classify()`의 8개 라벨과 route를 Claim 저장소의 1급 필드로 저장한다. `KOSIS_RETRIEVAL` route만 `PENDING` 상태로 큐잉하며, 나머지는 `CLASSIFIED` 상태로 보존한다. 기존 SQLite DB에는 안전한 `ALTER TABLE` 마이그레이션을 적용한다.

**Tech Stack:** Python 3.11, SQLite stdlib, Streamlit, pytest.

---

### Task 1: 저장소 분류 필드와 마이그레이션

**Files:**
- Modify: `clafact/service/store.py`
- Test: `tests/test_service.py`

1. `claims`에 `source_type`, `claim_type`, `route`, `classification_reason`을 추가한다.
2. 기존 DB를 열 때 누락 열을 `ALTER TABLE`로 추가한다.
3. `enqueue_claim()`이 분류 데이터를 저장하도록 확장한다.
4. 테스트: KOSIS·비KOSIS Claim의 분류와 상태가 저장되는지 검증한다.

### Task 2: 업로드 단계 라우팅

**Files:**
- Modify: `backend/app/ingest_service.py`
- Test: `tests/test_ingest_observability.py`

1. 후보 문장마다 `source_classify.classify()`를 호출한다.
2. KOSIS route만 `PENDING`, 나머지는 `CLASSIFIED`로 저장한다.
3. 응답에 source type·route별 건수, KOSIS 대기 건수, 분류 보존 건수를 추가한다.
4. 테스트: 국내 소비자물가는 큐잉되고, 수출·환율·해외·전망 문장은 분류만 저장되는지 검증한다.

### Task 3: 운영·검증 화면 연결

**Files:**
- Modify: `streamlit_app.py`
- Test: `tests/test_upload_scoped_dashboard.py`

1. 운영 홈에 KOSIS 검증 대기와 비검증 분류 결과 수를 분리해 표시한다.
2. 이번 업로드 감사 로그에 분류·라우팅 사유를 표시한다.
3. 검증 탭은 `route=KOSIS_RETRIEVAL` Claim만 기본 대상으로 조회한다.
4. 분류 결과 탭/영역에서 비KOSIS·범위 밖·사람 검토 수를 집계한다.

### Task 4: 검증

1. 새 테스트를 먼저 실패시키고 구현 후 통과시킨다.
2. `python -m py_compile streamlit_app.py backend/app/ingest_service.py clafact/service/store.py`를 실행한다.
3. `python -m pytest -q` 전체 회귀를 실행한다.
4. 검증된 코드·테스트만 커밋한다.