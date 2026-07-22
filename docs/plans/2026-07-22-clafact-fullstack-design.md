# ClaFact 실제 서비스 풀스택 설계

> Author: Human Team + ClaFact Hermes Agent
> Reviewed by: Human Team
> Managed by: ClaFact Hermes Agent
> Status: Approved
> Version: v0.1
> Last Updated: 2026-07-22

## 1. 목표

현재 Streamlit 데모와 Python 검증 엔진을 기자·팩트체커가 반복해서 사용하는 팀 업무용 웹서비스로 전환한다. 1차 범위는 저장소의 `news_data`를 적재하고, HCX API로 주장 정보를 구조화한 뒤, KOSIS API로 공식 근거를 매핑하고, 결정적 Verdict를 계산한 다음, 검증자가 승인·수정·반려하는 흐름이다.

## 2. 제품 사용자

- 검증자: Claim·Evidence·Verdict를 확인하고 최종 판정을 승인한다.
- R1 PM·Evaluation: 평가셋·릴리스 게이트·오류 분석을 관리한다.
- R2 Claim: 기사와 Claim 추출 결과를 관리한다.
- R3 Evidence: KOSIS 통계표 매핑과 근거 품질을 관리한다.
- R4 Verdict·Service: 판정 정책·발행등급·리뷰 큐를 관리한다.
- R5 Agent: 브리핑·실행·문서·운영 자동화를 담당한다.

## 3. 핵심 사용자 흐름

```text
news_data 기사 선택
  → 기사 전처리·문장 분리
  → HCX 주장 탐지·유형 분류·핵심 정보 추출
  → KOSIS 통계표 검색·후보 선정·API 조회
  → 검증 가능 / 판단불가 분기
  → 결정적 Verdict 계산
  → HCX 근거 설명 생성
  → 검증자 승인·수정·반려
  → 최종 리포트와 감사 이력 저장
```

HCX는 탐지·분류·추출·설명에만 사용하고, 일치·불일치·판단불가의 최종 판정은 기존 결정적 코드가 담당한다.

## 4. 권장 아키텍처

```text
Next.js 웹앱
  ↓ HTTPS / REST API
FastAPI API 서버
  ↓ 작업 생성
Redis Queue + Python Worker
  ├─ HCX Adapter
  ├─ KOSIS Adapter + Cache + Rate Limit
  └─ ClaFact Pipeline
       ├─ ingest / detect / parse
       ├─ retrieve / rerank
       ├─ deterministic verdict
       └─ explanation / audit
  ↓
PostgreSQL + S3 호환 파일 저장소
```

### 기술 선택

- Frontend: Next.js, TypeScript, 서버 상태 캐시, 접근성 중심 컴포넌트
- API: FastAPI, Pydantic, OpenAPI
- Worker: 기존 Python 엔진을 호출하는 별도 작업 프로세스
- Queue: Redis 기반 작업 큐
- DB: PostgreSQL
- 파일: 원문·KOSIS snapshot·리포트용 S3 호환 스토리지
- Auth: 조직·역할 기반 인증, 1차는 초대된 팀원만 접근
- Observability: 구조화 로그, 작업별 run ID, API 호출량·실패율·지연시간

## 5. 이미지 파이프라인과 실제 단계 매핑

| 이미지 단계 | 실제 시스템 책임 | 주요 산출물 |
|---|---|---|
| ① 기사 입력·전처리 | `news_data` 적재, 본문 정제, 문장 분리 | Article, Sentence |
| ② 주장 탐지 | 규칙 필터 + HCX 검증 | Claim 후보 |
| ③ 주장 유형 분류 | 증감·규모·비교·전망 분류 | Type label |
| ④ 핵심 정보 추출 | HCX 구조화 출력 검증 | Claim JSON |
| ⑤ KOSIS 통계 조회 | 통합검색·후보 선정·통계 API | Evidence |
| ⑥ 존재 여부 분기 | 근거 부재·정의 불명확·시점 불일치 처리 | Verifiable / Unverifiable |
| ⑦ 비교 판정 | 단위·시점·모집단 정렬과 계산 | Verdict |
| ⑧ 설명 생성 | Evidence와 계산식만 입력한 HCX 설명 | Report draft |
| ⑨ 검증자 리뷰 | 승인·수정·반려·재처리 | Final report, Review audit |
| Agent 운영층 | Daily·Backlog·브리핑·재시도·문서 자동화 | Run log, Briefing |

## 6. 1차 데이터 전략

`news_data`는 원천 입력으로 사용하되, 웹 요청마다 파일을 직접 읽지 않는다. 초기 적재 작업이 기사·메타데이터·원문 해시를 PostgreSQL에 저장하고, 원문 파일은 보존용 스토리지에 둔다.

### 핵심 엔터티

