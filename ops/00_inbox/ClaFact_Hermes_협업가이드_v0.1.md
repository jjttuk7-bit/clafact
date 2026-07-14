# ClaFact × Hermes Agent 협업 가이드 v0.1

| 항목 | 내용 |
|---|---|
| Author | Human Team + AI Assistant |
| Managed by | ClaFact Hermes Agent |
| Status | Draft |
| Version | v0.1 |
| Last Updated | 2026-07-15 |

---

# 1. 이 문서를 왜 보는가

ClaFact 팀은 3명의 인간 팀원과 1명의 AI 동료가 함께 일한다.

> **인간 3명 + ClaFact Hermes Agent = 4명의 프로젝트 팀**

Hermes는 단순히 질문에 답하는 챗봇이 아니다.  
프로젝트의 현재 상태를 읽고, 작업을 정리하고, 실제 파일을 수정하고, 문서를 관리하고, 반복 업무를 자동화하며, 다음에 무엇을 해야 하는지 제안하는 **제4의 팀원**이다.

이 문서는 팀원 모두가 Hermes와 같은 방식으로 협업하기 위한 실전 가이드다.

---

# 2. 가장 먼저 기억할 한 문장

> **사람은 무엇을 만들지, 무엇이 좋은지, 무엇을 승인할지 결정하고, AI는 실행의 대부분을 담당한다.**

사람이 담당하는 일:

- 문제 정의
- 기준 설정
- 중요한 판단
- 결과 검증
- 최종 승인
- 최종 책임

Hermes가 담당하는 일:

- 조사
- 초안 작성
- 코드 작성
- 파일 수정
- 테스트
- 비교
- 평가
- 문서 정리
- 반복 작업 자동화
- 다음 작업 제안

---

# 3. ClaFact의 핵심 구조

ClaFact는 다음 흐름으로 작동한다.

```text
Content
→ Claim
→ Evidence
→ Verdict
→ Service
→ Evaluation
→ Improvement
```

### Claim
**무엇을 검증할 것인가**

### Evidence
**무엇을 근거로 검증할 것인가**

### Verdict
**현재 확보된 근거로 어디까지 판단할 수 있는가**

Hermes는 이 세 영역을 섞지 않는다.

특히 다음 원칙을 지킨다.

- Evidence 없이 Verdict를 내리지 않는다.
- AI 내부 지식만으로 사실을 확정하지 않는다.
- 근거가 부족하면 `근거 부족` 또는 `판단불가`라고 말한다.
- 판정은 Evidence보다 강할 수 없다.

---

# 4. Discord에서는 어디서 어떻게 대화하는가

## 4.1 인간 팀원 전용 채널

예:

```text
#팀-대화
#회의-및-논의
```

이 공간은 인간 3명이 자유롭게 이야기하는 공간이다.

Hermes는 참여하지 않는다.

사용 예:

- 아이디어 토론
- 역할 조정
- 의견 충돌
- 인간끼리 먼저 정리해야 하는 논의

---

## 4.2 Hermes 전용 협업 채널

예:

```text
#hermes-desk
```

여기는 제4의 팀원과 직접 일하는 메인 공간이다.

사용 예:

```text
오늘 시작
```

```text
지금 우리 프로젝트 어디까지 왔어?
```

```text
이 작업 시작할게.
```

```text
작업 완료.
```

```text
오늘 종료.
```

```text
지금 가장 중요한 다음 작업은 뭐야?
```

---

## 4.3 역할별 작업 채널

```text
#claim
#evidence
#verdict-service
#integration
#evaluation
```

이 채널에서는 각 담당자가 실제 작업을 진행하고, 필요할 때 Hermes를 호출한다.

예:

```text
@ClaFact_Hermes_Agent
현재 논의를 바탕으로 Claim Schema 초안을 만들어줘.
```

```text
@ClaFact_Hermes_Agent
이 Evidence가 Claim을 실제로 뒷받침하는지 Critic 관점에서 검토해줘.
```

