# 검증 실험실 CSV 기사 선택 구현 계획

| 항목 | 내용 |
|---|---|
| Author | Human Team + ClaFact Hermes Agent |
| Reviewed by | Human Team |
| Managed by | ClaFact Hermes Agent |
| Status | Draft |
| Version | v0.1 |
| Last Updated | 2026-07-26 |

> **For Claude:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task.

**Goal:** 검증 실험실에서 기존 기사 CSV를 임시·읽기 전용으로 업로드하고, 사용자가 선택한 기사 한 건만 세 방식으로 비교한다.

**Architecture:** `streamlit_app.py`의 검증 실험실 블록이 업로드 바이트를 `csv.DictReader`로 읽어 기존 본문·제목·작성일 별칭을 해석한다. 유효 본문 행은 세션에만 보관하며 선택된 행의 본문과 작성일만 기존 `run_comparison`으로 전달한다. `Store`, `process_pending`, KOSIS 검증은 호출하지 않는다.

**Tech Stack:** Python 표준 라이브러리 (`csv`, `io`), Streamlit, pytest.

---

### Task 1: CSV 선택 UI 계약 테스트

**Files:**
- Modify: `tests/test_experiment_lab_ui.py`

**Step 1:** `검증 실험실 CSV 파일` 업로더, `experiment_lab_csv`, `csv.DictReader`, `기사 선택`, `Store` 미포함을 검증하는 테스트를 추가한다.

**Step 2:** `python -m pytest tests/test_experiment_lab_ui.py -q`를 실행해 현재 코드에서 해당 assertion이 실패하는지 확인한다.

### Task 2: CSV 읽기와 단일 기사 선택

**Files:**
- Modify: `streamlit_app.py:713-741`

**Step 1:** 업로드 CSV를 UTF-8 BOM으로 디코딩하고 `csv.DictReader`로 읽는다. `body`, `본문`, `content`, `text` 중 첫 유효 본문을 사용하며, `title`/`제목`과 `date`/`작성일`은 선택 표시용으로 읽는다.

**Step 2:** 유효 기사 수와 1,000건 이상도 자동 실행하지 않는 안내를 표시한다. 최대 1,000개 선택지에서 기사 제목·작성일·행 번호를 선택할 수 있게 한다.

**Step 3:** 선택한 CSV 기사의 본문과 작성일을 기존 비교 실행 버튼에 연결한다. 직접 입력은 그대로 유지하고, CSV 선택 기사가 있으면 해당 기사를 우선 사용한다.

**Step 4:** 동일 테스트를 다시 실행해 통과를 확인한다.

### Task 3: 회귀 검증과 커밋

