"""ClaFact MVP — Streamlit 데모 (Community Cloud 배포용).

4탭 구성:
  🔎 검증      — 기사 입력 → 자동 판정 (WF-1)
  👤 검증자 리뷰 — 승인/보정/반려, 보정은 실패 레코드로 (WF-2)
  🔥 플라이휠   — 실패 → 골든셋 → 재평가 → 규칙 → 재평가를 라이브로 (문서 20 4막)
  🔄 자산 현황  — 자산 축적 대시보드 (문서 11)
"""
import os
import json
import tempfile
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backend.app.ingest_service import import_article_file
from clafact.assets.alias_dict import AliasDict
from clafact.assets.failures import FailureRecorder, FAILURE_TYPES
from clafact.assets.rules import RuleRegistry
from clafact.assets import goldenset
from clafact.eval import harness
from clafact.kosis import FixtureKosisClient
from clafact.ops_dashboard import build_ops_claim_rows
from clafact.pipeline.ingest import load_articles
from clafact.service.batch import process_pending
from clafact.service.store import Store, stable_article_id
from clafact.pipeline import detect
from clafact.pipeline.retrieve import StatIndex
from clafact.pipeline.run import verify_article, verify_sentence

ROOT = Path(__file__).resolve().parent
GOLDEN = ROOT / "data/goldenset/golden_v0.jsonl"
RULES_DIR = ROOT / "data/assets/rules"
FAILURES = ROOT / "data/failures/failures.jsonl"