---

# 5. ClaFact의 공식 작업 공간은 어디인가

## GitHub 저장소

```text
https://github.com/jjttuk7-bit/clafact
```

이 저장소가 ClaFact의 공식 프로젝트 작업 공간이다.

Hermes가 실제로 읽고 수정하는 VPS 경로:

```text
/opt/data/profiles/clafact/workspace/clafact_repo
```

Hostinger 호스트 기준 경로:

```text
/docker/hermes-agent-ideu/data/profiles/clafact/workspace/clafact_repo
```

---

# 6. 우리가 반드시 알아야 할 4개의 핵심 파일

## 6.1 SOUL.md

```text
Hermes는 누구인가
```

ClaFact Hermes Agent의 정체성과 기본 행동 원칙을 정의한다.

현재 Hermes는 다음 역할을 가진다.

> ClaFact 프로젝트의 제4의 팀원

---

## 6.2 AGENTS.md

```text
ClaFact에서 어떻게 일해야 하는가
```

프로젝트 운영 규칙을 정의한다.

예:

- 문서 메타데이터 규칙
- Author 규칙
- Reviewed by 규칙
- Managed by 규칙
- Status 규칙
- 승인 규칙
- 문서 처리 흐름

---

## 6.3 PROJECT_STATE.md

```text
지금 프로젝트는 어디까지 왔는가
```

현재 상태의 기준 문서다.

포함 내용:

- 현재 단계
- 완료된 일
- 진행 중인 일
- 다음 작업
- 1차 PoC 범위
- 주요 운영 상태

Hermes에게 현재 상황을 물을 때 가장 먼저 참고하는 문서다.

---

## 6.4 DOCUMENT_INDEX.md

```text
어떤 공식 문서가 있는가
```

ClaFact의 공식 문서 목록이다.

각 문서의:

- 문서명
- 위치
- 분류
- 상태
- 담당
- 설명

을 관리한다.

---

# 7. 문서는 어디에 저장하는가

GitHub 저장소의 `ops/` 폴더를 사용한다.

```text
ops/
├── 00_inbox
├── 01_project
├── 02_claim
├── 03_evidence
├── 04_verdict_service
├── 05_evaluation
├── 06_meetings
├── 07_decisions
├── 08_outputs
└── 99_archive
```

### 00_inbox
새롭게 들어온 문서

### 01_project
제안서, 계획서, 요구사항, 프로젝트 개요

### 02_claim
Claim 관련 문서

### 03_evidence
Evidence 관련 문서

### 04_verdict_service
Verdict 및 Service 관련 문서

### 05_evaluation
Golden Set, 평가, 실험 결과

### 06_meetings
회의록, 멘토링 기록

### 07_decisions
중요한 결정과 이유

### 08_outputs
발표자료, 보고서, 최종 산출물

### 99_archive
대체되었거나 현재 사용하지 않는 문서

---

# 8. 새 문서를 처리하는 방법

새 문서는 먼저:

```text
ops/00_inbox
```

에 넣는다.

그다음 Discord에서:

```text
/document-intake
```

를 실행한다.

Hermes는 다음 순서로 처리한다.

```text
00_inbox 확인
→ 문서 읽기
→ 핵심 내용 분석
→ 기존 프로젝트 문서와 비교
→ 중복·충돌·미확정 사항 확인
→ 보관 위치와 파일명 제안
→ 인간 승인 요청
```

중요:

> **Hermes는 승인 전에는 중요한 문서를 마음대로 이동하거나 수정하지 않는다.**

인간이 승인하면:

```text
이동 또는 이름 변경
→ DOCUMENT_INDEX 등록
→ 필요 시 PROJECT_STATE 반영
→ 변경 결과 보고
```

를 수행한다.

---

# 9. 문서의 작성자와 관리자는 다를 수 있다

문서에는 다음 메타데이터를 사용한다.

