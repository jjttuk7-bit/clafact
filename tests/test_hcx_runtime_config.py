from __future__ import annotations

from clafact import llm


def _runtime_status(env: dict[str, str]) -> str:
    return getattr(llm, "hcx_runtime_status", lambda _env: "not_implemented")(env)


def test_hcx_runtime_defaults_to_live_when_key_is_configured():
    assert _runtime_status({"HCX_API_KEY": "configured-key"}) == "live"


def test_hcx_runtime_allows_explicit_fixture_opt_out():
    assert _runtime_status(
        {"HCX_API_KEY": "configured-key", "CLAFACT_HCX_MODE": "fixture"}
    ) == "fixture"


def test_hcx_runtime_reports_missing_key_in_live_mode():
    assert _runtime_status({"CLAFACT_HCX_MODE": "live"}) == "missing_key"