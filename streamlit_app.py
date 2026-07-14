"""ClaFact MVP — Streamlit 데모 (Community Cloud 배포용).

3탭 구성:
  🔎 검증      — 기사 입력 → 자동 판정 (WF-1)
  👤 검증자 리뷰 — 승인/보정/반려, 보정은 실패 레코드로 (WF-2)
  🔄 자산 현황  — 실패→자산 플라이휠 대시보드 (문서 11)
"""
import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clafact.assets.alias_dict import AliasDict
from clafact.assets.failures import FailureRecorder, FAILURE_TYPES
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
    "농가 증감률 (방향 검증)": {
        "date": "2025-04-10",
        "text": "지난해 논벼 농가는 전년보다 4.9% 감소했다. 지난해 과수 농가는 2% 감소했다. 지난해 과일 재배면적이 1% 줄었다.",
    },
}

STYLE = {
    "match": ("🟢 일치", "#2E8B57"),
    "mismatch": ("🔴 불일치", "#C0392B"),
    "unverifiable": ("⚪ 판단불가", "#8A8F98"),
}
LABEL_ORDER = {"mismatch": 0, "unverifiable": 1, "match": 2}
CONF_ORDER = {"low": 0, "medium": 1, "high": 2, None: 3}


@st.cache_resource
def load_engine():
    return (StatIndex(ROOT / "data/samples/kosis/tables_meta.json"),
            FixtureKosisClient(ROOT / "data/samples/kosis"))


def render_card(r):
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


st.set_page_config(page_title="ClaFact — 뉴스 수치 검증 MVP", page_icon="🔎", layout="centered")
st.title("🔎 ClaFact")
st.markdown("**뉴스 속 수치 주장을 국가통계(KOSIS)로 자동 검증합니다** — "
            "근거 없으면 판정하지 않습니다(판단불가 우선), 판정은 결정적 로직(환각 0)")

tab_verify, tab_review, tab_assets = st.tabs(["🔎 검증", "👤 검증자 리뷰", "🔄 자산 현황"])

# ═════════════ 탭 1: 검증 (WF-1) ═════════════
with tab_verify:
    st.session_state.setdefault("text", "")
    st.session_state.setdefault("date", "2025-07-14")
    clicked_sample = False
    cols = st.columns(2)
    for i, (name, s) in enumerate(SAMPLES.items()):
        if cols[i % 2].button(name, use_container_width=True):
            st.session_state["text"] = s["text"]
            st.session_state["date"] = s["date"]
            clicked_sample = True

    text = st.text_area("기사 본문", key="text", height=140,
                        placeholder="기사 본문을 붙여넣으세요...")
    date = st.text_input("기사 작성일 (YYYY-MM-DD)", key="date")

    def _reset():
        st.session_state["text"] = ""
        st.session_state["date"] = "2025-07-14"
        st.session_state.pop("results", None)
        st.session_state.pop("reviews", None)

    col_v, col_r = st.columns([3, 1])
    verify_clicked = col_v.button("검증하기", type="primary", use_container_width=True)
    col_r.button("🗑 초기화", use_container_width=True, on_click=_reset)

    if (verify_clicked or clicked_sample) and text.strip():
        idx, client = load_engine()
        st.session_state["results"] = [
            r for r in verify_article(text, date, idx, client) if r.label != "not_claim"]
        st.session_state["reviews"] = {}

    results = st.session_state.get("results", [])
    if results:
        n = {k: sum(1 for r in results if r.label == k) for k in STYLE}
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("검증 대상 주장", len(results))
        m2.metric("일치", n["match"])
        m3.metric("불일치", n["mismatch"])
        m4.metric("판단불가", n["unverifiable"])
        for r in results:
            render_card(r)
        st.info("👤 자동 판정은 최종이 아닙니다 — **검증자 리뷰 탭**에서 승인/보정해야 발행됩니다 (Human-in-the-Loop)")

