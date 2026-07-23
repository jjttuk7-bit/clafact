# Review Official Evidence Replacement Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 리뷰어가 공식 공지 URL·기관·시행일을 입력해 위험 Claim을 재검증한다.

**Architecture:** 리뷰 카드가 기존 공식 공지 등록 API를 호출하고 저장된 판정을 갱신한다. KOSIS 표 ID 직접 교체는 제외한다.

**Tech Stack:** Streamlit, FastAPI, SQLite, pytest.

---

### Task 1: Review card form
- Add a failing dashboard contract test.
- Add institution, URL, effective date fields and a `공식 근거 교체 후 재검증` button to stored review cards.
- Call the existing official-notice endpoint and rerun on success.
- Run focused dashboard and API tests.