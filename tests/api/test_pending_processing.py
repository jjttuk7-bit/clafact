from fastapi.testclient import TestClient

from backend.app.main import app
from clafact.service.store import PENDING, Store


def _enqueue_pending_claim(db_path, claim_id: str = "clm_pending") -> str:
    store = Store(db_path)
    article_id = f"art_{claim_id}"
    store.upsert_article(
        article_id, "비트코인", "2025-06-20", "경제", f"https://example.com/{claim_id}", "본문"
    )
    store.enqueue_claim(claim_id, article_id, "비트코인 가격이 1억 원을 넘어섰다.")
    store.close()
    return claim_id


def test_process_pending_endpoint_consumes_queued_claim(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "service.db"
    claim_id = _enqueue_pending_claim(db_path)
    monkeypatch.setenv("CLAFACT_SERVICE_DB", str(db_path))

    with TestClient(app) as client:
        response = client.post("/internal/batches/process-pending", json={})

    assert response.status_code == 200
    assert response.json()["processed"] == 1
    store = Store(db_path)
    claim = store.conn.execute(
        "SELECT status FROM claims WHERE claim_id = ?", (claim_id,)
    ).fetchone()
    assert claim["status"] != PENDING
    store.close()


def test_process_pending_respects_limit(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "service.db"
    _enqueue_pending_claim(db_path, "clm_first")
    _enqueue_pending_claim(db_path, "clm_second")
    monkeypatch.setenv("CLAFACT_SERVICE_DB", str(db_path))

    with TestClient(app) as client:
        response = client.post("/internal/batches/process-pending", json={"limit": 1})

    assert response.status_code == 200
    assert response.json()["processed"] == 1
    store = Store(db_path)
    pending = store.conn.execute(
        "SELECT COUNT(*) AS count FROM claims WHERE status = ?", (PENDING,)
    ).fetchone()
    assert pending["count"] == 1
    store.close()