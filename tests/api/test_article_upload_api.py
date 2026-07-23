from fastapi.testclient import TestClient

from backend.app.main import app
from clafact.service.store import Store


def test_csv_upload_api_registers_file_into_service_store(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "service.db"
    monkeypatch.setenv("CLAFACT_SERVICE_DB", str(db_path))
    content = (
        "제목,작성일,섹션,URL,본문\n"
        "실업률 변화,2025-01-20,경제,https://example.com/upload,실업률은 7.2%로 상승했다.\n"
    ).encode("utf-8-sig")

    response = TestClient(app).post(
        "/internal/articles/upload",
        content=content,
        headers={"content-type": "text/csv", "x-filename": "articles.csv"},
    )

    assert response.status_code == 200
    assert response.json()["read"] == 1
    assert response.json()["imported"] == 1
    assert response.json()["queued"] == 1
    store = Store(db_path)
    assert store.summary()["claims_by_status"] == {"PENDING": 1}
    store.close()
