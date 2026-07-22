# ClaFact 역할별 작업 로그 운영체계 설계

> Author: ClaFact Hermes Agent
> Reviewed by: Human Team
> Managed by: ClaFact Hermes Agent
> Status: Approved
> Version: v0.1
> Last Updated: 2026-07-22

## 목표

PDF의 운영 기준에 맞춰 `ops/10_roles/`를 GitHub 공식 역할별 작업 로그 공간으로 추가한다.

## 설계

- R1 PM·Evaluation부터 R5 Hermes Agent까지 책임별 폴더를 둔다.
- 모든 역할은 `README.md`, `backlog.md`, `daily/`를 소유한다.
- 매일의 사실은 `daily/YYYY-MM-DD.md`에 기록하고, 확정 결정은 `ops/DECISION_LOG.md`로 승격한다.
- 역할별 판단 기준은 특수 문서로 분리한다: `decisions.md`, `rules.md`, `mappings.md`, `verdict_policy.md`, `automation.md`.
- 기존 `PROJECT_STATE.md`와 `DOCUMENT_INDEX.md`를 전체 상태·문서 색인의 기준으로 유지한다.

## 운영 규칙

- Discord는 논의 공간이고 GitHub 문서가 공식 기록이다.
- Daily Log는 결정문서가 아니며, 골든셋 정답 라벨은 자동화가 직접 갱신하지 않는다.
- API 키·토큰·개인정보·내부 접근 링크는 기록하지 않는다.
