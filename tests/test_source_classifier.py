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
    # 재분류(2026-08-04): 무역통계도 KOSIS(관세청 산하 DT_134001_002 등)로 실제 조회된다 —
    # routing_v01.json "_reclassification_note" 참조.
    ("수출이 전년보다 8% 증가했다.", sc.KOSIS_BUT_COMPLEX),
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


def test_domestic_overseas_activity_is_not_overseas_source():
    """실측 발견(2026-08-04): '해외건설'처럼 한국 정부가 집계하는 국내 통계가
    '해외' 마커에 걸려 OVERSEAS_SOURCE로 잘못 빠졌다."""
    label = sc.classify("국토교통부는 해외 건설 누적 수주액이 1조달러를 돌파했다고 밝혔다.")
    assert label.source_type == sc.KOSIS_BUT_COMPLEX
    assert label.domain == "construction"


def test_specific_kosis_compound_beats_generic_private_keyword():
    """실측 발견(2026-08-04): private_source의 짧은 일반어('수주')가 KOSIS 쪽의
    훨씬 구체적인 복합어('해외건설')와 충돌하면, 더 구체적인 쪽이 이겨야 한다
    — 개별 기업 실적과 정부 집계가 같은 낱말을 쓰는 게 흔하기 때문이다."""
    label = sc.classify("올해 해외건설 수주액은 역대 최대를 기록했다.")
    assert label.source_type.startswith("KOSIS")
    assert label.domain == "construction"


def test_precision_first_ordering_survives_specificity_change():
    """길이 기반 우선순위를 넣은 뒤에도, 길이가 같으면 기존 KOSIS_precision
    우선 규칙(비-KOSIS 우승)이 그대로 유지돼야 한다."""
    label = sc.classify("고용 지표 발표에 주가가 3% 올랐다.")
    assert label.source_type == sc.PRIVATE_SOURCE


def test_official_announcement_is_not_sent_to_kosis():
    """Official survey schedules use announcement evidence, not KOSIS tables."""
    sentence = "2025 인구주택총조사는 10월 22일부터 시행된다."

    label = sc.classify(sentence)

    assert label.source_type == sc.OFFICIAL_ANNOUNCEMENT
    assert label.route == "NON_KOSIS_QUEUE"
    assert sc.kosis_query(sentence) == ""


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

def test_complex_kosis_claim_stays_in_kosis_analysis_route():
    label = sc.classify("소비자물가지수는 117.42(2020년=100)다.")

    assert label.source_type == sc.KOSIS_BUT_COMPLEX
    assert label.route == "KOSIS_RETRIEVAL"


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


def test_kosis_queries_adds_a_compact_population_hint():
    assert sc.kosis_queries("지난 8월 출생아 수는 2만867명이다.") == ["출생아", "인구동향"]


def test_kosis_queries_adds_a_compact_labor_hint():
    assert sc.kosis_queries("3분기 청년 실업률은 5.1%다.") == ["실업률", "경제활동인구"]



@pytest.mark.parametrize("sentence", [
    "해외 소비자물가가 3% 상승했다.",
    "해외 경제성장률이 둔화됐다.",
    "해외 실업률이 상승했다.",
])
def test_generic_overseas_indicators_do_not_enter_kosis(sentence):
    label = sc.classify(sentence)
    assert label.source_type == sc.OVERSEAS_SOURCE
    assert label.route == "OUT_OF_SCOPE"
    assert sc.kosis_query(sentence) == ""


@pytest.mark.parametrize("sentence", [
    "해외건설 수주액이 증가했다.",
    "해외직접투자가 늘었다.",
    "해외여행객 수가 증가했다.",
])
def test_domestic_overseas_activities_keep_kosis_review_route(sentence):
    label = sc.classify(sentence)
    assert label.source_type == sc.KOSIS_BUT_COMPLEX
    assert label.route == "KOSIS_RETRIEVAL"
