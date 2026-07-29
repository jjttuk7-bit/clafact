# Seed 100 골든셋 작성 가이드

| 항목 | 내용 |
|---|---|
| Author | ClaFact Hermes Agent |
| Reviewed by | Human Team |
| Managed by | ClaFact Hermes Agent |
| Status | Draft |
| Version | v0.1 |
| Last Updated | 2026-07-29 |

## 목적

`seed_v0.1.csv`는 뉴스 수치 문장과 KOSIS 근거를 같은 정답 계약으로 기록하는 연구 전용 원본입니다. 운영 Claim·리뷰 데이터는 수정하지 않습니다. 목표는 물가·고용·인구·주거·보건 각 20건, 총 100건입니다.

## 주요 열

- `claim_id`: 변경하지 않는 고유 ID. 예: `seed-v0.1-001`
- `domain`: `물가`, `고용`, `인구`, `주거`, `보건` 중 하나
- `sentence`: 검증할 원문 문장 전체
- `review_status`: `draft`, `needs_review`, `approved`, `on_hold` 중 하나
- `kosis_table_id`: 정답 KOSIS 통계표 ID. 아직 찾지 못했으면 비워 두고 `on_hold` 또는 `needs_review`로 남깁니다.
- `numeric_spans`: 문장 속 수치 표현을 `|`로 구분. 예: `2.4%|2.1%`
- `claim_type`: `수준형`, `증감형`, `비율형`, `순위형`, `비교형`, `추정형` 중 하나
- `indicator`, `value`, `unit`, `period`, `comparison_period`: 문장이 주장하는 지표·값·단위·기준기간·비교기간
- `kosis_selection`, `kosis_coordinates`: KOSIS에서 선택한 항목과 좌표/조건. 재현 가능한 수준으로 기록합니다.
- `official_value`, `formula`: 공식 값과 필요 시 계산식
- `source_url`, `snapshot_id`: 기사 원문과 KOSIS 조회 스냅샷의 추적 근거
- `annotator`, `reviewer`, `review_note`: 작성·검수 책임과 판단 이유

## 유효 예시

```csv
claim_id,domain,sentence,review_status,kosis_table_id,article_date,numeric_spans,is_verifiable_claim,claim_type,indicator,value,unit,period,comparison_period,geography,population,kosis_table_title,kosis_selection,kosis_coordinates,official_value,formula,source_url,snapshot_id,annotator,reviewer,review_note
seed-v0.1-001,물가,"지난달 소비자물가가 지난해 같은 달 대비 2.4% 상승했다.",approved,DT_1J22042,2025-11-04,2.4%,true,증감형,전년동월비,2.4,%,2025-10,2024-10,전국,전체,월별 소비자물가 등락률,지수종류=총지수;항목=전년동월비(%),2025.10/총지수/전년동월비(%),2.4,,https://example.org/article,kosis-example-001,작성자A,검수자B,표·항목·기간을 상호 검수함
```

## 2인 승인 규칙

1. 작성자(`annotator`)가 문장, 수치 분해, KOSIS 후보와 근거를 기록합니다.
2. 다른 사람(`reviewer`)이 원문·표 ID·선택 항목·공식값을 독립적으로 확인합니다.
3. 작성자와 검수자가 서로 다르고, 필수 열과 KOSIS 근거가 채워진 경우에만 `approved`로 변경합니다.
4. 불일치 또는 근거 미확정은 `needs_review` 또는 `on_hold`로 남기며, 추정으로 승인하지 않습니다.