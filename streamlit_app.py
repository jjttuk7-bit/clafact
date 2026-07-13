"""ClaFact MVP — Streamlit 데모 (Community Cloud 배포용).

로컬 실행:  streamlit run streamlit_app.py
배포:       share.streamlit.io 에서 이 레포 연결 (main file: streamlit_app.py)

파이프라인은 scripts/demo_server.py 와 동일한 verify_article 을 사용한다.
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clafact.kosis import FixtureKosisClient
from clafact.pipeline.retrieve import StatIndex
from clafact.pipeline.run import verify_article

ROOT = Path(__file__).resolve().parent

SAMPLES = {
    "과수 농가 고령화 (파생 계산)": {
        "date": "2025-03-14",
        "text": "농가 고령화가 이어지면서 올해 과일 재배면적이 1% 줄었다. 2024년 국내 과수 농가의 65세 이상 비율은 64.2%로 나타났다.",
    },
    "실업률 왜곡 (불일치)": {
        "date": "2025-06-20",
        "text": "올해 실업률이 10%에 달했다. 전문가들은 경기 둔화의 영향이라고 분석했다. 경제 상황이 크게 악화되었다.",
    },
    "1인 가구·출생아 (임계·환산)": {
        "date": "2025-06-02",
        "text": "서울의 1인 가구는 150만 가구를 넘어섰다. 지난해 출생아 수는 23만 명으로 역대 최저를 기록했다. 내년 경제성장률은 3%에 이를 전망이다.",
    },
}

STYLE = {
    "match": ("🟢 일치", "#2E8B57"),
    "mismatch": ("🔴 불일치", "#C0392B"),
    "unverifiable": ("⚪ 판단불가", "#8A8F98"),
}


@st.cache_resource
def load_engine():
    return (StatIndex(ROOT / "data/samples/kosis/tables_meta.json"),
            FixtureKosisClient(ROOT / "data/samples/kosis"))


st.set_page_config(page_title="ClaFact — 뉴스 수치 검증 MVP", page_icon="🔎", layout="centered")

st.title("🔎 ClaFact")
st.markdown("**뉴스 속 수치 주장을 국가통계(KOSIS)로 자동 검증합니다** — "
            "근거 없으면 판정하지 않습니다(판단불가 우선), 판정은 결정적 로직(환각 0)")

# 샘플 선택 — 위젯 key 에 직접 바인딩 (버튼이 위젯보다 먼저 실행되어야 반영됨)
st.session_state.setdefault("text", "")
st.session_state.setdefault("date", "2025-07-14")
clicked_sample = False
cols = st.columns(len(SAMPLES))
for col, (name, s) in zip(cols, SAMPLES.items()):
    if col.button(name, use_container_width=True):
        st.session_state["text"] = s["text"]
        st.session_state["date"] = s["date"]
        clicked_sample = True

text = st.text_area("기사 본문", key="text", height=140,
                    placeholder="기사 본문을 붙여넣으세요...")
date = st.text_input("기사 작성일 (YYYY-MM-DD)", key="date")

# 샘플 버튼은 클릭 즉시 검증까지 실행
if (st.button("검증하기", type="primary", use_container_width=True) or clicked_sample) and text.strip():
    idx, client = load_engine()
    results = [r for r in verify_article(text, date, idx, client) if r.label != "not_claim"]

    n = {k: sum(1 for r in results if r.label == k) for k in ("match", "mismatch", "unverifiable")}
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("검증 대상 주장", len(results))
    m2.metric("일치", n["match"])
    m3.metric("불일치", n["mismatch"])
    m4.metric("판단불가", n["unverifiable"])

    for r in results:
        label_ko, color = STYLE[r.label]
        chips = []
        if r.confidence:
            warn = " · 리뷰 최우선" if r.confidence == "low" else ""
            chips.append(f"신뢰도 {r.confidence}{warn}")
        if r.period:
            chips.append(f"시점 {r.period}")
        if r.quantity:
            chips.append(f"주장 수치 {r.quantity}")
        st.markdown(
            f"""<div style="border:1px solid #DDE5EF;border-left:6px solid {color};
            border-radius:10px;padding:14px 16px;margin:10px 0;background:#fff">
            <b style="color:{color}">{label_ko}</b>
            &nbsp;<span style="font-size:12px;color:#5A6B85">{" · ".join(chips)}</span>
            <div style="font-weight:bold;margin:6px 0">{r.sentence}</div>
            {f'<div style="font-size:13px;color:#5A6B85">근거: {r.evidence.get("tbl","")} → <b>{r.evidence.get("value","")}</b></div>' if r.evidence else ""}
            <div style="font-size:13px;color:#44546A;background:#F6F8FB;border-radius:8px;
            padding:10px;margin-top:8px;line-height:1.6">{r.explanation}</div>
            </div>""",
            unsafe_allow_html=True,
        )
        if r.notes:
            st.caption("⚠ " + " / ".join(r.notes))

st.divider()
st.caption("ClaBi × AIFFELTHON | 실데이터 검증 완료 (2026-07-14, KOSIS 실 API — 과수 농가 166,558가구 실증) | "
           "최종 판단은 검증자 리뷰로 확정")
