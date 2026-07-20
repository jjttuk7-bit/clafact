"""Source Classification 테스트 — 라우팅 규칙(단위) + 정확도 하네스(eval).

단위 테스트: 분류기 로직이 기획 문서의 규칙대로 동작하는지 (결정적, 항상 실행).
정확도 테스트(@eval): 사람 라벨 시드가 있을 때만 — G-SOURCE-1 게이트 자동 판정.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from clafact.pipeline import source_classify as sc

REPO = Path(__file__).resolve().parents[1]
SEED = REPO / "data/goldenset/source_routing_seed.jsonl"


# ---------- 단위: 라벨별 대표 케이스 ----------

@pytest.mark.parametrize("sentence,expected", [
    ("지난해 실업률은 7.2%였다.", sc.KOSIS_DOMESTIC),
    ("서울 1인 가구가 150만을 넘어섰다.", sc.KOSIS_BUT_COMPLEX),   # 임계형 → complex
    ("소비자물가가 3.1% 올랐다.", sc.KOSIS_BUT_COMPLEX),           # 물가 도메인 → complex
    ("수출이 전년보다 8% 증가했다.", sc.OTHER_OFFICIAL),
    ("코스피가 3000선을 넘었다.", sc.PRIVATE_SOURCE),
    ("영업이익이 2조원을 기록했다.", sc.PRIVATE_SOURCE),
    ("유튜브 조회수가 1억회를 돌파했다.", sc.PLATFORM_SOURCE),
    ("내년 성장률은 3%로 전망된다.", sc.FORECAST_OR_OPINION),
    ("그 회사는 업계 최고 수준의 기술을 갖췄다.", sc.UNKNOWN),
])
def test_label_by_representative_case(sentence, expected):
    assert sc.classify(sentence).source_type == expected


def test_precision_first_ordering():
    """KOSIS 키워드와 비-KOSIS 키워드가 함께면 비-KOSIS가 이긴다 (KOSIS_precision 보호)."""
    # '고용'(KOSIS)과 '주가'(PRIVATE)가 한 문장 — 억지 KOSIS 매핑 금지
    label = sc.classify("고용 지표 발표에 주가가 3% 올랐다.")
    assert label.source_type == sc.PRIVATE_SOURCE


def test_forecast_beats_kosis():
    """전망형은 KOSIS 키워드가 있어도 검증 부적합으로 컷."""
    assert sc.classify("실업률이 내년 3%로 전망된다.").source_type == sc.FORECAST_OR_OPINION


@pytest.mark.parametrize("sentence", [
    "이날 발표된 지난해 일본 소비자물가지수는 전년 대비 2.5% 올랐다.",
    "지난해 9월 2.4%까지 떨어졌던 미국 소비자물가 상승률은 12월 2.9%까지 올랐다.",
    "작년 12월 소비자물가 상승률은 3%로 일본은행 목표치를 뛰어넘었다.",
    "OECD 평균 고용률은 70%를 기록했다.",
])
def test_overseas_guard(sentence):
    """규칙 A2-0014 — 해외 주체 주장은 국내 지표어가 있어도 KOSIS로 보내지 않는다.

    유래: 첫 실 판정 5건 중 3건이 해외 주장이었고 전부 오'불일치'였다
    (일본·미국 물가를 한국 소비자물가와 대조). 틀린 불일치는 최악의 오류다.
    """
    label = sc.classify(sentence)
    assert label.source_type == sc.OVERSEAS_SOURCE
    assert label.route == "OUT_OF_SCOPE"
    assert sc.kosis_query(sentence) == ""      # 검색 자체를 하지 않는다(예산·오판 방지)


def test_domestic_claim_still_passes():
    """국내 주장은 그대로 KOSIS 경로 — 해외 가드가 과잉 차단하지 않는지."""
    label = sc.classify("지난달 소비자물가가 전년 동월 대비 2.2% 올랐다.")
    assert label.source_type.startswith("KOSIS")


def test_claim_type_detection():
    assert sc.claim_type("출생아 수는 23만 명이었다.") == "규모형"
    assert sc.claim_type("농가 수가 4.9% 감소했다.") == "증감형"
    assert sc.claim_type("10곳 중 6곳이 고령이다.") == "파생계산형"
    assert sc.claim_type("1인 가구가 150만을 넘어섰다.") == "임계형"


def test_route_mapping():
    assert sc.classify("지난해 실업률은 7.2%였다.").route == "KOSIS_RETRIEVAL"
    assert sc.classify("코스피가 3000을 넘었다.").route == "NON_KOSIS_QUEUE"
    assert sc.classify("내년 3% 전망이다.").route == "OUT_OF_SCOPE"
    assert sc.classify("업계 최고 수준이다.").route == "HUMAN_REVIEW"


# ---------- 하네스: 지표 계산 자체 검증 (분류 정확도 아님) ----------

def test_routing_metrics_math():
    """지표 계산 로직 자체를 합성 데이터로 검증."""
    pairs = [
        (sc.KOSIS_DOMESTIC, sc.KOSIS_DOMESTIC),   # tp
        (sc.KOSIS_BUT_COMPLEX, sc.OTHER_OFFICIAL),  # fp — 억지 KOSIS 매핑
        (sc.OTHER_OFFICIAL, sc.KOSIS_DOMESTIC),   # fn — 놓친 KOSIS
        (sc.UNKNOWN, sc.UNKNOWN),
    ]
    m = sc.routing_metrics(pairs)
    assert m["n"] == 4
    assert m["kosis_precision"] == 0.5   # tp=1 / (tp=1+fp=1)
    assert m["kosis_recall"] == 0.5      # tp=1 / (tp=1+fn=1)
    assert m["unknown_rate"] == 0.25


# ---------- eval: 사람 라벨 시드 대비 정확도 (G-SOURCE-1 게이트) ----------

@pytest.mark.eval
def test_kosis_precision_gate():
    """사람 라벨 시드가 있으면 KOSIS_precision ≥ 0.80 게이트를 판정한다.

    시드는 사람이 만든다(W1). 없으면 skip — 게이트 미도달로 표시.
    시드 스키마: {"sentence": str, "gold_source_type": str}
    """
    if not SEED.exists():
        pytest.skip(f"라우팅 시드 없음: {SEED} — W1에서 사람 라벨 50건 작성 필요")
    rows = [json.loads(x) for x in SEED.read_text(encoding="utf-8").splitlines() if x.strip()]
    pairs = [(sc.classify(r["sentence"]).source_type, r["gold_source_type"]) for r in rows]
    m = sc.routing_metrics(pairs)
    print(f"\nG-SOURCE-1 지표: {m}")
    assert m["kosis_precision"] >= 0.80, f"KOSIS_precision {m['kosis_precision']} < 0.80"
