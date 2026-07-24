# KOSIS 수치 주장 CSV 다운로드 설계

| 항목 | 내용 |
|---|---|
| Author | Human Team + ClaFact Hermes Agent |
| Reviewed by | Human Team |
| Managed by | ClaFact Hermes Agent |
| Status | Draft |
| Version | v0.1 |
| Last Updated | 2026-07-24 |

## Goal

운영 홈의 "KOSIS 수치 주장 추출 결과" 표에 표시되는 현재 업로드 결과를 CSV 파일로 다운로드할 수 있게 한다.

## Scope

- 현재 업로드의 `claim_previews`만 내보낸다.
- 화면 표와 동일한 열(기사, 기사 등록일, 수치 주장 문장, 추출 수치, 시점, 출처 분류)을 포함한다.
- UTF-8 BOM CSV를 생성해 한글 Excel에서 열 수 있게 한다.
- 추출 행이 없으면 다운로드 버튼을 표시하지 않는다.

## Design

`streamlit_app.py`는 기존 `extraction_rows`를 그대로 재사용한다. 표를 렌더링한 직후 `st.download_button`으로 메모리 내 CSV 바이트를 제공한다. 파일명은 다운로드 시점의 날짜를 포함한 `clafact_kosis_claims_YYYYMMDD.csv` 형식으로 만든다.

CSV 생성은 표준 라이브러리 `csv`와 `io.StringIO`만 사용한다. 데이터베이스 스키마, 기사·Claim·검증 결과 저장 로직은 변경하지 않는다.

## Validation

소스 수준 회귀 테스트로 다운로드 버튼, CSV MIME 타입, UTF-8 BOM 인코딩, 그리고 표 데이터 `extraction_rows` 재사용을 검증한다.
