# 뉴스 파일 등록·대기 큐 경계 설계

**Author:** Codex

**Reviewed by:** Human Team

**Managed by:** Human Team

**Status:** Approved

**Version:** v0.1

**Last Updated:** 2026-07-22

## 목표

`news_data` 형식의 기사 파일을 서비스 저장소에 등록하고, 기존 엔진이 처리할
후보 문장을 `PENDING` 상태로 보존한다. 이 경계에서는 HCX와 KOSIS를 호출하지
않는다.

## 입력·출력 계약

- 입력은 기존 `clafact.pipeline.ingest.load_articles()`가 지원하는 JSONL 또는 CSV다.
- 열 이름 정규화, 본문 정제, 문장 분리는 기존 ingest 계층의 결과를 그대로 사용한다.
- 신규 기사는 `Store.articles`에 저장하고, 숫자 Claim 후보만 `Store.claims`에
  `PENDING`으로 등록한다.
- 동일한 기사를 다시 등록하면 기사와 Claim은 추가되지 않는다.
- 반환값은 등록 경계에 필요한 `read`, `imported`, `duplicates`만 제공한다.

## 구조

`backend.app.ingest_service.import_article_file(path, store)`가 API 계층의 얇은
등록 서비스가 된다. 데이터 변환은 `load_articles`, 저장과 멱등성은 `Store`,
후보 탐지는 `detect.is_candidate`에 위임한다. 처리 워커는 기존
`service.batch.process_pending()`가 이후 단계에서 큐를 소비한다.

## 오류와 범위

- 지원하지 않는 파일 형식과 잘못된 JSONL은 기존 로더의 오류를 그대로 전달한다.
- 본문 없는 행·중복 URL은 기존 로더가 제외한다.
- 이 단계는 업로드 HTTP 엔드포인트, 배치 실행, HCX·KOSIS 연동을 추가하지 않는다.

## 검증

1. JSONL 한 건을 등록하면 정제된 기사가 한 건 저장되고, 재등록은 중복으로 집계된다.
2. 숫자 Claim 후보는 `PENDING`으로 큐잉되며 아직 결과 상태로 바뀌지 않는다.
3. 관련 테스트와 전체 오프라인 테스트를 실행한다.
