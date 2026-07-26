from pathlib import Path


def test_streamlit_exposes_a_separate_verification_lab_without_store_writes():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert '"검증 실험실"' in source
    assert 'NAV_ITEMS = ("운영 홈", "검증", "검증자 리뷰", "플라이휠", "자산 현황", "검증 실험실")' in source
    section = source[source.index('if view == "검증 실험실":'):source.index('# ═════════════ 탭 2: 검증자 리뷰')]
    assert "운영 Claim·리뷰 큐·판정 이력을 변경하지 않습니다" in section
    assert "run_comparison" in section
    assert "Python 규칙만" in section
    assert "LLM만" in section
    assert "하이브리드" in section
    assert 'st.file_uploader("검증 실험실 CSV 파일"' in section
    assert 'key="experiment_lab_csv"' in section
    assert 'csv.DictReader' in section
    assert '"기사 본문 전체"' in section
    assert '기사 선택' in section
    assert '자동 일괄 실행하지 않습니다' in section
    assert '전체 비교 실행' in section
    assert 'Python만 실행' in section
    assert 'LLM만 실행' in section
    assert '하이브리드만 실행' in section
    assert '방식별 판단 근거' in section
    assert '전체 비교 경과시간' in section
    assert "Store(" not in section
    assert "process_pending(" not in section
