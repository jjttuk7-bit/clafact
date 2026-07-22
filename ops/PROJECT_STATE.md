# ClaFact Project State

## 프로젝트

- 프로젝트명: ClaFact
- 기간: 40일
- 현재 단계: 1차 Vertical PoC 실데이터 검증 이후 운영·협업 Workflow 정렬

## 프로젝트 목표

ClaFact는 뉴스와 콘텐츠에서 검증 가능한 Claim을 추출하고,
신뢰할 수 있는 Evidence를 수집·구조화한 뒤,
근거에 기반한 Verdict를 사용자에게 제공하는 AI 기반 사실검증 시스템이다.

## 핵심 파이프라인

Content
→ Claim
→ Evidence
→ Verdict
→ Service
→ Evaluation
→ Improvement

## 1차 Vertical PoC 범위

- ClaFact의 전체 구조는 Claim → Evidence → Verdict → Service이다.
- KOSIS 공식 통계 기반 뉴스 수치 Claim 검증은 40일 프로젝트의 1차 Vertical PoC 범위로 기록한다.
- 이 PoC 범위를 ClaFact의 전체 장기 범위로 보지 않는다.
- 1차 Vertical PoC의 핵심 검증 대상은 조선일보 2025년 기사 데이터셋과 KOSIS 공식 통계 기반 수치 Claim이다.

## 팀 구조

- 팀원 1: Claim
- 팀원 2: Evidence
- 팀원 3: Verdict & Service
- 팀원 4: (역할 배정 예정 — W1 킥오프에서 확정)
- 팀원 5: ClaFact Hermes Agent

## 현재 완료

- ClaFact Hermes Profile 생성
- Discord Bot 연결
- Discord 일반 메시지 응답
- Discord DM 및 Slash Command 작동
- OpenAI Codex OAuth 연결
- GPT-5.5 사용
- ClaFact 전용 SOUL.md 적용
- 인간 팀원 전용 Discord 공간 생성
- ClaFact 공식 GitHub 저장소 연결 완료
- GitHub 저장소를 Hermes 공식 작업 공간으로 연결 완료
- ops/ 프로젝트 운영 구조 구축 완료
- PROJECT_STATE.md와 DOCUMENT_INDEX.md를 공식 저장소에 통합 완료
- Hermes가 공식 저장소의 PROJECT_STATE.md를 직접 읽는 테스트 완료
- Hermes가 공식 저장소 파일을 수정할 수 있도록 권한 설정 완료
- ClaFact 1차 PoC 기준안: KOSIS 공식 통계 기반 뉴스 수치 Claim 검증
- ClaFact 프로젝트 제안서 v0.1 공식 문서 등록
- CLF-LOG-001 1차 실데이터 작동 결과물 저장본 등록
- 조선일보 2025년 기사 데이터셋과 KOSIS Open API를 사용한 1차 실데이터 관통 실행 완료
- 실 기사 2,649건에서 Claim 후보 16,464건을 추출하고 KOSIS 검증 후보 820건을 선별
- KOSIS 검색 질의 19/19 성공 확인
- 7차 실행에서 실제 뉴스 기사와 실제 국가통계를 연결한 정확한 실판정 3건 확보
- 오'불일치' 5건을 0건으로 줄이는 가드·리랭커·규칙화 루프 확인
- 신규 규칙 카드 A2-0014, A2-0015, A2-0016 도출
- 테스트 수 137건 → 185건 확대
- Hermes 일일 오전 9시 브리핑 Workflow 생성 및 수동 실행 성공
- 역할별 작업 로그 운영체계 `ops/10_roles/` 생성
- R1~R5 역할별 README·Daily Log·Backlog·특수 문서 생성
- 공식 결정 로그 `ops/DECISION_LOG.md` 추가

## 현재 진행 중

- Hermes 문서 관리 Workflow 실제 테스트 및 PROJECT_STATE 최신화
- CLF-LOG-001 결과를 기준으로 다음 개발 우선순위 정렬
- Claim → Evidence → Verdict 협업 Workflow 구체화
- 1차 실데이터 실행에서 남은 오류·판단불가 사유를 규칙과 구현 과제로 분리

## 다음 작업

1. PROJECT_STATE.md 최신화 내용을 팀에 공유하고 인간 팀 검토를 받는다.
2. 모집단 정렬 문제를 A2-0017 후보로 정리한다.
   - 예: “175개 품목 평균” 같은 부분집합을 전체 CPI와 대조하는 문제.
   - 7차 실행에서 유일하게 남은 오'불일치 관련 과제다.
3. 지수 기준연도 표기 오파싱 문제를 수정 과제로 분리한다.
   - 예: “2020년=100”의 `2020년`을 주장 시점으로 오인하는 문제.
4. 리랭커와 Evidence 매핑 적합성 검증 범위를 확대한다.
   - 물가 계열에서 검증된 흐름을 취업자, 출생아, 인구 지표로 확장한다.
5. 판단불가 비중을 줄이기 위한 판정률 회복 전략을 세운다.
6. HCX 2차 판별 실연동을 완료한다.
   - `detect_llm.py` 구현·배선은 완료되었고 실 HCX 카세트 녹화가 남아 있다.
7. Hermes 일일 업무 Workflow를 실제 팀 운영에 맞춰 안정화한다.
   - 오전 9시 브리핑 결과, 멘션, 자료 기준, 완료 작업 재추천 방지 여부를 점검한다.
8. Claim → Evidence → Verdict 역할별 협업 규칙을 문서화한다.

## 운영 원칙

- Claim, Evidence, Verdict를 섞지 않는다.
- Evidence 없이 Verdict를 내리지 않는다.
- 모르는 것은 모른다고 말한다.
- 근거 부족도 정상적인 결과다.
- 문서보다 작동하는 결과물을 우선한다.
- 반복 작업은 AI에게 위임하고 자동화한다.
- 중요한 결정에는 이유를 남긴다.
- 오판을 줄이는 것을 판정률을 높이는 것보다 우선한다.
- 완료된 작업을 반복 추천하지 않는다.

## 최근 근거 문서

- DOCUMENT_INDEX.md
- CLF-LOG-001 1차 실데이터 작동 결과물 저장본
- ops/08_outputs/real_data_application_log_20260720/CLF-LOG-001_result_summary.md

## 마지막 업데이트

2026-07-22
- Discord 논의와 GitHub 공식 기록이 충돌하면 GitHub 문서를 우선하고 충돌 사실을 보고한다.
- Daily Log에는 API 키·토큰·개인정보·내부 접근 링크를 기록하지 않는다.

## 마지막 업데이트

2026-07-22
