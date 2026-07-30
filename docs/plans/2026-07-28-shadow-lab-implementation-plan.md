# Shadow Lab Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 운영 판정에 영향을 주지 않는 Shadow Lab을 기존 검증 실험실에 추가해 정책 기반 병렬 실행, 충돌 검토, 자동 저장, CSV·JSONL·Markdown 내보내기를 제공한다.

**Architecture:** 기존 `ExperimentStore`는 Python/HCX 탐지 비교에 특화돼 있으므로 변경하지 않는다. Shadow Lab은 `data/research/shadow_lab.db`의 연구 전용 SQLite 저장소와 별도 정책·실행 모델을 사용하며, 현재 `run_comparison()`을 첫 비교 실행기로 감싼다. Streamlit의 기존 검증 실험실에 탭으로 연결하고 운영 `Store`에는 절대 쓰지 않는다.

**Tech Stack:** Python 3, dataclasses, SQLite(stdlib), Streamlit, pytest.

---

| 항목 | 내용 |
| --- | --- |
| Author | Human Team + Codex |
| Reviewed by | Human Team |
| Managed by | Codex |
| Status | Draft |
| Version | v0.1 |
| Last Updated | 2026-07-28 |

## 안전 원칙

- 운영 `clafact/service/store.py`, 운영 claim 상태, 운영 리뷰 큐는 수정하지 않는다.
- 기존 `ExperimentStore`의 테이블·행 형식은 수정하지 않는다.
- 새 결과는 `data/research/shadow_lab.db`에만 기록한다.
- 첫 구현은 정책·문장 분석 방법 비교·검토·기록까지만 다룬다. KOSIS 값 조회·최종 판정은 다음 단계다.
- 각 Task 뒤 `docs/SHADOW_LAB_CHANGELOG.md`에 변경 ID, 영향, 테스트, 롤백 방법을 기록한다.

### Task 1: 정책 모델

**Files:**

- Create: `clafact/shadow_policy.py`
- Test: `tests/test_shadow_policy.py`
- Modify: `docs/SHADOW_LAB_CHANGELOG.md`

**Step 1: Write the failing tests**

`ShadowPolicy.default()`가 인구·KOSIS·판단 보류 정책을 반환하고, 알 수 없는 claim type을 거부하는지 테스트한다.

```python
from clafact.shadow_policy import ShadowPolicy

def test_default_policy_is_review_safe():
    policy = ShadowPolicy.default()
    assert policy.domain == "population"
    assert policy.evidence_source == "KOSIS"
    assert policy.default_when_uncertain == "insufficient_evidence"

def test_policy_rejects_unknown_claim_type():
    with pytest.raises(ValueError):
        ShadowPolicy(claim_types=("unknown",))
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_shadow_policy.py -v`
Expected: FAIL because `clafact.shadow_policy` does not exist.

**Step 3: Write minimal implementation**

- immutable `ShadowPolicy` dataclass를 만들고 domain, evidence_source, claim_types, default_when_uncertain, review_when, version을 저장한다.
- 허용 claim type·판정 상태를 검증한다.
- `default()`, `as_dict()`, `from_dict()`를 제공한다.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_shadow_policy.py -v`
Expected: PASS.

**Step 5: Record**

`CHG-SHADOW-002`에 연구 전용 정책 모델임을 기록한다.

### Task 2: 연구 전용 Shadow 저장소

**Files:**

- Create: `clafact/shadow_store.py`
- Test: `tests/test_shadow_store.py`
- Modify: `docs/SHADOW_LAB_CHANGELOG.md`

**Step 1: Write the failing tests**

실행·문장 행·검토 결과가 별도 DB에 저장되고, 동일 run ID의 다른 payload를 거부하는지 테스트한다.

```python
from clafact.shadow_store import ShadowStore

