# 오늘 당장 실행할 작업 3개

작성: 2026-07-20 · 선정 기준: [DIAGNOSIS.md](DIAGNOSIS.md) 리스크 상위 3을 하나씩 무력화

## 1. HCX 스모크 호출 1회 — 키 유효성 검증 (R2, 10분)

리스크 #3 제거. W2를 "디버깅 주간"으로 만들지 않는 보험.

```bash
cd clafact
PYTHONPATH=. python -c "
import os
from dotenv import load_dotenv  # 없으면: .env를 셸에서 export
" 2>/dev/null || true
# .env 로더가 없으므로 환경변수 주입 후 실행:
PYTHONPATH=. HCX_API_KEY=$(grep ^HCX_API_KEY .env | cut -d= -f2) python -c "
from clafact.llm import HcxClient
c = HcxClient()
print(c.complete('당신은 분류기다. 예/아니오로만 답하라.', '다음 문장에 수치 주장이 있는가: 실업률은 7.2%였다'))"
```

성공 기준: 응답 텍스트 수신. 실패 시 오류 그대로 기록(엔드포인트/모델명/쿼터 구분) → W1 중 해결.
**주의: 응답·로그에 키가 찍히지 않게. 결과는 데일리 보고에 1줄.**

## 2. 소스분류 스크립트 → 정식 모듈 승격 (R3, 반나절)

리스크 #1의 절반(G-SOURCE-1 산출물 형식)을 제거. 로직은 이미 검증됨(전수 16,464건) — 옮기기만 하면 된다.

만들 파일:
- `clafact/pipeline/source_classify.py` — 공유자료 19 분석에 쓴 분류 로직(8라벨, 비-KOSIS 우승, 애매하면 UNKNOWN)을 함수화
- `data/assets/routing_v01.json` — 키워드 사전을 코드에서 데이터 파일로 분리 (기획 문서 사전 v0.1 그대로)
- `tests/test_source_classifier.py` — 라벨별 대표 문장 + 오라우팅 시드 3건(공유자료 19 §6)을 회귀 케이스로

완료 확인:
```bash
PYTHONPATH=. python -m pytest tests/test_source_classifier.py -q
```

## 3. 파일럿 50건 층화 추출 + 라벨링 착수 (R1, 오늘 시작)

리스크 #2(라벨링 시간) 방어 — 휴가 전 12일의 첫날을 라벨링에 쓴다.

```bash
cd clafact
PYTHONPATH=. python - <<'EOF'
import json, random
random.seed(42)
recs = json.load(open(r"../news_data/claims_classified_v01.json", encoding="utf-8"))
kosis = [r for r in recs if r["source_type"].startswith("KOSIS")]
quota = {"population_household":20, "employment_labor":15, "prices_inflation":10, "agriculture_fishery":5}
picked = []
for dom, n in quota.items():
    pool = [r for r in kosis if r["domain"]==dom]
    picked += random.sample(pool, min(n, len(pool)))
unknown = random.sample([r for r in recs if r["source_type"]=="UNKNOWN"], 10)  # 재현율 손실 추정용
with open("../news_data/pilot_50_for_labeling.jsonl","w",encoding="utf-8") as f:
    for r in picked+unknown: f.write(json.dumps(r, ensure_ascii=False)+"\n")
print("파일럿 후보 저장:", len(picked), "+ UNKNOWN 10")
EOF
```

이후: 2인 교차 라벨(가이드: `data/goldenset/LABELING_GUIDE.md`), 불일치는 R1 중재. **라벨은 사람만.**

## 부수 정리 (오늘 중 아무나 5분)

- README·docs/verify.md의 "134건" → **137건** 갱신 (INVENTORY 모순 #1)
- `구현/` 미추적 폴더 처분 결정: 재커밋 또는 삭제 (모순 #2 — 소실된 소스분류_구현가이드는 히스토리 `ee5619f` 이전에 없음, 원격 삭제 전 버전은 `git show b354f58^:"구현/소스분류_구현가이드.md"`로 복구 가능)
- `release_gate.py` 시크릿 스캔 기준을 "존재"→"git 추적/스테이징 여부"로 수정 (모순 #3)

---

## 전체 요약 (인벤토리의 사실만으로)

ClaFact는 픽스처 세계에서 완전히 관통하는 파이프라인(탐지→파싱→매핑→결정적 판정→리뷰, 테스트 137건, 재현 URL·규칙 카드 12종·플라이휠 실증)과, 오늘 도착한 실물 데이터셋의 전수 분석(2,649건 적재, Claim 후보 16,464건, KOSIS 후보 820건)을 갖고 있다. 그러나 실세계와 닿는 세 지점 — 소스분류 모듈, 경로 C 실검색, HCX 실호출 — 은 모두 미완이며, 골든셋은 12건 시드로 포화 상태라 현재의 F1 1.0은 성능이 아니라 관통의 증거일 뿐이다. G-SOURCE-1은 분석이 산출물 형식을 앞질러 간 상태라 하루 작업으로 닿는 거리에 있고, 가장 먼저 죽는 지점은 클라우드 실행 환경에 걸린 경로 C 실측이다. 위 3개 작업이 오늘 실행되면 세 리스크가 각각 10분·반나절·하루 안에 무력화된다.
