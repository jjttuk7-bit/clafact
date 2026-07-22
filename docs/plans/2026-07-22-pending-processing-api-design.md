# PENDING 처리 API 경계 설계

**Author:** Codex

**Reviewed by:** Human Team

**Managed by:** Human Team

**Status:** Approved

**Version:** v0.1

**Last Updated:** 2026-07-22

## 목표

등록된 뉴스 Claim의 `PENDING` 큐를 기존 ClaFact 처리 워커로 소비할 수 있는
내부 FastAPI 경계를 제공한다. 이 단계에서는 실제 KOSIS·HCX 호출을 하지 않는다.

## API 계약

`POST /internal/batches/process-pending`은 선택적 `limit`을 받아, 그 수만큼의
`PENDING` Claim을 처리한다. 응답은 기존 `process_pending()`의
`processed`, `failed`, `by_tier`, `by_label` 집계를 반환한다.

## 구조와 데이터 흐름

FastAPI 경로는 서비스 DB의 `Store`를 열고, 현재는 샘플 `StatIndex`와
`FixtureKosisClient`를 주입해 `service.batch.process_pending()`을 호출한다.
워커는 Claim별 예외를 `FAILED`로 격리하고 다음 Claim 처리를 계속한다.
추후 KOSIS 단계에서만 이 의존성을 캐시된 실제 클라이언트로 교체한다.

## 테스트

- PENDING Claim을 처리하면 응답 집계와 DB 상태가 일치한다.
- 처리 오류는 500 응답으로 전체 요청을 실패시키지 않고, 해당 Claim만 `FAILED`로 남긴다.
- `limit`은 큐 소비 수를 제한한다.

## 범위 밖

- 뉴스 파일 업로드 엔드포인트
- 실제 KOSIS API 키·네트워크 호출
- HCX 호출과 설명 생성
- 스케줄러·인증·권한 부여