SAMPLES = {
    "과수 농가 고령화 (파생 계산·일치)": {
        # 5월 기사 — 2024 데이터가 이미 확정(최종수정 4월)된 뒤라 정상 판정 (1막)
        "date": "2025-05-14",
        "text": "농가 고령화가 이어지면서 올해 과일 재배면적이 1% 줄었다. 2024년 국내 과수 농가의 65세 이상 비율은 64.2%로 나타났다.",
    },
    "잠정치 함정 (판단불가·A2-0012)": {
        # 같은 주장, 3월 기사 — 통계 최종수정일(2025-04-09)보다 앞서므로 당시 잠정치를
        # 알 수 없다 → 정직하게 판단불가. 위 샘플과 '날짜만' 다르다 (시연 3막).
        "date": "2025-03-14",
        "text": "2024년 국내 과수 농가의 65세 이상 비율은 64.2%로 나타났다.",
    },
    "기준연도 함정 (판단불가·A2-0013)": {
        # 지수 '수준'은 기준연도(2020=100)에 따라 값이 달라진다 — 기사가 어느 기준
        # 계열을 인용했는지 확인 불가 → 판단불가. (상승률 주장이면 회피 안 함)
        "date": "2025-06-01",
        "text": "지난해 소비자물가지수는 114.2를 기록했다.",
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

STATUS_KO = {"PENDING": "검증 대기", "DONE": "검증 완료", "FAILED": "검증 실패", "CLASSIFIED": "분류 완료"}

STYLE = {
    "match": ("🟢 일치", "#2E8B57"),
    "mismatch": ("🔴 불일치", "#C0392B"),
    "unverifiable": ("⚪ 판단불가", "#8A8F98"),
}
LABEL_ORDER = {"mismatch": 0, "unverifiable": 1, "match": 2}

def _stored_json(value: str) -> dict:
    try:
        return json.loads(value or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}


def render_stored_claim(row, number: int) -> None:
    """배치가 저장한 Claim 결과를 재실행 없이 검증 화면에 표시한다."""
    status = row["status"]
    if status == "PENDING":
        label, color = "🟡 처리 대기", "#C58C00"
    elif status == "FAILED":
        label, color = "🔴 처리 실패", "#C0392B"
    else:
        label, color = STYLE.get(row["label"], ("⚪ 판단불가", "#8A8F98"))

    with st.expander(f"[{number}] {label}  ·  {row['sentence'][:64]}", expanded=False):
        st.markdown(f"**주장:** {row['sentence']}")
        st.caption(
            f"기사일: {row['article_date'] or '-'} | 시점: {row['period'] or '-'} | "
            f"수치: {row['quantity'] or '-'} | 처리 상태: {STATUS_KO.get(status, status)}"
        )
        if status == "PENDING":
            st.info("아직 판정 전입니다. 아래 버튼으로 이 수치 주장만 KOSIS 검증합니다.")
            if st.button("KOSIS 검증 실행", key=f"verify_{row['claim_id']}", type="primary"):
                verify_store = Store(ROOT / "data/service/clafact.db")
                try:
                    index, client = load_engine()
                    process_pending(verify_store, index, client, claim_ids=[row["claim_id"]])
                except Exception as error:
                    st.error(f"검증 실패: {error}")
                finally:
                    verify_store.close()
                st.rerun()
            return
        if status == "FAILED":
            st.error(row["error"] or "처리 중 오류가 발생했습니다.")
            return

        evidence = _stored_json(row["evidence_json"])
        if evidence:
            st.markdown(
                f"**KOSIS 근거:** {evidence.get('tbl', '통계표 정보 없음')} "
                f"→ `{evidence.get('value', '값 없음')}`"
            )
        else:
            st.caption("KOSIS 근거: 대응 통계표를 찾지 못했습니다.")
        if row["calculation"]:
            st.markdown(f"**계산:** `{row['calculation']}`")
        if row["reason"]:
            st.caption(f"판정 근거: {row['reason']}")
        st.markdown("**HCX 설명**")
        st.write(row["explanation"] or "저장된 설명이 없습니다.")

        audit = _stored_json(row["audit_json"])
        if audit:
            with st.expander("감사 로그 · KOSIS 조회 조건"):
                st.json(audit, expanded=False)
CONF_ORDER = {"low": 0, "medium": 1, "high": 2, None: 3}


@st.cache_resource
def load_engine():
    return (StatIndex(ROOT / "data/samples/kosis/tables_meta.json"),
            FixtureKosisClient(ROOT / "data/samples/kosis"))


def render_card(r, scope="v"):
    label_ko, color = STYLE[r.label]
    chips = []
    if r.confidence:
        warn = " · 리뷰 최우선" if r.confidence == "low" else ""
        chips.append(f"신뢰도 {r.confidence}{warn}")
    if r.period:
        chips.append(f"시점 {r.period}")
    if r.quantity:
        chips.append(f"주장 수치 {r.quantity}")

    # ⚠ HTML 은 들여쓰기·줄바꿈 없이 한 줄로 조립한다.
    #   여러 줄 f-string 으로 쓰면, 근거가 없는 카드(=판단불가)에서 조건부 줄이 빈 줄이 되고
    #   다음 줄의 들여쓰기를 마크다운이 '코드 블록'으로 해석해 HTML 이 날것으로 노출된다.
    #   하필 판단불가는 시연 3막의 주인공이다 (문서 20 §2.3).
    evidence_html = (
        f'<div style="font-size:13px;color:var(--ops-muted)">근거: {r.evidence.get("tbl", "")} '
        f'→ <b>{r.evidence.get("value", "")}</b></div>'
    ) if r.evidence else ""
    html = (
        f'<div style="border:1px solid var(--ops-border);border-left:6px solid {color};color:var(--ops-text);'
        f'border-radius:10px;padding:14px 16px;margin:10px 0;background:var(--ops-surface)">'
        f'<b style="color:{color}">{label_ko}</b>'
        f'&nbsp;<span style="font-size:12px;color:var(--ops-muted)">{" · ".join(chips)}</span>'
        f'<div style="font-weight:bold;margin:6px 0">{r.sentence}</div>'
        f'{evidence_html}'
        f'<div style="font-size:13px;color:var(--ops-text);background:var(--ops-page);border-radius:8px;'
        f'padding:10px;margin-top:8px;line-height:1.6">{r.explanation}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
    if getattr(r, "notes", None):
        st.caption("⚠ " + " / ".join(r.notes))
    # getattr 방어 — 결과 객체에 audit이 없어도(구버전 배포·부분결과) 카드가 죽지 않게
    if getattr(r, "audit", None):
        render_audit(r, scope)


def render_audit(r, scope="v"):
    """재현 패널 (문서 20 기능 3) — 기업이 진짜 묻는 것은 정확도가 아니라 감사 가능성.

    scope: 같은 문장이 검증 탭과 리뷰 탭에 동시에 그려지므로 위젯 키를 탭별로 분리한다.
    """
    a = r.audit
    with st.expander(f"🔍 이 판정 재현하기 — 코드 {a['code_version']} · {a['engine']}"):
        st.caption(a["note"])
        c1, c2 = st.columns(2)
        c1.markdown(f"**통계표** `{a['org_id']}` / `{a['tbl_id']}`  \n{a['tbl_name']}")
        c2.markdown(f"**매핑 점수** {a['match_score']}  \n"
                    f"**적용 규칙** {', '.join(a['rules']) if a['rules'] else '(기본 로직)'}")

        st.markdown("**조회 파라미터**")
        st.json(a["params"], expanded=False)

        st.markdown("**실 API 호출 URL** — 인증키만 넣으면 누구나 같은 수치를 받습니다")
        st.code(a["url"], language="text")
        st.caption("🔒 인증키는 자리표시자로 마스킹됩니다 (공개 데모에 실 키를 노출하지 않음)")

        st.markdown("**판정에 사용된 행**")
        st.dataframe(a["rows"], use_container_width=True, hide_index=True)

        if r.calculation:
            st.markdown(f"**계산** `{r.calculation}`")

        if st.button("🔁 지금 재실행해서 같은 값이 나오는지 확인",
                     key=f"re_{scope}_{abs(hash(r.sentence))}"):
            idx, client = load_engine()
            again = verify_sentence(r.sentence, st.session_state.get("date", ""), idx, client)
            same = (again.label == r.label and again.calculation == r.calculation
                    and again.evidence == r.evidence)
            if same:
                st.success(f"✅ 동일 — 판정 `{again.label}`, 계산 `{again.calculation or '-'}` "
                           "(판정은 결정적 로직이라 같은 입력이면 항상 같습니다)")
            else:
                st.error(f"⚠️ 다름! 이전 `{r.label}` → 지금 `{again.label}` — "
                         "코드나 자산이 바뀌었습니다. 이 경우 실패 레코드 대상입니다.")


st.set_page_config(page_title="ClaFact — 뉴스 수치 검증 MVP", page_icon="◈", layout="wide")
st.markdown("""
<style>
  :root {
    color-scheme:light dark;
    --ops-page:var(--background-color,#F3F6F8);
    --ops-surface:var(--secondary-background-color,#FFFFFF);
    --ops-text:var(--text-color,#102A3A);
    --ops-muted:color-mix(in srgb,var(--text-color,#102A3A) 66%,var(--background-color,#F3F6F8));
    --ops-border:color-mix(in srgb,var(--text-color,#102A3A) 24%,var(--background-color,#F3F6F8));
  }
  [data-testid="stSidebar"] { --ops-page:var(--background-color); --ops-surface:var(--secondary-background-color); --ops-text:var(--text-color); --ops-muted:color-mix(in srgb,var(--text-color) 66%,var(--background-color)); --ops-border:color-mix(in srgb,var(--text-color) 24%,var(--background-color)); background:var(--ops-surface); border-right:1px solid var(--ops-border); }
  [data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding-top:1.2rem; }
  .sidebar-brand { color:var(--ops-text); font-size:1.25rem; font-weight:780; letter-spacing:-.04em; margin:.25rem 0 .2rem; }
  .sidebar-caption { color:var(--ops-muted); font-size:.78rem; line-height:1.5; margin-bottom:1.4rem; }
  [data-testid="stSidebar"] [data-testid="stRadio"] label { border-radius:.55rem; color:var(--ops-text); padding:.48rem .55rem; margin:.12rem 0; }
  [data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background:var(--ops-page); }
  [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) { background:var(--ops-page); border-left:3px solid var(--primary-color); font-weight:720; }`n  .stApp { --ops-page:var(--background-color); --ops-surface:var(--secondary-background-color); --ops-text:var(--text-color); --ops-muted:color-mix(in srgb,var(--text-color) 66%,var(--background-color)); --ops-border:color-mix(in srgb,var(--text-color) 24%,var(--background-color)); background:var(--ops-page); color:var(--ops-text); }
  [data-testid="stHeader"] { --ops-page:var(--background-color); background:var(--ops-page); }
  .block-container { max-width:1440px; padding-top:2rem; padding-bottom:4rem; }
  h1,h2,h3 { color:var(--ops-text) !important; }
  [data-testid="stTabs"] [data-baseweb="tab-list"] { gap:.35rem; border-bottom:1px solid var(--ops-border); }
  [data-testid="stTabs"] button { color:var(--ops-text); font-weight:650; }
  [data-testid="stTabs"] button[aria-selected="true"] { color:var(--ops-text); background:var(--ops-surface); }
  [data-testid="stTextInput"] input,[data-testid="stNumberInput"] input,[data-testid="stTextArea"] textarea { background:var(--ops-surface); color:var(--ops-text); border-color:var(--ops-border); }
  [data-testid="stDataFrame"] { border:1px solid var(--ops-border); border-radius:.75rem; overflow:hidden; }
  .ops-hero { background:radial-gradient(circle at 90% 0%,rgba(70,213,199,.12),transparent 31%),var(--ops-surface); border:1px solid var(--ops-border); border-radius:1rem; padding:clamp(1.25rem,3vw,2.25rem); margin-bottom:1.25rem; }
  .ops-kicker { color:var(--primary-color); font-size:.75rem; font-weight:750; letter-spacing:.12em; text-transform:uppercase; }
  .ops-title { color:var(--ops-text); font-size:clamp(1.7rem,3.5vw,2.65rem); font-weight:760; line-height:1.1; margin:.5rem 0; }
  .ops-copy,.ops-note { color:var(--ops-muted); line-height:1.65; }
  .ops-chip { display:inline-block; margin-top:.8rem; padding:.35rem .65rem; border:1px solid var(--primary-color); border-radius:99px; color:var(--primary-color); font-size:.82rem; }
  .ops-card { min-height:8rem; background:var(--ops-surface); border:1px solid var(--ops-border); border-top:3px solid var(--accent); border-radius:.8rem; padding:1rem 1.1rem; }
  .ops-label { color:var(--ops-muted); font-size:.83rem; font-weight:650; }
  .ops-value { color:var(--ops-text); font-size:2.25rem; font-weight:760; letter-spacing:-.04em; margin-top:.4rem; }
  .ops-note { color:var(--ops-muted); font-size:.78rem; margin-top:.4rem; }
  div.stButton > button { background:var(--ops-surface); color:var(--ops-text); border-color:var(--ops-border); }
  div.stButton > button[kind="primary"] { background:#087f73 !important; color:#FFFFFF !important; border-color:#087f73 !important; }`n  div.stButton > button[kind="primary"] p { color:#FFFFFF !important; }
  div.stButton > button p { color:inherit !important; }
  :focus-visible { outline:3px solid #f1c96b !important; outline-offset:2px; }
  .ops-workspace { background:var(--ops-surface); border:1px solid var(--ops-border); border-radius:1rem; padding:1.15rem 1.25rem 1.3rem; margin:0 0 1.4rem; box-shadow:0 8px 24px rgba(16,42,58,.05); }
  .ops-section-head { margin:.2rem 0 1rem; }
  .ops-section-kicker { color:var(--primary-color); font-size:.72rem; font-weight:760; letter-spacing:.12em; text-transform:uppercase; margin-bottom:.25rem; }
  .ops-section-title { color:var(--ops-text); font-size:1.35rem; font-weight:760; letter-spacing:-.025em; margin:0; }
  .ops-section-copy { color:var(--ops-muted); font-size:.88rem; line-height:1.55; margin:.3rem 0 0; }
  .ops-summary-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.75rem; margin:.6rem 0 1.35rem; }
  .ops-summary-card { background:var(--ops-surface); border:1px solid var(--ops-border); border-radius:.8rem; padding:.9rem 1rem; min-height:6.2rem; }
  .ops-summary-label { color:var(--ops-muted); font-size:.78rem; font-weight:670; }
  .ops-summary-value { color:var(--ops-text); font-size:1.9rem; font-weight:780; letter-spacing:-.045em; margin-top:.35rem; }
  .ops-summary-note { color:var(--ops-muted); font-size:.74rem; margin-top:.25rem; }
  .ops-route-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.75rem; margin:.85rem 0 .8rem; }
  .ops-route-card { border:1px solid var(--ops-border); border-left:4px solid var(--route-accent); border-radius:.75rem; background:var(--ops-page); padding:.9rem 1rem; min-height:7.2rem; }
  .ops-route-label { color:var(--ops-text); font-size:.9rem; font-weight:740; }
  .ops-route-value { color:var(--ops-text); font-size:1.7rem; font-weight:780; margin-top:.4rem; }
  .ops-route-note { color:var(--ops-muted); font-size:.75rem; line-height:1.45; margin-top:.25rem; }
  .ops-next-action { display:flex; gap:.65rem; align-items:baseline; background:color-mix(in srgb,var(--primary-color) 10%,var(--ops-surface)); border:1px solid color-mix(in srgb,var(--primary-color) 35%,var(--ops-border)); border-radius:.75rem; color:var(--ops-text); padding:.85rem 1rem; margin-top:1rem; }
  .ops-next-label { color:var(--primary-color); font-size:.78rem; font-weight:760; white-space:nowrap; }
  @media (max-width:900px) { .ops-summary-grid { grid-template-columns:repeat(2,minmax(0,1fr)); } .ops-route-grid { grid-template-columns:1fr; } }
  @media (max-width:640px) { .ops-summary-grid { grid-template-columns:1fr 1fr; } .ops-workspace { padding:.9rem; } .ops-next-action { display:block; } }
  @media (max-width:640px) { .block-container { padding-inline:1rem; } .ops-card { min-height:6.5rem; } }
</style>
""", unsafe_allow_html=True)
st.markdown("""<section class="ops-hero"><div class="ops-kicker">ClaFact · Evidence Operations</div><h1 class="ops-title">국가통계 기반 뉴스 검증 운영</h1><p class="ops-copy">기사 등록부터 판정 감사까지, 근거가 남는 검증 흐름을 한 화면에서 관리합니다.</p><span class="ops-chip">● KOSIS 연결 기준 · 감사 로그 보존</span></section>""", unsafe_allow_html=True)

NAV_ITEMS = ("운영 홈", "검증", "검증자 리뷰", "플라이휠", "자산 현황")
st.sidebar.markdown('<div class="ops-kicker">ClaFact</div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="sidebar-brand">검증 운영 콘솔</div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="sidebar-caption">근거 기반 뉴스 수치 검증과 리뷰 흐름을 관리합니다.</div>', unsafe_allow_html=True)
view = st.sidebar.radio("주요 화면", NAV_ITEMS, label_visibility="collapsed")

if view == "운영 홈":
    store = Store(ROOT / "data/service/clafact.db")
    try:
        summary = store.summary()
    finally:
        store.close()
    st.markdown(f"""<div class="ops-summary-grid">
      <div class="ops-summary-card"><div class="ops-summary-label">누적 등록 기사</div><div class="ops-summary-value">{summary["articles"]:,}</div><div class="ops-summary-note">누적 수집</div></div>
      <div class="ops-summary-card"><div class="ops-summary-label">처리 대기</div><div class="ops-summary-value">{summary["claims_by_status"].get("PENDING", 0):,}</div><div class="ops-summary-note">다음 배치 대상</div></div>
      <div class="ops-summary-card"><div class="ops-summary-label">처리 실패</div><div class="ops-summary-value">{summary["claims_by_status"].get("FAILED", 0):,}</div><div class="ops-summary-note">조치 필요</div></div>
      <div class="ops-summary-card"><div class="ops-summary-label">리뷰 대기</div><div class="ops-summary-value">{summary["review_queue"]:,}</div><div class="ops-summary-note">검토자 확인</div></div>
    </div>""", unsafe_allow_html=True)

    st.markdown("""<div class="ops-workspace">
      <div class="ops-section-head"><div class="ops-section-kicker">WORKFLOW 01</div><h2 class="ops-section-title">운영 실행</h2><p class="ops-section-copy">CSV 기사를 등록하면 수치 주장을 분류하고, KOSIS 분석 대상만 검증 탭으로 전달합니다.</p></div>""", unsafe_allow_html=True)
    api_url = os.environ.get("CLAFACT_API_URL", "http://127.0.0.1:8000").rstrip("/")
    uploaded_csv = st.file_uploader("CSV 기사 파일", type=["csv"], help="UTF-8 또는 UTF-8 BOM CSV 파일을 선택하세요.")

    if st.button("기사 등록", use_container_width=True, type="primary"):
        if uploaded_csv is None:
            st.warning("등록할 CSV 기사 파일을 먼저 선택하세요.")
        else:
            temporary_path = None
            progress_status = st.status("기사 등록 진행 중", expanded=True)
            progress_status.write("파일 읽기: 진행 중")
            store = Store(ROOT / "data/service/clafact.db")
            try:
                with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as temporary_file:
                    temporary_file.write(uploaded_csv.getvalue())
                    temporary_path = Path(temporary_file.name)
                articles = load_articles(temporary_path)
                progress_status.write(f"파일 읽기: 완료 · 기사 {len(articles)}건")
                progress_status.write("기사 등록: 진행 중")
                out = import_article_file(temporary_path, store)
                progress_status.write(f"기사 등록: 완료 · 유효 기사 {out['read']}건 · 문장 {out['sentences']}건")
                progress_status.write(f"출처 분류: 완료 · 후보 {out['candidates']}건")
                progress_status.write(f"검증 후보 준비: 완료 · KOSIS {out.get('routes', {}).get('KOSIS_RETRIEVAL', 0)}건")
                progress_status.update(label="기사 등록 완료", state="complete", expanded=False)
                st.session_state["uploaded_article_ids"] = [
                    stable_article_id(article.url, article.title, article.date)
                    for article in articles
                ]
                st.session_state["upload_summary"] = out
                st.success(f"등록 완료 · 원본 {out['source_rows']}행 → 유효 기사 {out['read']}건 → 문장 {out['sentences']}건 → 수치 주장 후보 {out['candidates']}건 → 큐 등록 {out['queued']}건")
                if out['excluded_candidates']:
                    st.caption('제외: ' + ', '.join(f'{reason} {count}건' for reason, count in out['exclusion_reasons'].items()))
            except (OSError, UnicodeDecodeError, ValueError) as error:
                progress_status.update(label="기사 등록 실패", state="error", expanded=True)
                progress_status.write(f"오류: {error}")
                st.error(f"등록 실패: {error}")
            finally:
                store.close()
                if temporary_path is not None:
                    temporary_path.unlink(missing_ok=True)
    uploaded_article_ids = st.session_state.get("uploaded_article_ids", [])
    if uploaded_article_ids:
        pending_store = Store(ROOT / "data/service/clafact.db")
        try:
            pending_count = pending_store.count_pending(uploaded_article_ids)
            classified_count = pending_store.count_upload_results(uploaded_article_ids) - pending_count
        finally:
            pending_store.close()
        st.success(f"KOSIS 검증 후보 {pending_count}건 · 분류 보존 {classified_count}건")
        st.caption("검증 탭에서 수치 주장별로 실행하세요.")
    else:
        st.info("CSV 기사 파일을 등록하면 KOSIS 후보와 분류 결과가 표시됩니다.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("""<div class="ops-section-head"><div class="ops-section-kicker">WORKFLOW 02</div><h2 class="ops-section-title">이번 업로드 전처리 요약</h2><p class="ops-section-copy">원본 → 유효 기사 → 문장 → 수치 주장 → 출처 분류 → 검증 처리</p></div>""", unsafe_allow_html=True)
    upload = st.session_state.get("upload_summary", {})
    if upload:
        st.markdown(f"""<div class="ops-summary-grid">
          <div class="ops-summary-card"><div class="ops-summary-label">원본 행</div><div class="ops-summary-value">{upload.get("source_rows", 0):,}</div><div class="ops-summary-note">업로드 원본</div></div>
          <div class="ops-summary-card"><div class="ops-summary-label">유효 기사</div><div class="ops-summary-value">{upload.get("read", 0):,}</div><div class="ops-summary-note">등록 완료</div></div>
          <div class="ops-summary-card"><div class="ops-summary-label">문장</div><div class="ops-summary-value">{upload.get("sentences", 0):,}</div><div class="ops-summary-note">문장 분리</div></div>
          <div class="ops-summary-card"><div class="ops-summary-label">수치 주장</div><div class="ops-summary-value">{upload.get("candidates", 0):,}</div><div class="ops-summary-note">분류 대상</div></div>
        </div>""", unsafe_allow_html=True)
        kosis_count = upload.get("routes", {}).get("KOSIS_RETRIEVAL", 0)
        source_types = upload.get("source_types", {})
        direct_kosis_count = source_types.get("KOSIS_DOMESTIC", 0)
        complex_kosis_count = source_types.get("KOSIS_BUT_COMPLEX", 0)
        other_count = upload.get("candidates", 0) - kosis_count
        st.markdown(f"""<div class="ops-route-grid">
          <div class="ops-route-card" style="--route-accent:#087f73"><div class="ops-route-label">자동 검증 가능</div><div class="ops-route-value">{direct_kosis_count:,}건</div><div class="ops-route-note">직접 조회형 KOSIS · 자동 판정</div></div>
          <div class="ops-route-card" style="--route-accent:#d99718"><div class="ops-route-label">복합 KOSIS 사람 검토</div><div class="ops-route-value">{complex_kosis_count:,}건</div><div class="ops-route-note">KOSIS 분석 후 최종 확정은 검토자</div></div>
          <div class="ops-route-card" style="--route-accent:#718096"><div class="ops-route-label">별도 근거 확인 대상</div><div class="ops-route-value">{other_count:,}건</div><div class="ops-route-note">공식 공지·비KOSIS·민간 자료</div></div>
        </div>""", unsafe_allow_html=True)
        st.caption(f"KOSIS 분석 대상은 직접 조회형과 복합형을 모두 포함합니다 · 총 {kosis_count:,}건 = 직접 조회형 {direct_kosis_count:,}건 + 복합형 {complex_kosis_count:,}건")
        st.caption("복합 KOSIS는 KOSIS 분석 후 최종 판정만 사람이 검토합니다. KOSIS 조회·분석 결과는 함께 보존합니다.")
        st.caption(f"별도 근거 세부: 공식 공지 {source_types.get('OFFICIAL_ANNOUNCEMENT', 0):,} · 비KOSIS 공식자료 {source_types.get('OTHER_OFFICIAL', 0):,} · 민간·플랫폼 {source_types.get('PRIVATE_SOURCE', 0) + source_types.get('PLATFORM_SOURCE', 0):,} · 사람 검토 {source_types.get('UNKNOWN', 0):,}")
        st.markdown("""<div class="ops-next-action"><span class="ops-next-label">다음 행동</span><span>검증 탭에서 현재 페이지 50건을 일괄 검증하거나, 위험 Claim은 검증자 리뷰에서 확인하세요.</span></div>""", unsafe_allow_html=True)
    else:
        st.info("CSV를 등록하면 전처리·분류 요약이 표시됩니다.")# ═════════════ 탭 1: 검증 (WF-1) ═════════════
if view == "검증":
    st.markdown("#### 이번 업로드 검증 결과")
    st.caption("운영 홈에서 등록·처리한 Claim의 저장된 KOSIS 판정과 HCX 설명을 다시 실행하지 않고 확인합니다.")
    uploaded_article_ids = st.session_state.get("uploaded_article_ids", [])
    if uploaded_article_ids:
        result_store = Store(ROOT / "data/service/clafact.db")
        try:
            upload_results = result_store.fetch_upload_results(uploaded_article_ids, route="KOSIS_RETRIEVAL")
            non_kosis_results = result_store.fetch_upload_results(uploaded_article_ids, route="NON_KOSIS_QUEUE")
            unverifiable_rows = result_store.fetch_upload_results(uploaded_article_ids, label="unverifiable")
            official_announcements = [
                row for row in non_kosis_results
                if row["source_type"] == "OFFICIAL_ANNOUNCEMENT"
            ]
        finally:
            result_store.close()

        if unverifiable_rows:
            reason_counts = {}
            for row in unverifiable_rows:
                reason = row["reason"] or row["classification_reason"] or "근거 부족"
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            st.markdown("#### 판단불가 사유")
            st.caption("현재 업로드에서 자동 검증으로 결론을 내리지 못한 Claim의 사유입니다.")
            st.dataframe(
                [{"사유": reason, "건수": count} for reason, count in sorted(reason_counts.items())],
                hide_index=True,
                use_container_width=True,
            )

        if official_announcements:
            st.markdown("#### 공식 공지 검증")
            st.caption("KOSIS 표 해당 없음 · 공식 공지 검증")
            for row in official_announcements:
                evidence = _stored_json(row["evidence_json"])
                registered_notice = evidence.get("official_notice") or evidence.get("official_url")
                with st.expander(f"공식 조사·시행 일정 · {row['sentence'][:64]}", expanded=False):
                    st.markdown(f"**주장:** {row['sentence']}")
                    if registered_notice:
                        st.success("공식 공지 근거 등록 · 일치")
                        st.caption(f"공식 근거: {registered_notice}")
                    else:
                        st.warning("공식 근거 확인 필요")
                        organization = st.text_input("공식 기관명", key=f"notice_org_{row['claim_id']}")
                        notice_url = st.text_input("공식 공지 URL", key=f"notice_url_{row['claim_id']}")
                        effective_date = st.date_input("시행일", key=f"notice_date_{row['claim_id']}")
                        if st.button("공식 공지 검증", key=f"notice_verify_{row['claim_id']}"):
                            import requests
                            api_url = os.environ.get("CLAFACT_API_URL", "http://127.0.0.1:8000").rstrip("/")
                            response = requests.post(f"{api_url}/internal/claims/{row['claim_id']}/official-notice", json={"organization": organization, "url": notice_url, "effective_date": str(effective_date)}, timeout=10)
                            if response.ok:
                                st.success("공식 공지 근거가 등록되었습니다.")
                                st.rerun()
                            else:
                                st.error(response.json().get("detail", "공식 공지 등록에 실패했습니다."))

        if upload_results:
            pending = sum(row["status"] == "PENDING" for row in upload_results)
            completed = sum(row["status"] == "DONE" for row in upload_results)
            failed = sum(row["status"] == "FAILED" for row in upload_results)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("이번 업로드 수치 주장", len(upload_results))
            m2.metric("판정 완료", completed)
            m3.metric("처리 대기", pending)
            m4.metric("처리 실패", failed)

            view_mode = st.radio("결과 보기", ("선택 기사", "전체 수치 주장"), horizontal=True)
            if view_mode == "전체 수치 주장":
                filter_status, filter_label, filter_search = st.columns([1, 1, 2])
                status_option = filter_status.selectbox("처리 상태", ("전체", "검증 대기", "검증 완료", "검증 실패"))
                label_option = filter_label.selectbox("판정", ("전체", "일치", "불일치", "판단불가"))
                search = filter_search.text_input("수치 주장 검색", placeholder="주장 문장에 포함된 단어")
                label_map = {"일치": "match", "불일치": "mismatch", "판단불가": "unverifiable"}
                status = {"검증 대기": "PENDING", "검증 완료": "DONE", "검증 실패": "FAILED"}.get(status_option)
                label = label_map.get(label_option)
                page_size = 50
                filtered_store = Store(ROOT / "data/service/clafact.db")
                try:
                    total = filtered_store.count_upload_results(
                        uploaded_article_ids, status=status, label=label, route="KOSIS_RETRIEVAL", search=search)
                    page_count = max(1, (total + page_size - 1) // page_size)
                    page = st.number_input("페이지", min_value=1, max_value=page_count, value=1, step=1)
                    page_rows = filtered_store.fetch_upload_results(
                        uploaded_article_ids, status=status, label=label, route="KOSIS_RETRIEVAL", search=search,
                        limit=page_size, offset=(int(page) - 1) * page_size)
                finally:
                    filtered_store.close()
                start = 0 if total == 0 else (int(page) - 1) * page_size + 1
                end = min(int(page) * page_size, total)
                st.caption(f"검색 결과 {total:,}건 · {start:,}–{end:,}번 표시 · 50건씩 페이지 이동")
                pending_ids = [row["claim_id"] for row in page_rows if row["status"] == "PENDING"]
                if pending_ids and st.button("현재 페이지 50건 검증", type="primary"):
                    batch_store = Store(ROOT / "data/service/clafact.db")
                    try:
                        index, client = load_engine()
                        stats = process_pending(batch_store, index, client, claim_ids=pending_ids[:50])
                        st.success(f"일괄 검증 완료 · 처리 {stats['processed']}건 · 실패 {stats['failed']}건")
                    finally:
                        batch_store.close()
                    st.rerun()
                for number, row in enumerate(page_rows, start=start):
                    render_stored_claim(row, number)
            else:
                article_rows = {}
                for row in upload_results:
                    article_rows.setdefault(row["article_id"], row)
                article_ids = list(article_rows)
                selected_article_id = st.selectbox(
                    "검증할 기사",
                    article_ids,
                    format_func=lambda article_id: (
                        f"{article_rows[article_id]['article_date']} · "
                        f"{article_rows[article_id]['title'] or article_id}"
                    ),
                )
                selected = [row for row in upload_results if row["article_id"] == selected_article_id]
                st.caption(f"선택 기사 수치 주장 {len(selected)}건 · 아래 Claim을 하나씩 펼쳐 KOSIS 근거와 HCX 설명을 확인하세요.")
                for number, row in enumerate(selected, start=1):
                    render_stored_claim(row, number)
        else:
            st.info("이번 업로드에서 검증 후보 Claim이 추출되지 않았습니다.")
    else:
        st.info("운영 홈에서 CSV를 등록하면, 이곳에 해당 업로드의 Claim 판정 결과가 표시됩니다.")

    with st.expander("데모 샘플 직접 검증", expanded=False):
        st.caption("업로드 결과와 별도로, 예전 픽스처 샘플을 직접 실행해 볼 수 있습니다.")
        st.session_state.setdefault("text", "")
        st.session_state.setdefault("date", "2025-07-14")
        clicked_sample = False
        cols = st.columns(2)
        for i, (name, s) in enumerate(SAMPLES.items()):
            if cols[i % 2].button(name, use_container_width=True):
                st.session_state["text"] = s["text"]
                st.session_state["date"] = s["date"]
                clicked_sample = True

        text = st.text_area("기사 본문", key="text", height=160)
        date = st.date_input("기사 발행일", value=st.session_state["date"])

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
                r for r in verify_article(text, str(date), idx, client) if r.label != "not_claim"]
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
if view == "검증자 리뷰":
    persisted_store = Store(ROOT / "data/service/clafact.db")
    try:
        persisted_queue = persisted_store.review_queue()
    finally:
        persisted_store.close()
    if persisted_queue:
        st.markdown("#### 저장된 검증자 리뷰 큐")
        for row in persisted_queue:
            with st.expander(f"{row['label'] or '판정 확인'} · {row['sentence'][:64]}"):
                st.write(row["sentence"])
                st.caption(row["reason"] or "자동 판정 근거 확인 필요")
                review_org = st.text_input("공식 기관명", key=f"review_notice_org_{row['claim_id']}")
                review_url = st.text_input("공식 공지 URL", key=f"review_notice_url_{row['claim_id']}")
                review_date = st.date_input("시행일", key=f"review_notice_date_{row['claim_id']}")
                if st.button("공식 근거 교체 후 재검증", key=f"review_notice_verify_{row['claim_id']}"):
                    import requests
                    api_url = os.environ.get("CLAFACT_API_URL", "http://127.0.0.1:8000").rstrip("/")
                    response = requests.post(f"{api_url}/internal/claims/{row['claim_id']}/official-notice", json={"organization": review_org, "url": review_url, "effective_date": str(review_date)}, timeout=10)
                    if response.ok:
                        st.success("공식 근거로 재검증했습니다.")
                        st.rerun()
                    else:
                        st.error(response.json().get("detail", "재검증에 실패했습니다."))
                approve, hold = st.columns(2)
                if approve.button("자동 판정 승인", key=f"approve_{row['claim_id']}"):
                    review_store = Store(ROOT / "data/service/clafact.db")
                    try:
                        review_store.apply_review(row["claim_id"], "approve")
                    finally:
                        review_store.close()
                    st.rerun()
                if hold.button("판단 보류", key=f"hold_{row['claim_id']}"):
                    hold_store = Store(ROOT / "data/service/clafact.db")
                    try:
                        hold_store.apply_review(row["claim_id"], "hold", note="공식 근거 확인 필요")
                    finally:
                        hold_store.close()
                    st.rerun()
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
                if getattr(r, "audit", None):
                    render_audit(r, scope="rv")  # 검증자는 승인 전에 근거를 볼 수 있어야 한다
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
                            rec = FailureRecorder(FAILURES)
                            fid = rec.record(stage="review", ftype=cause,
                                             snapshot={"sentence": r.sentence, "auto": r.label,
                                                       "corrected": corrected_to},
                                             cause=memo)
                            reviews[rid] = f"보정 → {corrected_to} (실패 {fid} — 🔥 플라이휠 탭에서 자산화)"
                            # 플라이휠 탭으로 넘긴다 — 여기서 끊기면 루프가 데모에서 죽는다
                            st.session_state["fw"] = {
                                "fail_id": fid, "sentence": r.sentence,
                                "auto": r.label, "corrected": corrected_to,
                                "cause": cause, "memo": memo,
                            }
                        elif act == "승인":
                            reviews[rid] = "승인 (CONFIRMED — 발행 가능)"
                        else:
                            reviews[rid] = "반려 (REJECTED — 재처리 대상)"
                        st.rerun()

        if done and len(done) == len(queue):
            st.success("리뷰 완료! 보정 기록은 자산 현황 탭에서 플라이휠로 이어집니다 🔄")

# ═════════════ 탭 3: 플라이휠 라이브 (문서 20 4막) ═════════════
def run_eval():
    """하네스 실행 → 리포트. 규칙 캐시를 먼저 비워야 새 규칙이 반영된다."""
    detect.reload_rules()
    return harness.run(str(GOLDEN), out_dir=str(ROOT / "reports"), record_failures=False)


def show_metrics(rep, caption=""):
    d = rep["metrics"]["detection"]
    v = rep["metrics"]["verdict"].get("classification", {})
    c1, c2, c3 = st.columns(3)
    diff = rep.get("diff_vs_previous", {})

    def delta(key):
        x = diff.get(key)
        return f"{x['delta']:+.4f}" if x and x["delta"] else None

    c1.metric("탐지 F1", f"{d['f1']:.4f}", delta("detection_f1"))
    c2.metric("판정 정확도", f"{v.get('accuracy', 0):.4f}", delta("verdict_accuracy"))
    c3.metric("골든셋", f"{rep['golden']['n_rows']}행")
    if caption:
        st.caption(caption)


if view == "플라이휠":
    st.markdown("#### 🔥 실패 1건 = 자산 1줄 — 라이브")
    st.caption("검증 탭에서 시스템을 속인 문장을 여기서 자산으로 바꿉니다. "
               "**골든셋에 넣으면 점수가 일단 떨어집니다 — 그 하락이 골든셋이 진짜라는 증거입니다.**")

    fw = st.session_state.get("fw")
    with st.expander("① 대상 실패 — 리뷰에서 보정했거나, 직접 입력", expanded=not fw):
        default_s = fw["sentence"] if fw else ""
        s_in = st.text_input("시스템이 놓친/틀린 문장", value=default_s, key="fw_sent")
        col_a, col_b = st.columns(2)
        gold_in = col_a.selectbox("올바른 판정 (골든셋 정답)",
                                  ["match", "mismatch", "unverifiable", "(주장 아님)"], key="fw_gold")
        claim_in = col_b.checkbox("검증 가능 주장인가", value=True, key="fw_isclaim")
        if st.button("이 문장으로 진행", use_container_width=True) and s_in.strip():
            st.session_state["fw"] = {**(fw or {}), "sentence": s_in.strip(),
                                      "corrected": gold_in, "is_claim": claim_in,
                                      "fail_id": (fw or {}).get("fail_id")}
            st.rerun()

    fw = st.session_state.get("fw")
    if not fw or not fw.get("sentence"):
        st.info("위에서 문장을 입력하거나, **검증 → 리뷰 탭에서 보정**하면 여기로 넘어옵니다.")
    else:
        st.markdown(f"> **대상 문장:** {fw['sentence']}")
        detected = detect.is_candidate(fw["sentence"])
        st.caption(f"현재 탐지 결과: {'✅ 탐지됨' if detected else '❌ 놓침'}"
                   + (f" (규칙 {detect.which_rule(fw['sentence'])})" if detect.which_rule(fw['sentence']) else ""))

        # ── ② 골든셋 추가 (A3) ──
        st.markdown("##### ② 골든셋에 추가 (A3)")
        if fw.get("golden_added"):
            st.success(f"추가됨 → {fw['golden_added']}")
        elif st.button("골든셋에 추가", use_container_width=True):
            try:
                is_claim = fw.get("is_claim", True)
                row = goldenset.append_row(
                    GOLDEN, fw["sentence"], is_claim,
                    gold_label=None if not is_claim or fw.get("corrected") == "(주장 아님)"
                    else fw.get("corrected"),
                    notes=f"플라이휠 — 유래 실패 {fw.get('fail_id') or '(직접 입력)'}")
                st.session_state["fw"] = {**fw, "golden_added": row["article_id"]}
                st.rerun()
            except ValueError as e:
                st.error(f"거부됨: {e}")

        # ── ③ 재평가 (하락 확인) ──
        st.markdown("##### ③ 재평가 — 점수가 떨어지는가")
        if st.button("재평가 실행", key="fw_eval1", use_container_width=True):
            st.session_state["fw"] = {**st.session_state["fw"], "rep1": run_eval()}
            st.rerun()
        if fw.get("rep1"):
            show_metrics(fw["rep1"], "골든셋이 커졌고, 시스템이 못 푸는 행이 들어왔으므로 점수가 내려가는 것이 정상입니다.")

        # ── ④ 규칙 카드 생성 (A2) ──
        st.markdown("##### ④ 규칙 카드 생성 (A2) — 이 카드는 **실제로 실행됩니다**")
        reg = RuleRegistry(RULES_DIR)
        if fw.get("rule_id"):
            st.success(f"생성됨 → {fw['rule_id']} (실패 {fw.get('fail_id') or '-'} resolve 완료)")
        else:
            st.caption(f"다음 규칙 ID: **{reg.next_id()}** (기존 카드 수를 세어 자동 채번)")
            r_name = st.text_input("규칙 이름", key="fw_rname",
                                   placeholder="예: '반토막' 표현 탐지")
            r_pat = st.text_input("탐지 패턴 (정규식)", key="fw_rpat",
                                  placeholder="예: 반토막")
            r_cond = st.text_input("조건", key="fw_rcond",
                                   placeholder="예: 문장에 '반토막' 표현이 있는 경우")
            if st.button("규칙 생성 + 실패 resolve", type="primary", use_container_width=True):
                try:
                    card = reg.create(
                        type="detection", name=r_name, pattern=r_pat,
                        condition=r_cond or f"'{r_pat}' 패턴 포함",
                        handling="검증 가능 주장 후보로 탐지한다",
                        origin_case=fw["sentence"][:80],
                        origin_run=fw.get("fail_id", ""),
                        test="tests/test_rules.py::test_new_rule_card_changes_detection",
                    )
                    assets = [card["rule_id"]] + ([f"A3:{fw['golden_added']}"] if fw.get("golden_added") else [])
                    if fw.get("fail_id"):
                        try:
                            FailureRecorder(FAILURES).resolve(fw["fail_id"], assets)
                        except KeyError:
                            pass  # 다른 파일에 기록된 과거 실패 — 규칙 생성은 유효
                    detect.reload_rules()
                    st.session_state["fw"] = {**fw, "rule_id": card["rule_id"]}
                    st.rerun()
                except (ValueError, FileExistsError) as e:
                    st.error(f"거부됨: {e}")

        # ── ⑤ 재평가 (회복 확인) ──
        if fw.get("rule_id"):
            st.markdown("##### ⑤ 재평가 — 자산이 점수를 되돌리는가")
            if st.button("재평가 실행", key="fw_eval2", type="primary", use_container_width=True):
                st.session_state["fw"] = {**st.session_state["fw"], "rep2": run_eval()}
                st.rerun()
            if fw.get("rep2"):
                show_metrics(fw["rep2"], "방금 만든 규칙이 코드 수정 없이 적용되어 탐지가 회복됩니다.")
                st.success("🔄 루프 완주 — 실패가 골든셋(A3)과 규칙(A2)으로 남았고, 재측정으로 증명됐습니다.")
                st.caption("⚠ 정직 고지: 여기서 자동 적용되는 것은 **패턴형 탐지 규칙**입니다. "
                           "판정 로직(파생 계산 등) 규칙은 카드가 초안으로 남고, 실제 반영은 "
                           "개발자가 테스트와 함께 구현합니다 (문서 20 §3.1).")

        if st.button("🗑 플라이휠 초기화"):
            st.session_state.pop("fw", None)
            st.rerun()


# ═════════════ 탭 4: 자산 현황 (문서 11 플라이휠) ═════════════
if view == "자산 현황":
    st.markdown("#### 실패 1건 = 자산 1줄 — 축적 현황")
    aliases = AliasDict(ROOT / "data/assets/aliases.jsonl")
    reg = RuleRegistry(RULES_DIR)
    rstats = reg.stats()
    gstats = goldenset.stats(GOLDEN)
    fail_stats = FailureRecorder(FAILURES).stats()

    a1, a2, a3, a4 = st.columns(4)
    a1.metric("A1 별칭 사전", f"{len(aliases)}건")
    a2.metric("A2 규칙 카드", f"{rstats['total']}개", f"{rstats['executable']}개 실행형")
    a3.metric("A3 골든셋", f"{gstats['total']}건")
    a4.metric("A4 실패→자산 전환율",
              f"{fail_stats['asset_conversion_rate']:.0%}" if fail_stats.get("asset_conversion_rate") else "-")
    st.caption(f"실패 누적 {fail_stats['total']}건 (유형별: {fail_stats['by_type']}) · "
               f"골든셋 분포: {gstats['by_label']}")

    st.markdown("#### A2 규칙 카드 — 실패에서 태어난 지식")
    st.caption("⚡ = 카드가 곧 실행 (패턴을 런타임에 읽어 탐지에 적용) / 📄 = 선언 카드 (코드 구현 필요)")
    rows = []
    for d in reg.all():
        rows.append({"": "⚡" if d.get("pattern") else "📄",
                     "ID": d["rule_id"], "규칙": d["name"], "유형": d["type"],
                     "유래": (d.get("origin_case", "") or "")[:44] + "…"})
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.markdown(
        "> **플라이휠**: 검증 실행 → 실패 발생 → A4 기록 → 원인 분석 → "
        "규칙(A2)·사전(A1)·골든셋(A3) 자산화 → 재측정으로 개선 확인 — "
        "리뷰 탭의 '보정'이 이 루프의 입구입니다.")

st.divider()
st.caption("ClaBi × AIFFELTHON | 실데이터 검증 완료 (2026-07-14, KOSIS 실 API — 과수 농가 166,558가구 실증) | "
           "최종 판단은 검증자 리뷰로 확정")
