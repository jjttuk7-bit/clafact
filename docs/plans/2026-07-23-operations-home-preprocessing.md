# Operations Home Preprocessing Summary Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 운영홈에서 업로드 데이터의 전처리·분류·처리 결과와 다음 행동을 명확히 보여준다.

**Architecture:** 업로드 결과와 저장된 Claim 상태를 집계해 원본→기사→문장→Claim→라우팅→처리 흐름으로 표현한다. 운영홈 감사 로그 표는 제거하고 상세 감사는 검증자 리뷰로 둔다.

---

### Task 1: Dashboard contract and summary
- Test preprocessing labels and absence of the audit-log heading in `tests/test_upload_scoped_dashboard.py`.
- Update `streamlit_app.py` with preprocessing funnel, source routing counts, processing counts, and action links.
- Run focused dashboard tests and compile.