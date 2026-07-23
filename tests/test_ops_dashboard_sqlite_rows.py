import sqlite3

from clafact.ops_dashboard import build_ops_claim_rows


def test_build_ops_claim_rows_accepts_sqlite_rows() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            "SELECT '실업률은 3.7%다.' AS sentence, 'PENDING' AS status, "
            "NULL AS label, NULL AS tier, '{\"hcx_detection\": {\"mode\": \"live\"}}' AS audit_json, "
            "NULL AS error"
        ).fetchone()
    finally:
        connection.close()

    rows = build_ops_claim_rows([row])

    assert rows[0]["주장"] == "실업률은 3.7%다."
    assert rows[0]["HCX 신호"] == "실시간 보조"
