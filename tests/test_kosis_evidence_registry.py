from clafact.kosis_evidence_registry import build_evidence_registry_rows


def test_registry_rows_summarize_provenance_and_research_links():
    rows = build_evidence_registry_rows(
        evidence_objects=[{
            "evidence_id": "DT_1B040A3:total", "table_id": "DT_1B040A3", "title": "주민등록인구", "indicator": "총인구",
            "structure_type": "time_series", "definition_provenance": {
                "method": "meta_description", "approved_at": "2026-07-28T10:01:00+09:00",
            },
        }],
        snapshot_counts={"DT_1B040A3": 2},
        mapping_counts={"DT_1B040A3:total": 3},
        review_counts={"DT_1B040A3": 1},
    )

    assert rows == [{
        "근거 객체 ID": "DT_1B040A3:total",
        "통계표 ID": "DT_1B040A3",
        "표 제목": "주민등록인구",
        "핵심 지표": "총인구",
        "구조 유형": "시계열형",
        "정의 승인": "meta_description",
        "스냅샷": 2,
        "Shadow 연결": 3,
        "개정 검토": 1,
    }]
