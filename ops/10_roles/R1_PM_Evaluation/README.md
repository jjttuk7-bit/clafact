# R1 PM·Evaluation

> Author: Human Team + ClaFact Hermes Agent
> Reviewed by: Human Team
> Managed by: ClaFact Hermes Agent
> Status: Draft
> Version: v0.1
> Last Updated: 2026-07-22

## Mission

시스템이 좋아졌는지 나빠졌는지를 숫자와 릴리스 기준으로 판단한다.

## Owns

- `clafact/eval/harness.py`
- `clafact/eval/metrics.py`
- `scripts/run_eval.py`
- `scripts/release_gate.py`

## Inputs / Outputs

- Inputs: R4 리뷰 큐, 실패 레코드, 골든셋 라벨 결과
- Outputs: 평가 리포트, 릴리스 게이트 판정

## Rules

- Daily Log는 작업 기록이며 공식 결정은 `ops/DECISION_LOG.md`에 기록한다.
- 골든셋 정답 라벨을 자동화 결과로 직접 덮어쓰지 않는다.