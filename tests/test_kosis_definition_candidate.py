import pytest

from clafact.kosis_definition_candidate import (
    extract_definition_candidate,
    validate_kosis_source_url,
)


def test_extracts_official_meta_description_as_reviewable_candidate():
    candidate = extract_definition_candidate(
        '<html><head><meta name="description" content="주민등록인구는 주민등록표에 등재된 인구를 말합니다."></head></html>',
        source_url="https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1B040A3",
    )

    assert candidate.text == "주민등록인구는 주민등록표에 등재된 인구를 말합니다."
    assert candidate.method == "meta_description"


def test_rejects_non_kosis_definition_source():
    with pytest.raises(ValueError, match="kosis.kr"):
        validate_kosis_source_url("https://example.com/table")
