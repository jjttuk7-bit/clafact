# Official Notice UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 검증 탭에서 공식 공지 근거를 등록하고 판정 결과를 즉시 표시한다.

**Architecture:** Streamlit 공식 공지 카드가 내부 API를 호출하고, 성공 뒤 화면을 재실행한다. KOSIS 큐는 변경하지 않는다.

**Tech Stack:** Streamlit, requests, pytest.

---

### Task 1: UI contract test

- Modify: `tests/test_upload_scoped_dashboard.py`
- Modify: `streamlit_app.py`

1. 공식 공지 섹션에 기관명·URL·시행일·등록 버튼 문자열을 요구하는 실패 테스트를 작성한다.
2. `pytest tests/test_upload_scoped_dashboard.py -q`로 RED를 확인한다.
3. `OFFICIAL_ANNOUNCEMENT` 카드에 입력 폼과 API POST 호출을 추가한다.
4. 테스트를 GREEN으로 만든다.
5. 변경 파일만 커밋한다.