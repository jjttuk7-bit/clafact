from clafact.kosis_organization import normalize_kosis_organization


def test_normalizes_legacy_statistics_korea_name_to_current_agency_name():
    assert normalize_kosis_organization("통계청") == "국가데이터처"


def test_preserves_other_statistical_authorities():
    assert normalize_kosis_organization("한국은행") == "한국은행"
