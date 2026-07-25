# 검증 실험실 설계

| 항목 | 내용 |
|---|---|
| Author | Human Team + ClaFact Hermes Agent |
| Reviewed by | Human Team |
| Managed by | ClaFact Hermes Agent |
| Status | Draft |
| Version | v0.1 |
| Last Updated | 2026-07-26 |

## 목적

운영 검증과 분리된 화면에서 동일한 뉴스 입력을 Python 규칙, LLM 단독, 하이브리드 엔진으로 각각 실행하고, 탐지·구조화 결과와 실행 비용을 비교한다. 이 기능은 운영 Claim·리뷰 큐·판정 이력을 변경하지 않는다.

## 선택한 방식

사이드바에 `검증 실험실` 메뉴를 추가한다. 한 번의 실행에서 세 방식을 모두 계산해 같은 행으로 비교한다. LLM이 사용할 수 없는 환경에서는 해당 열에 원인을 표시하되 Python/하이브리드 비교 화면 자체는 유지한다.

## 데이터 흐름

1. 사용자가 기사 본문과 발행일을 입력한다.
2. Python 방식은 기존 `detect.is_candidate`, `parse_claim`, `source_classify.classify`를 사용한다.
3. LLM 방식은 문장마다 `detect_llm.judge`를 호출한다. 이 버전은 LLM이 ‘검증 가능한 수치 주장인가’를 판별한 결과와 사유를 비교 대상으로 제공한다.
4. 하이브리드는 Python 후보만 LLM 2차 판별에 통과시킨다. LLM 호출 실패 시 Python 후보를 보수적으로 유지한다.
5. 실험 결과는 `st.session_state`에만 보관한다. `Store.enqueue_claim`, `process_pending`, KOSIS 검증, 리뷰 승인 기능을 호출하지 않는다.

## 화면 구성

- 상단: 운영 DB에 저장하지 않는다는 고지와 방식별 역할 설명
- 입력: 기사 본문, 발행일, 실행 버튼
- 요약: 방식별 탐지 수, LLM 호출 수, 처리 시간
- 표: 문장, Python 결과, LLM 결과/사유, 하이브리드 결과, 차이 여부
- 상세: Python이 추출한 수치·시점·라우팅 결과와 LLM 사유

## 안전 및 품질 원칙

- LLM 결과는 검증 완료나 최종 판정을 만들지 않는다.
- LLM 단독 결과도 원문 문장을 넘어선 수치·통계표·근거를 생성하지 않는다.
- API 키·LLM 설정이 없으면 화면은 오류가 아닌 ‘LLM 미사용’ 상태를 명시한다.
- 비교 화면은 운영 DB를 열거나 쓰지 않아야 한다.

## 범위 제외

- 이번 단계에서는 실험 실행 이력을 SQLite에 영구 저장하지 않는다.
- KOSIS 표 검색·최종 판정의 3방식 비교는 다음 단계에서 Claim 구조화 스키마와 골든셋이 준비된 뒤 추가한다.
- LLM이 수치·지표를 JSON으로 완전 추출하는 기능은 별도 실험으로 확장한다.

