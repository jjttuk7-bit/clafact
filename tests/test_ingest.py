"""Ingest 모듈 테스트 — 샘플 픽스처 기반 (실물 데이터셋 도착 전 검증)."""
from pathlib import Path

from clafact.pipeline.ingest import load_articles, clean_body, split_sentences

SAMPLE = Path(__file__).resolve().parents[1] / "data/samples/articles_sample.jsonl"


def test_load_and_filter():
    """본문 없음 제외 + 중복 URL 제거 → 5개 레코드 중 3개만 남는다"""
    arts = load_articles(SAMPLE)
    assert len(arts) == 3
    assert all(a.body for a in arts)


def test_korean_field_aliases():
    arts = load_articles(SAMPLE)
    a1 = arts[0]
    assert "과일 재배면적" in a1.title
    assert a1.date == "2025-03-14" and a1.label == "True"


def test_clean_body_removes_noise():
    """기자명·이메일·저작권 고지가 본문에서 제거된다"""
    arts = load_articles(SAMPLE)
    body = arts[0].body
    assert "기자" not in body and "@" not in body and "무단" not in body


def test_sentence_split():
    arts = load_articles(SAMPLE)
    sents = arts[0].sentences
    assert len(sents) == 3
    assert sents[1].startswith("2024년 국내 과수 농가")


def test_decimal_not_split():
    """소수점(7.2%)에서 문장이 잘리지 않는다"""
    sents = split_sentences("실업률은 7.2%로 상승했다. 경기 둔화 탓이다.")
    assert len(sents) == 2 and "7.2%" in sents[0]


if __name__ == "__main__":
    import sys, traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
        except Exception:
            failed += 1
            print(f"  FAIL  {fn.__name__}")
            traceback.print_exc()
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)


# --- 실물 데이터셋(크롤 페이지) 크롬 제거 ---
from clafact.pipeline.ingest import strip_site_chrome, section_from_url

CRAWLED = ("2026년 4월 20일(월) 신문구독 | English 조선경제 오피니언 정치 사회 "
           "수출 역대 최대 김철수 기자 입력 2025.01.01. 14:18 업데이트 2025.01.02. 02:53 5 "
           "정부가 CES 2025에 역대 최대 통합한국관을 마련한다고 밝혔다.")


def test_strip_site_chrome_removes_menu_and_stamps():
    """메뉴·크롤시점 날짜·업데이트 타임스탬프가 제거되고 본문만 남는다"""
    text, anchored = strip_site_chrome(CRAWLED)
    assert anchored is True
    assert text.startswith("정부가 CES 2025")
    assert "신문구독" not in text and "업데이트" not in text and "2026년 4월" not in text


def test_strip_site_chrome_no_anchor_returns_original():
    """앵커가 없으면 원문 유지 + anchored=False (수동 확인 대상 표시용)"""
    text, anchored = strip_site_chrome("실업률은 7.2%로 상승했다.")
    assert anchored is False and text == "실업률은 7.2%로 상승했다."


def test_section_from_url():
    assert section_from_url("https://www.chosun.com/economy/industry/2025/01/01/ABC/") == "economy"
    assert section_from_url("") == ""
