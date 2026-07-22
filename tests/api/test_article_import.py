import json

from backend.app.ingest_service import import_article_file
from clafact.service.store import PENDING, Store


def test_import_article_file_persists_clean_articles_and_pending_claims(tmp_path) -> None:
    source = tmp_path / "articles.jsonl"
    source.write_text(
        json.dumps(
            {
                "제목": "실업률 변화",
                "작성일": "2025-01-20",
                "섹션": "경제",
                "URL": "https://example.com/a1",
                "본문": "실업률은 7.2%로 상승했다. 홍길동 기자 gildong@example.com",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    store = Store(":memory:")

    first = import_article_file(source, store)
    second = import_article_file(source, store)

    assert first == {"read": 1, "imported": 1, "duplicates": 0}
    assert second == {"read": 1, "imported": 0, "duplicates": 1}
    assert store.summary()["articles"] == 1
    article = store.conn.execute("SELECT title, body FROM articles").fetchone()
    claim = store.conn.execute(
        "SELECT status, label, processed_at FROM claims"
    ).fetchone()
    assert article["title"] == "실업률 변화"
    assert "기자" not in article["body"]
    assert claim["status"] == PENDING
    assert claim["label"] is None
    assert claim["processed_at"] is None

    store.close()
