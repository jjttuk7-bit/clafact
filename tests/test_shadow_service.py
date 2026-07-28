from clafact.pipeline.detect_llm import HcxDecision
from clafact.shadow_policy import ShadowPolicy
from clafact.shadow_service import ShadowLabService


def _judge(_: str) -> HcxDecision:
    return HcxDecision(False, "제외", "unknown", "", [])


def test_service_executes_persists_and_returns_decoded_run(tmp_path):
    with ShadowLabService(tmp_path / "shadow_lab.db") as service:
        result = service.execute(
            "2025년 인구는 5,000만 명이다.",
            "2026-07-28",
            ShadowPolicy.default(),
            judge_fn=_judge,
            run_id="shadow-service-1",
            created_at="2026-07-28T10:00:00+09:00",
        )

        assert result["run_id"] == "shadow-service-1"
        assert result["inserted"] is True
        assert result["summary"]["row_count"] == 1
        saved = service.get_run("shadow-service-1")
        assert saved["policy"]["version"] == "shadow-policy-v1"
        assert saved["rows"][0]["baseline"]["python_candidate"] is True
        assert "candidate_conflict" in saved["rows"][0]["risk_reasons"]


def test_service_keeps_review_history_outside_operating_store(tmp_path):
    with ShadowLabService(tmp_path / "shadow_lab.db") as service:
        service.execute(
            "2025년 인구는 5,000만 명이다.", "2026-07-28", ShadowPolicy.default(),
            judge_fn=_judge, run_id="shadow-service-2", created_at="2026-07-28T10:00:00+09:00",
        )

        assert service.review(
            "shadow-service-2", 1, action="hold", note="시간 기준 확인", reviewed_at="2026-07-28T10:01:00+09:00"
        ) is True
        assert service.get_run("shadow-service-2")["rows"][0]["review_state"] == "reviewed"
