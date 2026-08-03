import json

from clafact.kosis_catalog import save_catalog_snapshot


def test_save_catalog_snapshot_merges_tables_and_preserves_resume_queue(tmp_path):
    path = tmp_path / "catalog.json"

    first = save_catalog_snapshot(
        path, "MT_ZTITLE",
        {"tables": [{"TBL_ID": "T1", "TBL_NM": "첫 표"}], "pending_parent_ids": ["p2"]},
    )
    second = save_catalog_snapshot(
        path, "MT_ZTITLE",
        {"tables": [{"TBL_ID": "T1", "TBL_NM": "첫 표"}, {"TBL_ID": "T2", "TBL_NM": "둘째 표"}], "pending_parent_ids": ["p3"]},
    )

    assert first["table_count"] == 1
    assert second["table_count"] == 2
    assert second["pending_parent_ids"] == ["p3"]
    assert json.loads(path.read_text(encoding="utf-8"))["tables"][1]["TBL_ID"] == "T2"
