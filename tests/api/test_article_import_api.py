import json

from fastapi.testclient import TestClient

from backend.app.main import app
from clafact.service.store import Store


def test_article_import_api_registers_file_into_service_store(tmp_path, monkeypatch) -> None:
    source = tmp_path / "articles.jsonl"
    source.write_text(
        json.dumps(
            {
                "제목": "실업률 변화",
                "작성일": "2025-01-20",
                "섹션": "경제",
                "URL": "https://example.com/a1",
                "본문": "실업률은 7.2%로 상승했다.",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    db_path = tmp_path / "service.db"
    monkeypatch.setenv("CLAFACT_SERVICE_DB", str(db_path))

    response = TestClient(app).post(
        "/internal/articles/import",
        json={"path": str(source)},
    )

    assert response.status_code == 200
    assert response.json() == {"read": 1, "imported": 1, "duplicates": 0}

    store = Store(db_path)
    assert store.summary()["articles"] == 1
    assert store.summary()["claims_by_status"] == {"PENDING": 1}
    store.close()


def test_article_import_api_records_hcx_live_signal(tmp_path, monkeypatch) -> None:
    source = tmp_path / "articles-hcx.jsonl"
    source.write_text(json.dumps({"제목": "실업률", "작성일": "2025-01-20", "URL": "https://example.com/hcx", "본문": "실업률은 7.2%로 상승했다."}, ensure_ascii=False) + "\n", encoding="utf-8")
    db_path = tmp_path / "service.db"
    monkeypatch.setenv("CLAFACT_SERVICE_DB", str(db_path))
    monkeypatch.setenv("CLAFACT_HCX_MODE", "live")
    monkeypatch.setattr("backend.app.main.hcx_detection_signal", lambda sentence: {"verifiable": True, "mode": "live"})
    response = TestClient(app).post("/internal/articles/import", json={"path": str(source)})
    assert response.status_code == 200
    store = Store(db_path)
    assert json.loads(store.conn.execute("SELECT audit_json FROM claims").fetchone()["audit_json"])["hcx_detection"]["mode"] == "live"
    store.close()
