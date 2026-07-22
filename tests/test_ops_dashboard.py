from clafact.ops_dashboard import build_ops_claim_rows


def test_build_ops_claim_rows_exposes_readable_status_and_hcx_signal() -> None:
    rows = build_ops_claim_rows([
        {
            "sentence": "실업률은 3.7%다.",
            "status": "PENDING",
            "label": None,
            "tier": None,
            "audit_json": '{"hcx_detection": {"mode": "live"}}',
            "error": None,
        }
    ])

    assert rows[0]["처리 상태"] == "● 대기"
    assert rows[0]["HCX 신호"] == "실시간 보조"
