"""News-file registration boundary for the service queue."""
from __future__ import annotations

import csv
from pathlib import Path

from clafact.pipeline import detect
from clafact.pipeline.ingest import load_articles
from clafact.service.store import Store, stable_article_id, stable_claim_id


def _source_row_count(path: str | Path) -> int:
    path = Path(path)
    if path.suffix == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as file:
            return sum(1 for _ in csv.DictReader(file))
    if path.suffix == ".jsonl":
        with path.open(encoding="utf-8") as file:
            return sum(1 for line in file if line.strip())
    raise ValueError(f"지원하지 않는 형식: {path.suffix}")


def import_article_file(path: str | Path, store: Store, hcx_signal=None) -> dict[str, int]:
    """Store articles, queue claim candidates, and report pipeline counts."""
    source_rows = _source_row_count(path)
    articles = load_articles(path)
    imported = candidates = queued = sentences = 0
    exclusion_reasons: dict[str, int] = {}
    for article in articles:
        article_id = stable_article_id(article.url, article.title, article.date)
        if store.upsert_article(article_id, article.title, article.date, article.section, article.url, article.body):
            imported += 1
        for sentence in article.sentences:
            sentences += 1
            if not detect.is_candidate(sentence):
                continue
            candidates += 1
            audit = None
            if hcx_signal:
                try:
                    audit = {"hcx_detection": hcx_signal(sentence)}
                except Exception as error:
                    audit = {"hcx_detection": {"fallback": str(error)}}
            if store.enqueue_claim(stable_claim_id(article_id, sentence), article_id, sentence, audit=audit):
                queued += 1
    return {
        "source_rows": source_rows,
        "read": len(articles),
        "discarded_articles": source_rows - len(articles),
        "imported": imported,
        "duplicates": len(articles) - imported,
        "sentences": sentences,
        "candidates": candidates,
        "queued": queued,
        "excluded_candidates": sum(exclusion_reasons.values()),
        "exclusion_reasons": exclusion_reasons,
    }