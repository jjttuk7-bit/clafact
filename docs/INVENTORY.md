# ClaFact 자산 인벤토리

작성: 2026-07-20 · 근거: 리포 전수 스캔 + 직접 실행 검증 (문서 주장 아님)
검증 커밋: `ee12e6c` · 실행 환경: Python 3.14, Windows

## 완성도 범례

- **동작 확인됨** = 오늘(07-20) 직접 실행해 결과를 봤다
- **부분 구현** = 코드는 있으나 실환경(실 API·실 LLM) 검증이 없다
- **설계만** = 문서·계획만 존재

## 1. 파이프라인 레이어별 자산

### Claim 추출 (탐지·파싱)

| 자산 | 무엇 | 완성도 |
|---|---|---|
| `clafact/pipeline/ingest.py` | 데이터셋 로더 + 크롬·댓글 제거(오늘 추가) + 문장 분리 | **동작 확인됨** — 실물 CSV 2,649건 적재 실측 |
| `clafact/pipeline/detect.py` | 규칙 필터 1차 탐지, 규칙 카드 패턴 런타임 로드 | **동작 확인됨** — 전수 16,464 후보 추출 실측 |
| `clafact/pipeline/parse.py` | Claim 구조화(수치·단위·상대시점·임계·추세) | **동작 확인됨** — run_eval 경유 |
| `clafact/llm.py` | Mock↔HCX 스위치, HcxClient | **부분 구현** — `.env`에 키 있음, **실호출 0회(키 유효성 미검증)** |
| `detect_llm.py` (LLM 2차 판별) | — | **없음** (W1 태스크, 파일 미생성) |

### Source Classification

| 자산 | 무엇 | 완성도 |
|---|---|---|
| `clafact/pipeline/source_classify.py` | — | **없음** — 모듈 자체 미구현, `run.py`에 배선 없음(grep 0건) |
| 규칙 v0.1 전수 분류 결과 | 8라벨 분류 16,464건 (`news_data/claims_classified_v01.json`) | **동작 확인됨** — 단, 일회성 스크립트 산출물이며 모듈·테스트 아님 |
| `data/goldenset/source_routing_seed.jsonl` | — | **없음** (기획 문서가 요구하는 파일) |

### Evidence Retrieval (KOSIS)

| 자산 | 무엇 | 완성도 |
|---|---|---|
| `clafact/pipeline/retrieve.py` | 경로 A: 별칭+키워드 검색 (픽스처 인덱스) | **동작 확인됨** — run_eval 경유 |
| `clafact/pipeline/retrieve_semantic.py` | 경로 B: 문자 n-gram 의미 검색 기준선 | **동작 확인됨** — 테스트 경유 |
| `clafact/pipeline/retrieve_kosis.py` | 경로 C: KOSIS 통합검색 클라이언트 | **부분 구현** — 오프라인 배선 검증만, **실검색(28만 표) 0회** (개발망 정부망 차단, 클라우드 필요) |
| `clafact/kosis.py` | Fixture/Http/Cached 클라이언트, URL 빌더 | **부분 구현** — Http 실호출은 2026-07-14 일부 검증 기록, 이후 0회 |
| `clafact/throttle.py` | 분당 제한 + 파일 영속 예산 가드 | **동작 확인됨** — 테스트 경유, `data/cache/call_budget.json` 존재 |
| `clafact/pipeline/query_gen.py` | 주장 문장 → 검색어 생성 | **동작 확인됨** — 테스트 경유 |

### Verdict

| 자산 | 무엇 | 완성도 |
|---|---|---|
| `clafact/pipeline/verdict.py` | 결정적 판정(단위·반올림·임계·파생계산), LLM import 없음 | **동작 확인됨** — run_eval 판정 3분류 Acc 1.0 |
| `clafact/pipeline/run.py` | E2E 오케스트레이션 | **동작 확인됨** — 단 소스분류 단계 미배선 |
| `clafact/audit.py` | 재현 URL(키 마스킹)·감사 로그 | **동작 확인됨** — 키 유출 회귀 테스트 통과 |
| 규칙 카드 12종 (`data/assets/rules/`) | A2-0001~0010, 0012, 0013 (0011은 결번 — 실 API 메타 필요로 미구현) | **동작 확인됨** — detect가 런타임 로드 |

### 평가 (run_eval)

