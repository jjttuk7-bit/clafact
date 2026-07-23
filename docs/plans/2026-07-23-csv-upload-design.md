# CSV Article Upload Design

| 항목 | 내용 |
|---|---|
| Author | Human Team + ClaFact Hermes Agent |
| Reviewed by | Human Team |
| Managed by | ClaFact Hermes Agent |
| Status | Draft |
| Version | v0.1 |
| Last Updated | 2026-07-23 |

## Goal

운영자가 서버 경로를 입력하지 않고 CSV 기사 파일을 업로드해 기사 등록을 완료한 뒤, 기존 배치 버튼으로 Claim 처리를 별도 실행하게 한다.

## Flow

1. 운영 홈에서 UTF-8 또는 UTF-8 BOM CSV 파일을 선택한다.
2. 업로드 API가 임시 파일을 생성하고 기존 `import_article_file` 흐름으로 등록한다.
3. 응답으로 읽은 기사·신규 등록·중복 수를 보여준다.
4. 임시 파일은 성공·실패 모두에서 제거한다.
5. 검증 처리는 자동 실행하지 않으며, 사용자가 기존 대기 Claim 처리 버튼을 사용한다.

## Validation

- `.csv` 파일만 받는다.
- 기존 별칭 스키마의 본문 컬럼을 사용한다.
- 파일 형식·본문 누락 등 로더 오류는 API에서 명확한 4xx 응답으로 전달한다.
