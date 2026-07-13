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
