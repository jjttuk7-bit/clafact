from fastapi.testclient import TestClient
from backend.app.main import app
from clafact.service.store import Store

def test_register_official_notice_api(tmp_path, monkeypatch):
    db=tmp_path/'service.db'; monkeypatch.setenv('CLAFACT_SERVICE_DB',str(db))
    s=Store(db); s.upsert_article('a','t','2025-01-01','','u','b'); s.enqueue_claim('c','a','2025 인구주택총조사는 10월 22일부터 시행된다.',classification={'source_type':'OFFICIAL_ANNOUNCEMENT','route':'NON_KOSIS_QUEUE'}); s.close()
    r=TestClient(app).post('/internal/claims/c/official-notice',json={'organization':'통계청','url':'https://kostat.go.kr/notice','effective_date':'2025-10-22'})
    assert r.status_code == 200
    assert r.json()['label'] == 'match'
def test_get_official_notice_api_returns_registered_evidence(tmp_path, monkeypatch):
    db=tmp_path/'service.db'; monkeypatch.setenv('CLAFACT_SERVICE_DB',str(db))
    s=Store(db); s.upsert_article('a','t','2025-01-01','','u','b'); s.enqueue_claim('c','a','2025 인구주택총조사는 10월 22일부터 시행된다.',classification={'source_type':'OFFICIAL_ANNOUNCEMENT','route':'NON_KOSIS_QUEUE'}); s.register_official_notice('c','통계청','https://kostat.go.kr/notice','2025-10-22'); s.close()
    r=TestClient(app).get('/internal/claims/c/official-notice')
    assert r.status_code == 200
    assert r.json()['evidence']['official_notice'] == '통계청'
def test_official_notice_api_rejects_bad_targets_and_urls(tmp_path, monkeypatch):
    db = tmp_path / "service.db"; monkeypatch.setenv("CLAFACT_SERVICE_DB", str(db))
    s = Store(db); s.upsert_article("a", "t", "2025-01-01", "", "u", "b"); s.enqueue_claim("k", "a", "실업률은 3%다."); s.close()
    client = TestClient(app); payload = {"organization":"통계청", "url":"https://kostat.go.kr/n", "effective_date":"2025-10-22"}
    assert client.post("/internal/claims/missing/official-notice", json=payload).status_code == 404
    assert client.post("/internal/claims/k/official-notice", json=payload).status_code == 422
    assert client.post("/internal/claims/k/official-notice", json={**payload, "url":"ftp://bad"}).status_code == 422
    assert client.get("/internal/claims/k/official-notice").status_code == 422