```text
Author
Reviewed by
Managed by
Status
Version
Last Updated
```

예:

```text
Author: Human Team
Reviewed by: ClaFact Hermes Agent
Managed by: ClaFact Hermes Agent
Status: Draft
Version: v0.1
```

### Author

실제 작성자를 기록한다.

- 사람이 작성: `Human Team`
- Hermes가 작성: `ClaFact Hermes Agent`
- 공동 작성: `Human Team + ClaFact Hermes Agent`

Hermes가 문서를 분류하거나 이동했다고 해서 Author가 되는 것은 아니다.

### Status

- Draft: 초안
- Review: 검토 중
- Approved: 인간 팀이 승인한 공식 문서
- Superseded: 새 버전으로 대체됨
- Archived: 보관 문서

Hermes는 인간 승인 없이 중요한 문서를 `Approved`로 바꾸지 않는다.

---

# 10. 실제 문서관리 Workflow 예시

첫 번째 공식 문서:

```text
ClaFact_Project_Proposal_v0.1.md
```

실제 처리 흐름:

```text
Human Team이 문서 작성
→ GitHub ops/00_inbox 업로드
→ Hermes가 문서 분석
→ PROJECT_STATE와 비교
→ 중복·충돌·업데이트 필요 사항 탐지
→ 보관 위치와 파일명 제안
→ 인간 승인
→ ops/01_project로 이동
→ DOCUMENT_INDEX 등록
→ PROJECT_STATE 업데이트
→ Git 변경사항 확인
→ 인간 검토 후 Commit / Push
```

이 문서의 역할 구분:

```text
Author: Human Team
Reviewed by: ClaFact Hermes Agent
Managed by: ClaFact Hermes Agent
```

---

# 11. GitHub 변경은 어떻게 관리하는가

기본 원칙:

```text
Hermes가 파일 수정
→ Git이 변경 추적
→ 인간이 git diff 확인
→ 인간 승인
→ Commit
→ Push
```

Hermes는 기본적으로 다음을 자동 실행하지 않는다.

- git commit
- git push
- main 브랜치 병합

중요한 변경은 사람이 검토한다.

---

# 12. 팀원이 Hermes에게 일을 시킬 때 좋은 방식

나쁜 요청:

```text
이거 좀 해줘.
```

좋은 요청:

```text
이 작업의 목적은 Claim Extraction 정확도 개선이야.

입력:
Golden Set 20건

원하는 결과:
Claim Extraction 결과와 오류 유형 정리

완료 조건:
20건 모두 실행
오류 유형 분류
다음 개선안 제안

AI가 할 수 있는 부분은 최대한 직접 수행해줘.
중요한 결정은 실행 전에 알려줘.
```

하지만 모든 요청을 길게 쓸 필요는 없다.

Hermes는 프로젝트 상태를 알고 있으므로 다음처럼 말해도 된다.

```text
이 작업 시작할게.
```

```text
현재 상태를 보고 작업 목적과 완료 조건부터 정리해줘.
```

---

# 13. 매일 Hermes와 일하는 기본 흐름

## 아침

```text
오늘 시작
```

또는 매일 오전 9시 자동 Daily Brief를 확인한다.

Daily Brief에는:

- 오늘 가장 중요한 3가지
- 팀원별 핵심 작업
- AI에게 위임할 작업
- Blocker
- 결정 필요 사항

이 포함된다.

---

## 작업 시작

```text
이 작업 시작할게.
```

Hermes가 정리해야 하는 것:

- 왜 하는가
- 입력
- 결과물
- 완료 조건
- AI가 할 일
- 사람이 확인할 일

---

## 작업 완료

```text
작업 완료.
```

Hermes가 정리해야 하는 것:

- 무엇을 했는가
- 성공했는가
- 실패한 것은 무엇인가
- 무엇을 배웠는가
- 다음 작업은 무엇인가

---

