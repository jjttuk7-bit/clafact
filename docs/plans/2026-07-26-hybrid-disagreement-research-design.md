# 하이브리드 불일치 연구 자산 설계

| 항목 | 내용 |
|---|---|
| Author | Human Team + ClaFact Hermes Agent |
| Reviewed by | Human Team |
| Managed by | ClaFact Hermes Agent |
| Status | Draft |
| Version | v0.1 |
| Last Updated | 2026-07-26 |

## 목적

Python 규칙과 HCX-005의 문장별 탐지 결과를 독립 실행해 `P+/H+`, `P+/H-`, `P-/H+`, `P-/H-`로 집계한다. 성공과 실패를 누적 가능한 연구 자산으로 전환하고, 하이브리드가 어느 실패를 보완하는지 심사·논문·제품 개선에 재현 가능한 수치로 제시한다.

## 설계 결정

검증 실험실의 결과만 별도 연구용 SQLite에 append-only로 저장한다. 운영 Claim·리뷰 큐·KOSIS 판정 DB는 열거나 변경하지 않는다.

- 연구 DB: `data/research/verification_lab.db` — 로컬 실행 이력이며 Git에 커밋하지 않는다.
- 승인 골든셋: `data/goldenset/hybrid_disagreements_v0.jsonl` — 사람이 검토한 사례만 버전 관리한다.
- 심사 자료: 화면 필터 결과를 CSV로 내려받는다.

## 분류 계약

HCX 실행 실패를 `H-`와 섞지 않는다. 문장별 상태는 다음 다섯 가지다.

| 코드 | 의미 | 후보 합집합 |
|---|---|---|
| `P+/H+` | 둘 다 탐지 | 포함 |
| `P+/H-` | Python만 탐지, HCX는 정상 미탐지 | 포함 |
| `P-/H+` | HCX만 탐지 | 포함하되 사람 검토 필요 |
| `P-/H-` | 둘 다 정상 미탐지 | 제외 |
| `HCX_ERROR` | HCX 호출·빈 응답·JSON 파싱 실패 | Python 결과 보존, 모델 성능 집계에서 분리 |

`P-/H+`는 자동 정답이 아니다. 사람이 원문을 검토해 `true_candidate`, `false_positive`, `hold` 중 하나를 부여한 뒤 골든셋 승격 여부를 결정한다.

## 저장 스키마

### experiment_runs

- `run_id`, `created_at`, `article_hash`, `article_title`, `article_date`
- `provider`, `model`, `prompt_version`
- `python_ms`, `hcx_ms`, `total_ms`, `hcx_calls`
- `source_row_count`, `sentence_count`

### experiment_sentences

- `run_id`, `sentence_index`, `sentence_hash`, `sentence_text`
- `python_candidate`, `python_reason`
- `hcx_status`, `hcx_candidate`, `hcx_reason`, `evidence_status`
- `disagreement_class`
- `human_label`, `review_note`, `reviewed_at`

기사 전체 본문은 저장하지 않는다. 업로드 행을 식별할 수 있는 해시와 결과 문장만 저장한다. API 키·Authorization 헤더·원문 밖 생성 문장은 저장하지 않는다.

## 화면

1. 네 유형과 `HCX_ERROR`을 카드와 비율 막대로 표시한다.
2. 유형을 선택하면 해당 문장·양쪽 근거·HCX 오류를 필터링한다.
3. `P-/H+`와 `P+/H-`에 사람 검토 라벨을 붙인다.
4. 현재 실행 또는 누적 기간을 CSV로 내려받는다.
5. 심사 요약에는 전체 문장 수, HCX 정상 응답률, 유형별 건수, 사람 검토 후 Python/HCX/합집합의 정밀도·재현율을 표시한다.

## 평가 원칙

- 사람 정답이 없는 네 유형 집계는 “모델 간 일치·불일치”이지 정확도가 아니다.
- 정밀도·재현율은 사람 검토가 완료된 골든셋에 대해서만 계산한다.
- HCX 오류는 미탐지로 계산하지 않는다.
- 모델·프롬프트 버전이 다른 실행은 기본적으로 분리해 비교한다.
- 동일 문장은 해시로 중복을 식별하되 실행 이력은 삭제하지 않는다.

## 성공 기준

- 동일 실행의 모든 문장이 네 유형 또는 `HCX_ERROR` 중 정확히 하나로 집계된다.
- 유형 합계와 오류 합계가 전체 문장 수와 일치한다.
- 연구 저장이 운영 DB에 쓰지 않는다는 테스트가 통과한다.
- 승인 전 사례는 골든셋 JSONL에 기록되지 않는다.
- CSV만으로 심사위원이 대표 성공·실패 사례와 누적 지표를 재현할 수 있다.
