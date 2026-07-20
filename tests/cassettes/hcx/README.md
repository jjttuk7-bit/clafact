# HCX 카세트 (record-replay)

이 폴더의 `smoke.json`은 실 HCX 응답의 **녹화본**이다. CI·금요일 리추얼은
이 녹화본으로 오프라인 재생하므로 무과금·결정적이고, 키가 없어도 계약 테스트가 돈다.

## 녹화 방법 (R2, 키 있는 환경에서)

```bash
export HCX_API_KEY=$(grep ^HCX_API_KEY .env | cut -d= -f2)   # 셸 기록 주의
PYTHONPATH=. python scripts/record_hcx.py
```

- `smoke.json`이 생성/갱신된다. **키는 저장되지 않는다**(응답만) → 커밋 가능.
- 실 API 응답 구조가 바뀌면 재실행해 재녹화한다.

## 재생 (자동, 키 불필요)

```bash
PYTHONPATH=. python -m pytest -m contract      # 카세트 재생 계약 테스트
```

카세트가 없으면 계약 테스트는 skip된다(조용한 통과 아님 — 사유가 콘솔에 남는다).

## 실호출 스모크 (키 유효성 1회 확인)

```bash
export HCX_API_KEY=...
PYTHONPATH=. python -m pytest -m live          # 실 HCX 1회 호출
```