def test_store_persists_reviewable_row(tmp_path):
    with ShadowStore(tmp_path / "shadow_lab.db") as store:
        assert store.append_run(
            {"run_id": "shadow-1", "created_at": "t", "input_hash": "h", "policy_json": "{}", "status": "completed"},
            [{"row_index": 1, "sentence": "인구는 감소했다.", "baseline_json": "{}", "shadow_json": "{}", "review_state": "needs_review", "risk_reasons_json": "[\"candidate_conflict\"]"}],
        ) is True
        assert store.list_review_rows("shadow-1")[0]["sentence"] == "인구는 감소했다."
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_shadow_store.py -v`
Expected: FAIL because `ShadowStore` does not exist.

**Step 3: Write minimal implementation**

- `shadow_runs`, `shadow_rows`, `shadow_reviews` SQLite 테이블을 만든다.
- run에는 정책 JSON, 입력 해시, 방법 이름, 상태, 요약 JSON을 저장한다.
- row에는 baseline/shadow JSON, 위험 사유, 검토 상태를 저장한다.
- review는 `approve`, `correct`, `hold`와 메모·시각을 append-only로 저장한다.
- `list_review_rows()`는 `needs_review` 행만 위험도 순으로 반환한다.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_shadow_store.py -v`
Expected: PASS.

**Step 5: Record**

`CHG-SHADOW-003`에 DB 격리와 운영 영향 없음을 기록한다.

### Task 3: 기존 비교 엔진을 감싼 Shadow Runner

**Files:**

- Create: `clafact/shadow_runner.py`
- Test: `tests/test_shadow_runner.py`
- Modify: `docs/SHADOW_LAB_CHANGELOG.md`

**Step 1: Write the failing test**

고정 judge를 주입했을 때 기존 Python 결과와 LLM 결과 충돌이 `candidate_conflict` 검토 사유로 변환되는지 테스트한다.

```python
from clafact.shadow_policy import ShadowPolicy
from clafact.shadow_runner import run_shadow_experiment

def test_runner_marks_candidate_conflict_for_review():
    result = run_shadow_experiment(
        text="지난해 실업률은 2.7%였다.",
        article_date="2026-07-28",
        policy=ShadowPolicy.default(),
        judge_fn=lambda sentence: (False, "LLM 미탐지"),
    )
    assert any("candidate_conflict" in row.risk_reasons for row in result.rows)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_shadow_runner.py -v`
Expected: FAIL because `run_shadow_experiment` does not exist.

**Step 3: Write minimal implementation**

- 현재 `clafact.experiment_modes.run_comparison()`을 호출한다.
- baseline은 Python, shadow는 HCX/Hybrid 비교 결과로 저장한다.
- 각 행에 문장, 수치, 기간, 주장 유형, 기존/Shadow 결과, 위험 사유를 만든다.
- 위험 사유는 `candidate_conflict`, `llm_error`, `required_slot_missing`, `ambiguous_time_or_unit`을 지원한다.
- 불확실 사례는 자동 판정 대신 `needs_review` 또는 `hold`로 둔다.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_shadow_runner.py -v`
Expected: PASS.

**Step 5: Record**

`CHG-SHADOW-004`에 baseline/shadow 정의와 운영 파이프라인 미변경을 기록한다.

### Task 4: 실행 저장과 검토 서비스

**Files:**

- Create: `clafact/shadow_service.py`
- Test: `tests/test_shadow_service.py`
- Modify: `docs/SHADOW_LAB_CHANGELOG.md`

**Step 1: Write the failing test**

서비스 실행 결과가 ShadowStore에 저장되고, `hold` 검토가 운영 Store 대신 연구 DB에만 저장되는지 테스트한다.

```python
def test_review_is_saved_only_in_shadow_store(tmp_path):
    service = ShadowService(tmp_path / "shadow_lab.db")
    run_id = service.run_and_save(
        text="지난해 실업률은 2.7%였다.", article_date="2026-07-28",
        policy=ShadowPolicy.default(), judge_fn=lambda sentence: (False, "LLM 미탐지"),
    )
    assert service.apply_review(run_id, 1, action="hold", note="기간 확인 필요") is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_shadow_service.py -v`
Expected: FAIL because `ShadowService` does not exist.

**Step 3: Write minimal implementation**

- 입력 해시·실행 ID를 생성해 Runner 결과를 저장한다.
- 빈 입력과 정책 검증 실패는 저장하지 않는다.
- 검토 행동은 허용 행동만 받으며, Phase 0에서는 운영 골든셋으로 승격하지 않는다.
- Streamlit에 종속되지 않는 서비스 API로 만든다.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_shadow_service.py -v`
Expected: PASS.

**Step 5: Record**

`CHG-SHADOW-005`에 연구 검토 격리를 기록한다.

### Task 5: 결과 내보내기

**Files:**

- Create: `clafact/shadow_export.py`
- Test: `tests/test_shadow_export.py`
- Modify: `docs/SHADOW_LAB_CHANGELOG.md`

