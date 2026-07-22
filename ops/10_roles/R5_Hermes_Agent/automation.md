# R5 Hermes Automation

> Author: Human Team + ClaFact Hermes Agent
> Reviewed by: Human Team
> Managed by: ClaFact Hermes Agent
> Status: Draft
> Version: v0.1
> Last Updated: 2026-07-22

## Hermes cron

- 매일 오전 9시에 공식 문서를 읽고 브리핑을 생성한다.
- 읽기 순서: `PROJECT_STATE.md` → `ops/DECISION_LOG.md` → 역할별 최신 Daily → 역할별 Backlog → `DOCUMENT_INDEX.md`.

## Discord 브리핑

- Discord는 브리핑 전달과 논의 공간으로 사용한다.
- 브리핑의 근거 파일 경로와 기준일을 함께 표시한다.

## 문서 자동화

- 새 문서와 최신 Daily Log를 `DOCUMENT_INDEX.md`에 반영한다.
- 확정되지 않은 내용을 결정문서로 자동 승격하지 않는다.

## GitHub workflow

- 변경 전 민감정보 검사와 Markdown 링크·경로 검사를 수행한다.
- 자동화 실패는 작업 로그에 남기고 조용히 무시하지 않는다.