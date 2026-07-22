import json

from backend.app.ingest_service import import_article_file
from clafact.service.store import Store


def test_import_records_hcx_detection_signal_without_dropping_claim(tmp_path) -> None:
    source = tmp_path / "article.jsonl"
    source.write_text(json.dumps({"제목": "실업률", "작성일": "2025-01-20", "URL": "https://x/a", "본문": "실업률은 7.2%로 상승했다."}, ensure_ascii=False) + "\n", encoding="utf-8")
    store = Store(":memory:")

    import_article_file(source, store, hcx_signal=lambda sentence: {"verifiable": False, "mode": "live"})

    row = store.conn.execute("SELECT status, audit_json FROM claims").fetchone()
    assert row["status"] == "PENDING"
    assert json.loads(row["audit_json"])["hcx_detection"]["verifiable"] is False
    store.close()


def test_import_keeps_claim_when_hcx_signal_raises(tmp_path) -> None:
    source = tmp_path / "article-fallback.jsonl"
    source.write_text(json.dumps({"제목": "실업률", "작성일": "2025-01-20", "URL": "https://x/b", "본문": "실업률은 7.2%로 상승했다."}, ensure_ascii=False) + "\n", encoding="utf-8")
    store = Store(":memory:")

    def unavailable(sentence):
        raise RuntimeError("HCX timeout")

    import_article_file(source, store, hcx_signal=unavailable)

    row = store.conn.execute("SELECT status, audit_json FROM claims").fetchone()
    assert row["status"] == "PENDING"
    assert json.loads(row["audit_json"])["hcx_detection"]["fallback"] == "HCX timeout"
    store.close()