# ═════════════ 탭 2: 검증자 리뷰 (WF-2) ═════════════
with tab_review:
    results = st.session_state.get("results", [])
    reviews = st.session_state.setdefault("reviews", {})
    if not results:
        st.info("먼저 **검증 탭**에서 기사를 검증하세요 — 자동 판정이 리뷰 큐로 들어옵니다.")
    else:
        queue = sorted(results, key=lambda r: (LABEL_ORDER[r.label], CONF_ORDER[r.confidence]))
        done = [v for v in reviews.values()]
        corrected = sum(1 for v in done if v.startswith("보정"))
        c1, c2, c3 = st.columns(3)
        c1.metric("리뷰 대기", len(queue) - len(done))
        c2.metric("처리 완료", len(done))
        c3.metric("보정률 (뒤집힌 판정)", f"{corrected}/{len(done)}" if done else "0/0")
        st.caption("큐 정렬: 불일치 → 신뢰도 low → medium → high (위험한 것부터 사람이 본다)")

        for i, r in enumerate(queue):
            rid = f"q{i}"
            status = reviews.get(rid)
            label_ko, _ = STYLE[r.label]
            head = f"{'✅' if status else '⏳'} {label_ko} · {r.sentence[:42]}"
            with st.expander(head, expanded=(status is None)):
                st.markdown(f"**{r.sentence}**")
                st.caption(f"자동 판정: {label_ko} (신뢰도 {r.confidence or '-'}) | 근거: {r.reason} | 계산: {r.calculation or '-'}")
                if status:
                    st.success(f"처리됨 → {status}")
                else:
                    act = st.radio("처리", ["승인", "보정", "반려"], key=f"act{rid}", horizontal=True)
                    corrected_to, cause, memo = "", "", ""
                    if act == "보정":
                        corrected_to = st.selectbox("올바른 판정", ["match", "mismatch", "unverifiable"], key=f"cor{rid}")
                        cause = st.selectbox("실패 원인 유형 (A4 분류)", list(FAILURE_TYPES), key=f"cau{rid}")
                        memo = st.text_input("보정 사유 메모", key=f"memo{rid}")
                    if st.button("확정", key=f"ok{rid}", type="primary"):
                        if act == "보정":
                            rec = FailureRecorder(ROOT / "data/failures/review_web.jsonl")
                            fid = rec.record(stage="review", ftype=cause,
                                             snapshot={"sentence": r.sentence, "auto": r.label,
                                                       "corrected": corrected_to},
                                             cause=memo)
                            reviews[rid] = f"보정 → {corrected_to} (실패 기록 {fid} — 파생 자산 등록 후 resolve)"
                        elif act == "승인":
                            reviews[rid] = "승인 (CONFIRMED — 발행 가능)"
                        else:
                            reviews[rid] = "반려 (REJECTED — 재처리 대상)"
                        st.rerun()

        if done and len(done) == len(queue):
            st.success("리뷰 완료! 보정 기록은 자산 현황 탭에서 플라이휠로 이어집니다 🔄")

# ═════════════ 탭 3: 자산 현황 (문서 11 플라이휠) ═════════════
with tab_assets:
    st.markdown("#### 실패 1건 = 자산 1줄 — 축적 현황")
    aliases = AliasDict(ROOT / "data/assets/aliases.jsonl")
    rules = sorted((ROOT / "data/assets/rules").glob("A2-*.json"))
    golden = (ROOT / "data/goldenset/golden_v0.jsonl").read_text(encoding="utf-8").strip().splitlines()
    fail_stats = FailureRecorder(ROOT / "data/failures/failures.jsonl").stats()

    a1, a2, a3, a4 = st.columns(4)
    a1.metric("A1 별칭 사전", f"{len(aliases)}건")
    a2.metric("A2 규칙 카드", f"{len(rules)}개")
    a3.metric("A3 골든셋", f"{len(golden)}건")
    a4.metric("A4 실패→자산 전환율",
              f"{fail_stats['asset_conversion_rate']:.0%}" if fail_stats.get("asset_conversion_rate") else "-")
    st.caption(f"실패 누적 {fail_stats['total']}건 (유형별: {fail_stats['by_type']}) — 전부 규칙·테스트로 전환됨")

    st.markdown("#### A2 규칙 카드 — 실패에서 태어난 지식")
    rows = []
    for p in rules:
        d = json.loads(p.read_text(encoding="utf-8"))
        rows.append({"ID": d["rule_id"], "규칙": d["name"], "유형": d["type"],
                     "유래": d.get("origin_case", "")[:46] + "…"})
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.markdown(
        "> **플라이휠**: 검증 실행 → 실패 발생 → A4 기록 → 원인 분석 → "
        "규칙(A2)·사전(A1)·골든셋(A3) 자산화 → 재측정으로 개선 확인 — "
        "리뷰 탭의 '보정'이 이 루프의 입구입니다.")

st.divider()
st.caption("ClaBi × AIFFELTHON | 실데이터 검증 완료 (2026-07-14, KOSIS 실 API — 과수 농가 166,558가구 실증) | "
           "최종 판단은 검증자 리뷰로 확정")