**Step 1: Write the failing tests**

저장 실행에서 CSV·JSONL·Markdown을 만들 때 정책, 실행 ID, 문장별 결과, 위험 사유, 검토 상태가 포함되는지 테스트한다.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_shadow_export.py -v`
Expected: FAIL because export functions do not exist.

**Step 3: Write minimal implementation**

- CSV는 Excel 안전 UTF-8 BOM으로 만든다.
- JSONL은 run metadata와 row를 구분하는 `record_type`을 포함한다.
- Markdown은 실행 요약, 정책, 방법, 검토 필요 사례, 전체 행을 포함한다.
- 운영 DB 데이터·비밀 설정값은 내보내지 않는다.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_shadow_export.py -v`
Expected: PASS.

**Step 5: Record**

`CHG-SHADOW-006`에 다운로드 형식과 데이터 노출 범위를 기록한다.

### Task 6: 검증 실험실의 Shadow Lab 탭

**Files:**

- Modify: `streamlit_app.py:789` (기존 `if view == "검증 실험실"` 블록)
- Test: `tests/test_shadow_lab_ui.py`
- Modify: `docs/SHADOW_LAB_CHANGELOG.md`

**Step 1: Write the failing UI contract test**

```python
def test_verification_lab_includes_shadow_controls(app_source):
    assert "Shadow Lab" in app_source
    assert "Shadow 실험 실행" in app_source
    assert "운영 결과는 변경되지 않습니다" in app_source
    assert "Shadow 결과 CSV" in app_source
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_shadow_lab_ui.py -v`
Expected: FAIL because controls do not exist.

**Step 3: Write minimal implementation**

- 기존 검증 실험실을 `기존 방식 비교`와 `Shadow Lab` 탭으로 나눈다. 기존 session key와 동작은 보존한다.
- Shadow 탭에는 기본 정책, 입력, `Shadow 실험 실행` 버튼, 상시 안전 안내를 표시한다.
- 실행 후 요약 지표, 비교 행, 검토 카드, CSV·JSONL·Markdown 다운로드 버튼을 표시한다.
- 기존 ExperimentStore의 저장·검토 버튼과 이름을 구분한다.

**Step 4: Run focused tests**

Run: `pytest tests/test_shadow_lab_ui.py tests/test_streamlit_theme_contract.py -v`
Expected: PASS.

**Step 5: Record**

`CHG-SHADOW-007`에 화면 추가와 기존 기능 보존을 기록한다.

### Task 7: 회귀 검증과 변경 기록

**Files:**

- Modify: `docs/SHADOW_LAB_CHANGELOG.md`
- Modify: `docs/plans/2026-07-28-shadow-lab-design.md`
- Test: `tests/test_shadow_*.py`

**Step 1: Run Shadow focused tests**

Run: `pytest tests/test_shadow_policy.py tests/test_shadow_store.py tests/test_shadow_runner.py tests/test_shadow_service.py tests/test_shadow_export.py tests/test_shadow_lab_ui.py -v`
Expected: PASS.

**Step 2: Run existing experiment regressions**

Run: `pytest tests/test_experiment_lab.py tests/test_experiment_store.py tests/test_experiment_review.py tests/test_experiment_export.py tests/test_streamlit_theme_contract.py -v`
Expected: PASS.

**Step 3: Manual verification**

1. `streamlit run streamlit_app.py`를 실행한다.
2. `검증 실험실 > Shadow Lab`에서 테스트 문장을 실행한다.
3. 실행 ID, 요약, 충돌 행, 검토 카드가 나타나는지 확인한다.
4. `hold` 검토를 저장하고 새로고침 후에도 유지되는지 확인한다.
5. CSV·JSONL·Markdown에 정책·행·검토 상태가 포함되는지 확인한다.
6. 운영 홈·검증·검증자 리뷰에 새 claim 또는 상태 변화가 없는지 확인한다.

**Step 4: Final documentation**

실제 수정 파일, 테스트 출력, 수동 검증 결과, 롤백 방법을 변경 이력에 추가한다. 설계 문서는 사람 승인 전까지 `Draft` 상태를 유지한다.

**Step 5: Commit only on request**

사용자가 명시적으로 요청한 경우에만 코드·테스트·문서를 커밋하며, 기존 사용자 미추적 파일은 포함하지 않는다.
