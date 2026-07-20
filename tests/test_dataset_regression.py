"""실물 데이터셋 회귀 스위트 (@dataset) — 조선일보 CSV가 있을 때만 실행.

픽스처가 못 잡는 실물의 함정(사이트 크롬·댓글·푸터 잔여, 문장 분리 붕괴)을
불변식으로 고정한다. ingest 클리닝이 퇴행하면 여기서 잡힌다.

주의: 데이터셋은 저작권상 커밋 금지 → 본문을 픽스처로 박지 않고,
실물 CSV에 대한 '집계 불변식'만 검사한다(수치는 여유 범위로).
"""
from __future__ import annotations

import statistics

import pytest

from clafact.pipeline.detect import filter_sentences
from clafact.pipeline.ingest import load_articles

pytestmark = pytest.mark.dataset

# 크롬·댓글·푸터가 본문에 남으면 안 되는 마커 (하나라도 있으면 클리닝 퇴행)
LEAK_MARKERS = ["100자평", "By Taboola", "무단 전재", "Copyright 조선일보",
                "신문구독", "당신이 좋아할 만한 콘텐츠"]


@pytest.fixture(scope="module")
def articles(dataset_path):
    return load_articles(dataset_path)


def test_article_count_invariant(articles):
    """중복·빈본문 제외 후 2,600건 이상 적재 (2026-07-20 실측 2,649)."""
    assert len(articles) >= 2600, f"적재 {len(articles)}건 — 클리닝이 과도하게 버림?"


def test_body_length_reasonable(articles):
    """본문 중앙값이 기사 분량대(500~5000자)여야 — 크롬 미제거면 1만+, 과제거면 0대."""
    med = statistics.median(len(a.body) for a in articles)
    assert 500 <= med <= 5000, f"본문 중앙값 {med} — 크롬/푸터 처리 퇴행 의심"


def test_no_chrome_or_comment_leakage(articles):
    """본문에 사이트 크롬·독자 댓글·푸터 마커가 남지 않는다."""
    leaked = {}
    for a in articles:
        for mk in LEAK_MARKERS:
            if mk in a.body:
                leaked.setdefault(mk, 0)
                leaked[mk] += 1
    # 소량 잔존은 허용하되(개행 없는 특이 레이아웃), 대량 누수는 실패
    total = len(articles)
    for mk, cnt in leaked.items():
        assert cnt / total < 0.03, f"'{mk}' 누수 {cnt}/{total} — 클리닝 퇴행"


def test_section_derived_from_url(articles):
    """섹션 컬럼이 없어도 URL에서 economy가 유도된다 (다수가 경제면)."""
    secs = [a.section for a in articles if a.section]
    assert secs, "섹션 유도 실패 — section_from_url 퇴행"
    assert secs.count("economy") / len(secs) > 0.5


def test_detection_yield_invariant(articles):
    """전수 탐지가 기사당 3~10건 범위 (2026-07-20 실측 6.2). 붕괴 시 경보."""
    total = sum(len(filter_sentences(a.sentences)) for a in articles)
    per = total / len(articles)
    assert 3.0 <= per <= 10.0, f"기사당 후보 {per:.2f} — 탐지·문장분리 퇴행 의심"
    assert total >= 10000, f"총 후보 {total} — 급감"
