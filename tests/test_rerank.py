"""통계표 재순위 테스트 — 실 KOSIS 응답('소비자물가' 10건, 2026-07-20)을 픽스처로.

유래: RANK 1위가 지역·연간표(e-지방지표)였고, 월간 주장에 맞는
'월별 소비자물가 등락률'(DT_1J22042)은 7위에 있어 오'불일치'가 났다.
"""
from __future__ import annotations

from clafact.pipeline.rerank import rerank_rows, score_row

# 실 응답에서 발췌 (필드명·값 그대로)
ROWS = [
    {"TBL_ID": "DT_1YL20581", "TBL_NM": "소비자물가 등락률(시도/시)",
     "STAT_NM": "e-지방지표", "VW_CD": "MT_GTITLE01", "MT_ATITLE": "주제별 > 소득과 소비"},
    {"TBL_ID": "DT_1J22041", "TBL_NM": "연도별 소비자물가 등락률",
     "STAT_NM": "소비자물가조사", "VW_CD": "MT_ZTITLE",
     "MT_ATITLE": "물가 > 소비자물가조사", "STRT_PRD_DE": "1966", "END_PRD_DE": "2025"},
    {"TBL_ID": "DT_2WEO011", "TBL_NM": "물가상승률, 소비자물가지수",
     "STAT_NM": "IMF", "VW_CD": "MT_RTITLE",
     "MT_ATITLE": "국제기구별 통계 > IMF > 세계경제전망"},
    {"TBL_ID": "DT_1J22042", "TBL_NM": "월별 소비자물가 등락률",
     "STAT_NM": "소비자물가조사", "VW_CD": "MT_ZTITLE",
     "MT_ATITLE": "물가 > 소비자물가조사", "STRT_PRD_DE": "1965", "END_PRD_DE": "2026"},
    {"TBL_ID": "DT_2STES047", "TBL_NM": "주요 단기 경제 지표 > 소비자 물가",
     "STAT_NM": "OECD", "VW_CD": "MT_RTITLE", "MT_ATITLE": "국제기구별 통계 > OECD"},
]

MONTHLY_CLAIM = "통계청은 1월 소비자물가 동향에서 지난달 소비자물가가 작년 같은 달보다 2.2% 올랐다고 밝혔다."
ANNUAL_CLAIM = "지난해 연간 소비자물가 상승률은 2.3%였다."
REGION_CLAIM = "서울의 소비자물가가 지난해 2.5% 올랐다."


def test_monthly_claim_picks_monthly_table():
    """월간 주장 → '월별 소비자물가 등락률'이 1위로 올라온다 (원래 4번째)."""
    ranked = rerank_rows(ROWS, MONTHLY_CLAIM, "202501")
    assert ranked[0]["TBL_ID"] == "DT_1J22042"


def test_annual_claim_picks_annual_table():
    """연간 주장 → '연도별 소비자물가 등락률'."""
    ranked = rerank_rows(ROWS, ANNUAL_CLAIM, "2024")
    assert ranked[0]["TBL_ID"] == "DT_1J22041"


def test_international_tables_are_demoted():
    """IMF·OECD 표는 국내 주장에서 하위로 밀린다."""
    ranked = rerank_rows(ROWS, MONTHLY_CLAIM, "202501")
    intl_pos = [i for i, r in enumerate(ranked) if r["STAT_NM"] in ("IMF", "OECD")]
    assert min(intl_pos) >= 3, "국제기구 표가 상위에 오면 안 된다"


def test_regional_table_demoted_for_national_claim():
    """전국 주장에서는 지역표(e-지방지표)가 1위가 아니다 — 실측 오판의 원인."""
    ranked = rerank_rows(ROWS, MONTHLY_CLAIM, "202501")
    assert ranked[0]["TBL_ID"] != "DT_1YL20581"


def test_regional_table_preferred_for_regional_claim():
    """반대로 지역을 말하는 주장에서는 지역표가 유리해야 한다."""
    s_region, _ = score_row(ROWS[0], REGION_CLAIM, "2024")
    s_national, _ = score_row(ROWS[0], ANNUAL_CLAIM, "2024")
    assert s_region > s_national


def test_reasons_are_recorded():
    """왜 그 표를 골랐는지 근거가 남는다 (감사 추적)."""
    ranked = rerank_rows(ROWS, MONTHLY_CLAIM, "202501")
    assert ranked[0]["_rerank_why"], "선택 근거가 비면 안 된다"
    assert "_orig_rank" in ranked[0]


def test_stable_when_no_signal():
    """신호가 없으면 원래 RANK 순서를 지킨다(임의 뒤섞기 금지)."""
    plain = [{"TBL_ID": f"T{i}", "TBL_NM": f"표{i}"} for i in range(5)]
    ranked = rerank_rows(plain, "숫자 없는 문장", "")
    assert [r["TBL_ID"] for r in ranked] == [f"T{i}" for i in range(5)]


def test_rerank_prefers_youth_table_for_youth_unemployment_claim():
    rows = [
        {"TBL_ID": "ALL", "TBL_NM": "실업률", "STAT_NM": "경제활동인구조사"},
        {"TBL_ID": "YOUTH", "TBL_NM": "청년층 실업률", "STAT_NM": "경제활동인구조사"},
    ]
    assert rerank_rows(rows, "3분기 청년 실업률은 5.1%다.")[0]["TBL_ID"] == "YOUTH"
