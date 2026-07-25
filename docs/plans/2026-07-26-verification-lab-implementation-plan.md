# 검증 실험실 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

| 항목 | 내용 |
|---|---|
| Author | Human Team + ClaFact Hermes Agent |
| Reviewed by | Human Team |
| Managed by | ClaFact Hermes Agent |
| Status | Draft |
| Version | v0.1 |
| Last Updated | 2026-07-26 |

**Goal:** 운영 DB와 완전히 분리된 Streamlit 검증 실험실에서 Python·LLM·하이브리드 수치 주장 탐지 결과를 비교한다.

**Architecture:** 순수 Python 서비스 함수가 기사 문장을 세 방식으로 분석해 비교 행을 반환한다. Streamlit은 그 결과만 `session_state`에 보관하고 렌더링하며, 운영 큐와 KOSIS 판정 흐름을 호출하지 않는다.

**Tech Stack:** Python 3.14, pytest, Streamlit, 기존 ClaFact 탐지/파싱/분류 모듈, 선택적 HCX LLM 클라이언트.

---

### Task 1: 비교 엔진의 실패 테스트 작성

**Files:**
- Create: `tests/test_experiment_lab.py`
- Create: `clafact/experiment_lab.py`

**Step 1:** Python 결과·LLM 결과·하이브리드 결과가 같은 문장 목록에 대해 생성되고, 실행 결과가 Store를 요구하지 않는다는 테스트를 작성한다.

**Step 2:** `pytest tests/test_experiment_lab.py -v`를 실행해 모듈 없음으로 실패함을 확인한다.

**Step 3:** 최소 비교 엔진을 구현한다. 주입 가능한 `judge` 함수를 받아 외부 LLM 없이도 테스트 가능하게 한다.

**Step 4:** 같은 pytest 명령으로 통과를 확인한다.

### Task 2: 하이브리드 보수 통과와 메타데이터 테스트

**Files:**
- Modify: `tests/test_experiment_lab.py`
- Modify: `clafact/experiment_lab.py`

**Step 1:** LLM이 비검증으로 판정하면 하이브리드 후보가 제외되고, LLM 예외는 Python 후보를 유지하며 사유를 남긴다는 실패 테스트를 추가한다.

**Step 2:** 테스트가 실패함을 확인한다.

**Step 3:** LLM 호출 수·경과시간·Python 파싱/라우팅 메타데이터를 포함하도록 구현한다.

**Step 4:** 테스트를 통과시킨다.

### Task 3: Streamlit 검증 실험실 화면 추가

**Files:**
- Modify: `streamlit_app.py`
- Test: `tests/test_experiment_lab.py`

**Step 1:** 새 메뉴명과 렌더링에 필요한 문구가 있는 실패 테스트를 추가한다.

**Step 2:** 테스트가 실패함을 확인한다.

**Step 3:** `검증 실험실` 메뉴, 입력 폼, 실행 버튼, 요약 지표, 문장별 비교표·상세 패널을 구현한다. `Store`, `enqueue_claim`, `process_pending`를 이 경로에서 호출하지 않는다.

**Step 4:** 테스트를 통과시킨다.

### Task 4: 회귀 검증 및 문서화

**Files:**
- Modify: `docs/plans/2026-07-26-verification-lab-design.md` (검증 결과만 필요 시)

**Step 1:** `pytest tests/test_experiment_lab.py tests/test_detect_llm.py tests/test_ingest_observability.py -v`를 실행한다.

**Step 2:** 전체 `pytest -q`를 실행한다.

**Step 3:** Streamlit 문법 검증과 앱 임포트 검증을 실행한다.

**Step 4:** 변경 파일만 스테이징해 커밋한다. 기존 사용자의 미추적 파일은 포함하지 않는다.

