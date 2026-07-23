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

def test_import_routes_only_kosis_claims_to_pending_and_preserves_other_numeric_claims(tmp_path) -> None:
    source = tmp_path / "routing.csv"
    with source.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["제목", "작성일", "URL", "본문"])
        writer.writeheader()
        writer.writerow({
            "제목": "분류 기사", "작성일": "2025-02-05", "URL": "https://x/routing",
            "본문": (
                "지난달 소비자물가가 전년 동월 대비 2.2% 올랐다. "
                "코스피가 3% 올랐다. 일본 소비자물가가 2.5% 올랐다. "
                "내년 성장률은 3%로 전망된다."
            ),
        })

    store = Store(":memory:")
    result = import_article_file(source, store)
    rows = store.conn.execute("SELECT sentence, status, source_type, route FROM claims ORDER BY sentence").fetchall()

    assert result["candidates"] == 4
    assert result["queued"] == 1
    assert result["classified"] == 3
    assert result["routes"] == {"KOSIS_RETRIEVAL": 1, "NON_KOSIS_QUEUE": 1, "OUT_OF_SCOPE": 2}
    assert {(row["source_type"], row["status"], row["route"]) for row in rows} == {
        ("KOSIS_BUT_COMPLEX", "PENDING", "KOSIS_RETRIEVAL"),
        ("PRIVATE_SOURCE", "CLASSIFIED", "NON_KOSIS_QUEUE"),
        ("OVERSEAS_SOURCE", "CLASSIFIED", "OUT_OF_SCOPE"),
        ("FORECAST_OR_OPINION", "CLASSIFIED", "OUT_OF_SCOPE"),
    }
    store.close()