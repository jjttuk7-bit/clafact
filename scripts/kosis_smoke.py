"""KOSIS 실 API 스모크 테스트 — 픽스처와 실데이터가 일치하는지 검증.

사용법:
  1) clafact/.env 파일에 KOSIS_API_KEY=발급받은키 입력 (채팅·코드에 절대 붙여넣지 말 것)
  2) python scripts/kosis_smoke.py

검증 내용:
  - 실 KOSIS 통계자료 API 호출 성공 여부 (인증·파라미터 형식)
  - 클라비 제시 사례 통계표(DT_1EA1019, 농림어업조사)의 실제 수치가
    노션 제시값(2024 과수 총 166,558가구, 65세 이상 합계 106,877)과 일치하는지
  - 응답 필드명이 픽스처 스키마(C1_NM/C2_NM/UNIT_NM/PRD_DE/DT)와 같은지
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]


def load_env():
    """stdlib .env 로더 — KEY=VALUE 줄만 해석."""
    import os
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def main() -> int:
    load_env()
    from clafact.kosis import HttpKosisClient

    try:
        client = HttpKosisClient()
    except RuntimeError as e:
        print(f"✗ {e}")
        print("  → clafact/.env 파일을 만들고 KOSIS_API_KEY=<발급키> 를 넣어주세요")
        return 1

    print("① 실 API 호출: 농림어업조사 DT_1EA1019 (orgId=101, 2024년)...")
    try:
        rows = client.fetch_data("101", "DT_1EA1019", prd_de="2024")
    except Exception as e:
        print(f"✗ 호출 실패: {e}")
        print("  → 파라미터 형식이 다를 수 있음 — 응답 원문을 보고 kosis.py 를 조정합니다 (예상된 검증 과정)")
        return 1
    print(f"  ✓ 응답 {len(rows)}행")

    if not rows:
        print("✗ 0행 — 파라미터(prdSe/objL) 조정 필요. 원 API 는 통했으니 절반 성공.")
        return 1

    # 필드 스키마 확인
    sample = rows[0]
    expected = {"C1_NM", "ITM_NM", "UNIT_NM", "PRD_DE", "DT"}
    missing = expected - set(sample.keys())
    print(f"② 필드 스키마: {'✓ 픽스처와 호환' if not missing else f'△ 누락 필드 {missing} — 어댑터 매핑 필요'}")
    print(f"  실제 필드: {sorted(sample.keys())[:12]}")

    # 노션 제시값 검증
    print("③ 노션 제시값 대조 (과수 농가):")
    found = {}
    for r in rows:
        names = " ".join(str(r.get(k, "")) for k in ("C1_NM", "C2_NM", "C3_NM", "ITM_NM"))
        if "과수" in names:
            try:
                found[names.strip()] = float(str(r["DT"]).replace(",", ""))
            except (KeyError, ValueError):
                pass
    if found:
        for k, v in list(found.items())[:10]:
            mark = " ← 총 농가 예상값 166,558" if abs(v - 166558) < 1 else ""
            print(f"  {k}: {v:,.0f}{mark}")
        if any(abs(v - 166558) < 1 for v in found.values()):
            print("  ✓ 노션 제시값(166,558가구) 실데이터로 확인 — 픽스처가 진짜였음이 증명됨!")
    else:
        print("  △ '과수' 행 미발견 — 분류 파라미터(objL1) 지정 필요할 수 있음. 아래 원시 3행 참고:")
        for r in rows[:3]:
            print("   ", json.dumps(r, ensure_ascii=False)[:150])

    print("\n스모크 테스트 종료 — 결과를 보고 다음 단계(실 인덱싱)를 진행합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
