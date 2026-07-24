# KOSIS 통계표 매핑 재현율 개선 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

| 항목 | 내용 |
|---|---|
| Author | Human Team + ClaFact Hermes Agent |
| Reviewed by | Human Team |
| Managed by | ClaFact Hermes Agent |
| Status | Draft |
| Version | v0.1 |
| Last Updated | 2026-07-24 |


**Goal:** 월간 인구동향·청년 실업률 등 실제 KOSIS 표 후보를 더 정확히 선택하고 선택 과정을 투명하게 표시한다.

**Architecture:** 짧은 도메인 보조 질의 두 개의 후보를 합쳐 중복 제거한 후, 핵심 지표어·주기 신호로 재정렬한다. UI는 evidence가 없을 때 audit의 표 정보를 대체 표시한다.

### Task 1: Regression tests
- Add fake-client tests for two compact queries, deduplication, and monthly population-table preference.
- Add parser test for `1~8월` → article-year August.
- Add UI contract test for audit-table fallback.

### Task 2: Minimal implementation
- Add `kosis_queries()` domain hint helper.
- Merge and rerank compact-query candidate rows in `KosisSearchIndex`.
- Add domain keyword scoring and month-range parsing.
- Show audit table/search query when no evidence row is selected.

### Task 3: Verification
- Run retrieval, parser, rerank, and Streamlit UI tests plus `py_compile`.
- Commit with `feat: improve KOSIS table mapping recall`.