- `organizations`, `users`, `memberships`: 조직과 역할 권한
- `articles`: 제목·날짜·섹션·URL·본문·원문 해시
- `claims`: 문장·유형·구조화 필드·상태·신뢰도
- `evidence`: KOSIS 기관·통계표 ID·지표·기간·단위·원자료 snapshot
- `verdicts`: label·reason·calculation·rules·confidence
- `reviews`: reviewer·action·note·before/after
- `runs`: 실행 종류·상태·코드 버전·통계·오류
- `audit_events`: 키 마스킹된 단계별 감사 이벤트

## 7. 상태 모델

```text
INGESTED
  → EXTRACTING
  → CLAIMS_READY
  → EVIDENCE_SEARCHING
  → EVIDENCE_READY / UNVERIFIABLE
  → VERDICT_READY
  → EXPLANATION_READY
  → NEEDS_REVIEW / AUTO_CONFIRMED
  → CONFIRMED / CORRECTED / REJECTED
```

한 Claim의 실패가 전체 배치를 중단시키지 않도록 Claim 단위 격리를 유지한다. KOSIS·HCX 호출 실패는 재시도 가능 오류와 영구 실패를 분리한다.

## 8. API 초안

- `POST /api/v1/ingest/news-data`: news_data 적재 작업 생성
- `GET /api/v1/articles`: 기사 목록·필터·실행 상태
- `POST /api/v1/articles/{article_id}/runs`: 기사 검증 실행
- `GET /api/v1/runs/{run_id}`: 전체 진행 상태와 단계별 통계
- `GET /api/v1/articles/{article_id}/claims`: Claim 목록
- `GET /api/v1/claims/{claim_id}`: Claim·Evidence·Verdict 상세
- `POST /api/v1/claims/{claim_id}/reviews`: 승인·수정·반려
- `GET /api/v1/review-queue`: 불일치·저신뢰·판단불가 리뷰 큐
- `GET /api/v1/reports/{claim_id}`: 최종 리포트
- `GET /api/v1/ops/summary`: 역할별 Backlog·실패·실행 요약

브라우저는 HCX·KOSIS 키를 절대 받지 않는다. 모든 외부 API 호출은 FastAPI가 만든 작업을 Worker가 수행한다.

## 9. 웹 화면

1. 로그인·조직 선택
2. 기사 작업대: `news_data` 기사 목록, 검증 시작, 실행 상태
3. 실행 상세: 9단계 진행 타임라인, 실패·재시도 상태
4. Claim 검토: 문장·유형·추출 JSON·원문 위치
5. KOSIS Evidence: 후보 통계표, 선택 근거, API 조회값, 재현 URL
6. Verdict: 계산식·정렬 조건·판정·판단불가 사유
7. 리뷰 큐: 우선순위·승인·수정·반려·재처리
8. 리포트: 출처·계산·한계·검증자·감사 이력
9. 운영 대시보드: R1~R5 Daily·Backlog·실패·API 예산·릴리스 게이트

## 10. 보안·운영 원칙

- HCX·KOSIS 키는 서버 Secret으로만 관리한다.
- 로그·리포트·Daily에 키·토큰·개인정보·내부 링크를 기록하지 않는다.
- 원문 접근 권한과 조직별 데이터 격리를 적용한다.
- KOSIS 호출은 캐시·레이트 리밋·예산·재시도를 적용한다.
- HCX 설명에는 검색된 Evidence와 계산 결과만 전달한다.
- 자동 발행과 사람 리뷰 발행을 명시적으로 구분한다.
- 모든 실행은 `run_id`, 커밋, 데이터 버전, API 호출 요약을 남긴다.

## 11. 출시 단계

### Phase 1 — 실제 파이프라인 서버화

`news_data → HCX → KOSIS → Verdict`를 실제 API와 Worker로 연결하고, 작업 상태와 실패 재시도를 구현한다.

### Phase 2 — 검증자 업무 도구

Claim·Evidence·Verdict 상세와 리뷰 큐, 승인·수정·반려, 최종 리포트를 제공한다.

### Phase 3 — 팀 운영화

조직·역할 권한, R1~R5 운영 대시보드, Daily·Backlog·Agent 브리핑, 평가·릴리스 게이트를 연결한다.

### Phase 4 — 외부 서비스화

기사 URL 입력, 공개 리포트, API 키·요금제·호출량 제한을 추가한다.

## 12. Phase 1 완료 기준

- `news_data` 기사 1건을 DB에 적재할 수 있다.
- HCX 호출 실패·타임아웃·잘못된 JSON을 Claim 단위로 격리한다.
- KOSIS 검색·조회 결과와 재현 URL을 저장한다.
- 근거가 없으면 자동으로 `UNVERIFIABLE`이 된다.
- 결정적 Verdict와 계산식이 재실행해도 동일하다.
- 실행 상태를 웹 API에서 조회할 수 있다.
- API 키가 브라우저·로그·DB 일반 필드에 노출되지 않는다.
