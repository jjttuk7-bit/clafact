# ClaFact Project State

## 프로젝트

- 프로젝트명: ClaFact
- 기간: 40일
- 현재 단계: AI Native 프로젝트 운영체계 구축

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

## 팀 구조

- 팀원 1: Claim
- 팀원 2: Evidence
- 팀원 3: Verdict & Service
- 팀원 4: ClaFact Hermes Agent

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

## 현재 진행 중

- Hermes 문서 관리 Workflow 실제 테스트

## 다음 작업

1. Hermes 문서 관리 Workflow 실제 테스트
2. Hermes 일일 업무 Workflow 구축
3. Claim → Evidence → Verdict 협업 Workflow 구축

## 운영 원칙

- Claim, Evidence, Verdict를 섞지 않는다.
- Evidence 없이 Verdict를 내리지 않는다.
- 모르는 것은 모른다고 말한다.
- 근거 부족도 정상적인 결과다.
- 문서보다 작동하는 결과물을 우선한다.
- 반복 작업은 AI에게 위임하고 자동화한다.
- 중요한 결정에는 이유를 남긴다.

## 마지막 업데이트

2026-07-15
