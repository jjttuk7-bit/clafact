import csv

from backend.app.ingest_service import import_article_file
from clafact.service.store import Store


def test_import_reports_pipeline_counts(tmp_path) -> None:
    source = tmp_path / "articles.csv"
    with source.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["제목", "작성일", "URL", "본문"])
        writer.writeheader()
        writer.writerow({"제목": "유효 기사", "작성일": "2025-01-01", "URL": "https://x/1", "본문": "실업률은 7.2%로 상승했다."})
        writer.writerow({"제목": "빈 기사", "작성일": "2025-01-01", "URL": "https://x/2", "본문": ""})

    store = Store(":memory:")
    result = import_article_file(source, store)

    assert result["source_rows"] == 2
    assert result["read"] == 1
    assert result["discarded_articles"] == 1
    assert result["sentences"] == 1
    assert result["candidates"] == 1
    assert result["queued"] == 1
    store.close()