from backend.app.main import build_kosis_engine
from clafact.kosis import CachedKosisClient, FixtureKosisClient


def test_kosis_engine_defaults_to_fixture(monkeypatch) -> None:
    monkeypatch.delenv("CLAFACT_KOSIS_MODE", raising=False)

    _, client = build_kosis_engine()

    assert isinstance(client, FixtureKosisClient)


def test_kosis_engine_uses_cached_http_client_in_live_mode(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CLAFACT_KOSIS_MODE", "live")
    monkeypatch.setenv("KOSIS_API_KEY", "DUMMY")
    monkeypatch.setenv("CLAFACT_KOSIS_CACHE_DIR", str(tmp_path))

    _, client = build_kosis_engine()

    assert isinstance(client, CachedKosisClient)


def test_kosis_engine_falls_back_to_fixture_without_key(monkeypatch) -> None:
    monkeypatch.setenv("CLAFACT_KOSIS_MODE", "live")
    monkeypatch.delenv("KOSIS_API_KEY", raising=False)

    _, client = build_kosis_engine()

    assert isinstance(client, FixtureKosisClient)