## 하루 종료

```text
오늘 종료.
```

Hermes가 정리해야 하는 것:

- 오늘 완료
- 미완료
- 중요한 결정
- 실패
- 새롭게 알게 된 것
- 내일 가장 중요한 일

---

# 14. Hermes에게 맡겨야 하는 일

적극적으로 맡긴다.

- 조사
- 문서 초안
- 코드 작성
- 테스트
- 파일 정리
- 비교
- 오류 분석
- 평가
- 반복 작업
- 결과 요약
- 다음 행동 제안

---

# 15. 사람이 반드시 확인해야 하는 일

- 프로젝트 방향 변경
- 중요 기술 결정
- 공식 문서 승인
- 평가 기준 확정
- Verdict 기준 확정
- 외부 공개
- Git main 반영
- 최종 결과 책임

---

# 16. 반복되는 작업은 자동화한다

우리의 기본 발전 단계:

```text
Manual
→ Prompt
→ Template
→ Script
→ Skill
→ Agent
→ Automation
```

실제 예:

```text
매번 긴 문서관리 지시
→ document-intake Skill
```

앞으로도 같은 작업이 반복되면 Hermes에게 묻는다.

> 이 작업은 사람이 계속 직접 해야 하는가?

---

# 17. 현재 ClaFact Hermes가 할 수 있는 것

현재까지 완료:

- ClaFact 전용 Profile
- Discord Bot 연결
- Discord DM / Slash Command
- GPT-5.5 사용
- Codex OAuth 연결
- ClaFact 전용 SOUL.md
- AGENTS.md 운영 규칙
- PROJECT_STATE.md
- DOCUMENT_INDEX.md
- GitHub 공식 저장소 연결
- Hermes의 실제 파일 읽기/수정
- Git 기반 변경 추적
- document-intake Skill
- 문서 분석·분류·승인 Workflow
- 매일 아침 Daily Brief 자동화 준비

---

# 18. 팀원에게 가장 중요한 5가지

## 1
Hermes는 챗봇이 아니라 제4의 팀원이다.

## 2
모든 것을 직접 하지 말고 먼저 AI에게 맡길 수 있는지 본다.

## 3
Hermes가 만든 결과도 반드시 검증한다.

## 4
중요한 변경은 인간 승인 후 반영한다.

## 5
반복되는 작업은 Prompt → Skill → Automation으로 바꾼다.

---

# 19. 우리가 만들고 싶은 팀의 모습

```text
사람이 문제를 정의한다.
↓
Hermes가 실행한다.
↓
사람이 검증한다.
↓
Hermes가 기록한다.
↓
반복 작업은 시스템이 된다.
↓
다음 작업은 더 빠르고 더 정확해진다.
```

ClaFact의 목표는 단순히 사실검증 MVP 하나를 만드는 것이 아니다.

> **3명의 인간 팀원 모두가 AI에게 일을 시키고, 결과를 검증하고, 반복 작업을 시스템으로 만드는 AI Native한 작업 방식을 습득하는 것**

이것이 40일 동안 우리가 Hermes와 함께 일하는 이유다.

---

# 20. 처음 참여하는 팀원을 위한 10분 온보딩

1. `#팀-대화`는 인간끼리 대화한다.
2. `#hermes-desk`에서는 Hermes와 프로젝트를 운영한다.
3. `PROJECT_STATE.md`가 현재 상태의 기준이다.
4. 새 문서는 `ops/00_inbox`에 넣는다.
5. `/document-intake`로 문서를 분석한다.
6. Hermes의 제안을 보고 인간이 승인한다.
7. Hermes가 실제 파일을 수정한다.
8. Git 변경사항을 사람이 검토한다.
9. 반복 작업은 Skill이나 Automation으로 만든다.
10. 항상 마지막에 묻는다.

> **지금 ClaFact를 앞으로 움직이기 위한 가장 중요한 다음 행동은 무엇인가?**
