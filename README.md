# ClaFact — AI 기반 뉴스 사실검증 시스템

뉴스 기사 속 수치 주장을 탐지하고, KOSIS 공식 통계와 비교해 **일치 / 불일치 / 판단불가**를
근거와 함께 판정하는 시스템. (클라비 × 아이펠톤 프로젝트)

**🔴 라이브 데모: https://clafact-buhqbmwbqcvjh8a29kxrhs.streamlit.app** — 샘플 버튼 클릭 한 번으로 검증 체험
| [설계 구조(머메이드)](docs/architecture.md) | 실데이터 검증 완료 (KOSIS 실 API, 2026-07-14)

> 운영 원칙: **"실패 1건 = 자산 1줄"** — 매핑이 실패하면 사전에, 판정이 틀리면 규칙에,
> 리뷰에서 뒤집히면 골든셋에 추가한다. 예외 없이. (문서 11 참조)

## 빠른 시작

```bash
# 평가 하네스 (A5) — 한 줄로 전 지표
python scripts/run_eval.py

# 릴리스 게이트 — 데모·파일럿 공개 전 필수 (문서 12 §5.1)
python scripts/release_gate.py

# 단위 테스트
python -m tests.test_verdict
python -m tests.test_detect
```

외부 의존성 없음(표준 라이브러리만). Python 3.10+.

## 구조

```
clafact/
├── clafact/
│   ├── schemas.py            # Claim/Evidence/Verdict + 상태 머신 (문서 10)
│   ├── assets/
│   │   ├── alias_dict.py     # A1. 별칭 사전 (기사어↔통계어)
│   │   └── failures.py       # A4. 실패 레코드 — resolve 시 파생 자산 ID 필수(감사 장치)
│   ├── pipeline/
│   │   ├── detect.py         # 1차 규칙 필터 (FR-02) — 재현율 책임
│   │   └── verdict.py        # 판정 엔진 (결정적, LLM 미사용) — 단위 정규화·반올림·임계·파생계산
│   └── eval/
│       ├── harness.py        # A5. 평가 하네스 — 실행·버전기록·전회차 비교·실패 자동 덤프
│       └── metrics.py        # P/R/F1, 3분류 리포트, Fallback 지표 (문서 05)
├── data/
│   ├── goldenset/golden_v0.jsonl   # A3. 골든셋 (12행 시드 — 단순/파생/환산/임계/함정형)
│   ├── assets/aliases.jsonl        # A1 저장소
│   ├── assets/rules/*.json         # A2. 규칙 카드 (조건·처리·유래 실패·테스트 링크)
│   └── failures/failures.jsonl     # A4 저장소
├── scripts/run_eval.py
├── tests/                    # "테스트 없는 규칙은 등록 불가"
└── reports/                  # 평가 리포트 (run별 + latest.json)
```

## 플라이휠 — 실제로 돌아간 첫 사례 (2026-07-13)

1. 하네스 첫 실행 → 탐지 F1 **0.9412**, 실패 1건 자동 기록 (`F20260713142141-0828`)
2. 원인: "사상 최악" 같은 숫자 없는 최상급 주장을 규칙 필터가 놓침
3. 규칙 **A2-0003** 작성(+테스트) → 실패 resolve (파생 자산 연결, 빈 자산은 거부됨)
4. 재실행 → 탐지 F1 **1.0000 (▲0.0588)** — 전 회차 대비 diff로 자동 표시

같은 방식으로 판정 엔진도 첫 실행에서 **A2-0001**(임계 표현 부등호 판정),
**A2-0002**(반올림은 기사 단위 스케일 기준)를 획득했다.

## 다음 단계 (WBS 문서 06 연동)

- [x] `git init` + 첫 커밋 (하네스의 code_version 기록 활성화)
- [x] 신뢰도 그라데이션 (Verdict.confidence, 규칙 A2-0004) — 문서 12 §5.2
- [x] 릴리스 게이트 스크립트 (`scripts/release_gate.py`) — 문서 12 §5.1
- [x] 규칙 기반 Claim Parser (`pipeline/parse.py`) — 수치·단위, 상대 시점(A2-0005), 임계·추세
- [x] Ingest 모듈 (`pipeline/ingest.py`) — 데이터셋 로더·전처리·문장 분리 (파일 도착 시 꽂기만)
- [x] 매핑 경로 A 기준선 (`pipeline/retrieve.py`) — 별칭 사전 + 키워드 검색, 픽스처 풀체인 검증
- [x] KOSIS 클라이언트 (`kosis.py`) — Fixture(오프라인) + Http(키 도착 시 스위치)
- [x] LLM 추상화 (`llm.py`) — MockLLMClient(개발) + HcxClient(키 도착 시 스위치)
- [x] 리뷰 CLI (`scripts/review_cli.py`) — WF-2 승인/보정/반려, 보정→A4 배선
- [ ] 키 도착 후: HCX 실연동(주장 판별·추출·설명), KOSIS 실 인덱싱, 경로 B(임베딩) 실험 EXP-001
- [ ] 데이터셋 도착 후: 골든셋 50건 확장 (교차 라벨링, 가이드 v1)
- [ ] 스탠드업 질문: "어제 자산 몇 건?" — `FailureRecorder.stats()` / `AliasDict.stats()`

관련 문서: `../프로젝트_문서/` (01 제안서 ~ 11 기술자산전략)

⚠️ API Key(HCX·KOSIS)는 `.env`로만 관리 — 커밋·공유 금지 (문서 07 보안 수칙)
