# 직접 검증 절차 — README의 주장을 코드로 확인하기

README의 모든 주장은 아래 순서로 직접 확인할 수 있습니다.

> 요구사항: Python 3.10+. 코어는 표준 라이브러리만, 데모 UI만 Streamlit.
> 실 KOSIS API는 `.env`의 키로 스위치되며, **키 없이도 픽스처로 전 기능이 동작합니다.**
> 키는 커밋·공유 금지 — 재현 URL에도 자동 마스킹됩니다.

## 1. 전 기능이 오프라인으로 검증됨을 확인 (외부 API·키 불필요)

```bash
PYTHONPATH=. python -m pytest tests/ -q     # 134건, 약 12초
```

외부 의존성 없이 전부 통과한다는 것은 판정 로직이 네트워크·LLM 상태와 무관하게
결정적이라는 뜻입니다. 키 유출 방지 회귀 테스트(`tests/test_audit.py`)도 이 안에 있습니다.

## 2. 플라이휠의 계기판 확인

```bash
python scripts/run_eval.py                   # 골든셋 전 지표 + 전 회차 대비 diff
```

이 프로젝트에서 "좋아졌다"는 말은 금지어입니다 — 모든 변경은 이 diff로만 증명됩니다.
처음 실행하면 현재 지표가 곧 기준선입니다.

## 3. 운영 흐름 체험 (기사 넣기 → 검증 → 사람 리뷰 큐)

```bash
python scripts/service_run.py ingest 기사.jsonl   # 멱등 적재 (같은 파일 두 번 넣어도 안전)
python scripts/service_run.py process             # 검증 실행 — 건별 격리
python scripts/service_run.py queue               # 리뷰 큐: 불일치가 맨 앞에 온다
```

불일치는 절대 자동 발행되지 않고 사람 앞에 줄을 섭니다 —
발행등급 정책이 코드로 강제되는 것을 볼 수 있습니다.

## 4. 데모 로컬 실행 (선택)

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

배포본은 https://clafact-buhqbmwbqcvjh8a29kxrhs.streamlit.app 에서 설치 없이 체험할 수 있습니다.
