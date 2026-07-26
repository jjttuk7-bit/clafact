# 하이브리드 불일치 연구 자산 Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Python과 HCX의 네 불일치 유형 및 HCX 오류를 누적 저장·검토·내보내기 가능한 연구 자산으로 만든다.

**Architecture:** 기존 `run_comparison` 결과에서 문장별 유형을 결정하고, 운영 DB와 분리된 SQLite 저장소에 append-only로 기록한다. 사람 승인 사례만 기존 골든셋 계층의 별도 JSONL로 승격하며 Streamlit은 집계·필터·CSV를 제공한다.

**Tech Stack:** Python 3, sqlite3, dataclasses, csv, json, pytest, Streamlit.

---

### Task 1: 불일치 분류 계약

**Files:**
- Create: `clafact/experiment_analysis.py`
- Create: `tests/test_experiment_analysis.py`

1. `P+/H+`, `P+/H-`, `P-/H+`, `P-/H-`, `HCX_ERROR` 각각의 실패 테스트를 작성한다.
2. 테스트를 실행해 모듈 부재로 실패하는지 확인한다.
3. `classify_disagreement(python_candidate, hcx_candidate, hcx_status)`를 최소 구현한다.
4. 모든 분류 테스트와 합계 불변식 테스트를 통과시킨다.

### Task 2: 연구용 SQLite 저장소

**Files:**
- Create: `clafact/experiment_store.py`
- Create: `tests/test_experiment_store.py`
- Modify: `.gitignore`

1. 메모리 SQLite에 실행·문장 결과를 저장하고 다시 읽는 실패 테스트를 작성한다.
2. `experiment_runs`, `experiment_sentences` 스키마와 append-only 저장 API를 구현한다.
3. 동일 실행 재저장, HCX 오류, 사람 검토 라벨 테스트를 추가한다.
4. `data/research/`를 Git 제외 경로로 추가한다.

### Task 3: 전체 비교 결과 연결

**Files:**
- Modify: `clafact/experiment_lab.py`
- Modify: `clafact/experiment_modes.py`
- Modify: `tests/test_experiment_lab.py`

1. `ComparisonRow`가 HCX 실행 상태와 불일치 유형을 보존하는 실패 테스트를 작성한다.
2. 전체 비교에서만 Python·HCX 독립 결과를 분류하고 집계한다.
3. HCX 오류가 `P+/H-`나 `P-/H-`에 섞이지 않는지 검증한다.

### Task 4: 실험실 집계·필터 UI

**Files:**
- Modify: `streamlit_app.py`
- Modify: `tests/test_experiment_lab_ui.py`

1. 다섯 집계 카드, 유형 필터, 오류 분리 표시에 대한 UI 계약 테스트를 작성한다.
2. 현재 실행의 유형별 건수·비율·대표 문장을 표시한다.
3. 연구 이력 저장은 명시적 `연구 이력 저장` 버튼에서만 수행한다.
4. 운영 `Store`를 사용하지 않는 기존 안전 계약을 유지한다.

### Task 5: CSV와 골든셋 승인

**Files:**
- Create: `clafact/experiment_export.py`
- Create: `tests/test_experiment_export.py`
- Modify: `streamlit_app.py`

1. 선택한 실행을 UTF-8 BOM CSV로 내보내는 실패 테스트를 작성한다.
2. 승인된 문장만 `hybrid_disagreements_v0.jsonl` 행으로 만드는 테스트를 작성한다.
3. `true_candidate`, `false_positive`, `hold` 검토 상태와 중복 방지를 구현한다.
4. 다운로드와 승인 UI를 연결한다.

### Task 6: 평가 지표와 문제 원장

**Files:**
- Modify: `docs/VERIFICATION_LAB_ISSUE_LEDGER.md`
- Modify: `tests/test_experiment_analysis.py`

1. 사람 검토 완료 집합에서만 정밀도·재현율을 계산하는 테스트를 작성한다.
2. Python, HCX, `Python OR HCX` 지표와 HCX 정상 응답률을 구현한다.
3. VLAB-012/013에 구현 커밋과 검증 결과를 기록한다.
4. 관련 테스트, `py_compile`, `git diff --check`를 실행한다.