| 자산 | 무엇 | 완성도 |
|---|---|---|
| `clafact/eval/harness.py` + `scripts/run_eval.py` | 골든셋 평가 + 전 회차 diff + 실패 자동 기록 | **동작 확인됨** — 오늘 실행: 탐지 F1 1.0, 판정 Acc 1.0 (골든셋 12건 **포화**) |
| `data/goldenset/golden_v0.jsonl` | 골든셋 시드 **12건** (사람 라벨) | 실존 — **"20건 파일럿(경제8/사회8/파생2/판단불가2)"은 존재하지 않음** |
| `data/goldenset/mapping_eval.jsonl` | 매핑 평가셋 10건 | 실존 — EXP-001용, 포화 상태 |
| `data/goldenset/LABELING_GUIDE.md` | 라벨링 가이드 | 실존 (문서) |
| `scripts/release_gate.py` | 공개 전 자동+사람 게이트 | **동작 확인됨** — 현재 판정: **실패(고위험)** — 시크릿 스캔이 `.env` 존재를 플래그 |
| `data/failures/failures.jsonl` | 실패 레코드 5건 — 전부 resolved | 실존 |
| `data/assets/aliases.jsonl` | 별칭 사전 5건 | 실존 (목표 300 대비 초기) |
| `reports/` | 평가 리포트 27개 (07-13~07-17) + exp001 | 실존 — 금요일 diff의 증거 사슬 |

### 운영 (서비스층·Hermes)

| 자산 | 무엇 | 완성도 |
|---|---|---|
| `clafact/service/` + `scripts/service_run.py` | SQLite 멱등 적재·건별 격리·리뷰 큐·발행등급 CLI | **동작 확인됨** — 단 현재 DB는 비어 있음(실데이터 미적재) |
| `scripts/review_cli.py`, `demo_server.py`, `streamlit_app.py` | HITL 리뷰, 데모 | 실존 — 데모는 Streamlit Cloud 배포 중 |
| `ops/` (PROJECT_STATE·인덱스·수신함 3문서) | Hermes 작업 공간 | 실존 — 팀 구조 5인 체제로 갱신됨 |
| `.claude/agents/` 4종 | 역할 전속 보조 에이전트 정의 | 실존 (오늘 커밋) |
| 테스트 137건 (`tests/` 15파일) | 규칙·키유출·서비스 포함 | **동작 확인됨** — 오늘 137 passed, 10.6s |

## 2. 리포 밖 자산 (참조)

- `../news_data/` — 조선일보 CSV 2,706건(89.6MB) + 분류 결과 JSON. **커밋 금지 유지**
- `../클라비_공유자료/` 01~19 — 킥오프·역할·일정·EDA·소스분류 분석
- `../프로젝트_문서/` 25종 — 제안서~실서비스 구축설계
- `data/external/snu_factcheck/` — SNU 아카이브 3,334건 (gitignore, W2 이후 보조용)

## 3. 모순·불일치 지점 (발견 즉시 기록)

1. **README가 "테스트 134건"이라 주장하나 실측 137건** — 오늘 ingest 테스트 3건 추가분 미반영. (docs/verify.md도 동일)
2. **`구현/` 폴더의 유령 상태**: 원격에서는 삭제 커밋(b354f58)으로 사라졌는데, 로컬에 **미추적 상태로 2/3만 재출현** (`검색매핑_구현가이드.md`, `구현계획.md` — `소스분류_구현가이드.md`는 소실). 커밋할지 폐기할지 결정 필요.
3. **릴리스 게이트 시크릿 스캔이 `.env` 존재 자체를 고위험 FAIL 처리** — 개발 단계에선 `.env`가 반드시 존재해야 하므로(HCX 키), 게이트 기준이 "존재"가 아니라 "추적/스테이징 여부"로 수정되어야 함.
4. **본 메타 프롬프트가 가정한 "20건 파일럿 골든셋"은 어느 파일에도 없음** — 실물은 12건 시드 + 매핑 10건. 어떤 문서가 이 가정의 출처인지 확인 필요(ops 쪽 계획 문서로 추정).
5. **A2-0011 결번** — 규칙 ID가 0010→0012로 건너뜀(이중계상 규칙, 실 API 메타 필요로 보류). 다음 채번은 0014. 모르면 버그로 오인하기 쉬움.
6. **서비스 DB 공백** — 서비스층은 검증됐지만 `data/service/`가 비어 있어, "운영 중"이 아니라 "운영 가능" 상태.
