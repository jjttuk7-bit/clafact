# KOSIS 실호출 모드 설계

**Author:** Codex

**Reviewed by:** Human Team

**Managed by:** Human Team

**Status:** Approved

**Version:** v0.1

**Last Updated:** 2026-07-22

## 목표

PENDING 처리 API가 명시적 환경변수에 따라 Fixture KOSIS 또는 캐시된 실제 KOSIS
클라이언트를 선택하도록 한다. 실호출은 기본값이 아니다.

## 계약

- `CLAFACT_KOSIS_MODE` 기본값은 `fixture`다.
- 값이 `live`인 경우에만 `CachedKosisClient(HttpKosisClient())`를 구성한다.
- live 구성에 필요한 키가 없으면 Fixture로 폴백한다.
- live 클라이언트는 기존 `CallBudget`, `RateLimiter`, 디스크 캐시를 사용한다.

## 검증

- 기본·미지원 모드는 Fixture를 선택한다.
- live 모드는 캐시된 HTTP 클라이언트를 선택한다.
- 키 누락 시 실제 네트워크를 건드리지 않고 Fixture로 폴백한다.
- 마지막에 통합검색 1회만 실 호출해 비어 있지 않은 구조화 응답을 확인한다.

## 범위 밖

- HCX 연결
- API 요청별 live 모드 선택
- KOSIS 응답 원문·키의 로그 출력
