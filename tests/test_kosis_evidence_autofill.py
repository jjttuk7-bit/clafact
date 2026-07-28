from clafact.kosis_evidence_autofill import autofill_from_rows, parse_kosis_table_identity


def test_parse_kosis_table_identity_from_source_url():
    identity = parse_kosis_table_identity(
        "DT_1B040A3",
        "https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1B040A3",
    )

    assert identity.org_id == "101"
    assert identity.table_id == "DT_1B040A3"


def test_autofill_uses_official_row_labels_without_inventing_definition():
    fields = autofill_from_rows(
        table_id="DT_1B040A3",
        rows=[{
            "TBL_NM": "주민등록인구", "ORG_NM": "통계청", "ITM_NM": "총인구",
            "C1_OBJ_NM": "시도", "C1_NM": "전국", "C2_OBJ_NM": "성별", "C2_NM": "계",
            "PRD_SE": "Y", "UNIT_NM": "명",
        }],
    )

    assert fields.title == "주민등록인구"
    assert fields.dimensions == "시도, 성별"
    assert fields.source_selection == "시도=전국;성별=계"
    assert fields.time_dimension == "연"
    assert fields.definition == ""
