"""News-file registration boundary for the service queue."""
from __future__ import annotations

from pathlib import Path

from clafact.pipeline import detect
from clafact.pipeline.ingest import load_articles
from clafact.service.store import Store, stable_article_id, stable_claim_id


def import_article_file(path: str | Path, store: Store, hcx_signal=None) -> dict[str, int]:
    """Store articles and queue rule candidates with optional HCX audit signals."""
    articles = load_articles(path)
    imported = 0
    for article in articles:
        article_id = stable_article_id(article.url, article.title, article.date)
        if store.upsert_article(article_id, article.title, article.date, article.section, article.url, article.body):
            imported += 1
        for sentence in article.sentences:
            if detect.is_candidate(sentence):
                audit = None
                if hcx_signal:
                    try:
                        audit = {"hcx_detection": hcx_signal(sentence)}
                    except Exception as error:
                        audit = {"hcx_detection": {"fallback": str(error)}}
                store.enqueue_claim(stable_claim_id(article_id, sentence), article_id, sentence, audit=audit)
    return {"read": len(articles), "imported": imported, "duplicates": len(articles) - imported}