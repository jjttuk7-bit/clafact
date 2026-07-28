"""ClaFact MVP — Streamlit 데모 (Community Cloud 배포용).

4탭 구성:
  🔎 검증      — 기사 입력 → 자동 판정 (WF-1)
  👤 검증자 리뷰 — 승인/보정/반려, 보정은 실패 레코드로 (WF-2)
  🔥 플라이휠   — 실패 → 골든셋 → 재평가 → 규칙 → 재평가를 라이브로 (문서 20 4막)
  🔄 자산 현황  — 자산 축적 대시보드 (문서 11)
"""
import csv
import hashlib
import io
import os
import json
import tempfile
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backend.app.ingest_service import import_article_file
from clafact import audit
from clafact.assets.alias_dict import AliasDict
from clafact.assets.failures import FailureRecorder, FAILURE_TYPES
from clafact.assets.rules import RuleRegistry
from clafact.assets import goldenset
from clafact.eval import harness
from clafact.kosis import HttpKosisClient
from clafact.ops_dashboard import build_ops_claim_rows
from clafact.pipeline.ingest import load_articles
from clafact.service.batch import process_pending
from clafact.service.store import Store, stable_article_id
from clafact.pipeline import detect
from clafact.experiment_lab import run_comparison, run_mode
from clafact.experiment_eda_controller import prepare_eda
from clafact.experiment_eda_session import (
    EDA_CACHE_KEY,
    EdaCsvReadError,
    EDA_FILTER_STATE_KEYS,
    EDA_RANGE_END_KEY,
    EDA_RANGE_KEY,
    EDA_RANGE_START_KEY,
    EDA_REPORT_KEY,
    EDA_SELECTED_ARTICLE_KEY,
    EDA_VIEW_KEY,
    MAX_EDA_ROWS,
    EdaRange,
    UploadIdentity,
    UploadMetadata,
    analysis_scope_caption,
    cache_key as eda_cache_key,
    cached_upload_metadata,
    comparison_input_signature,
    hash_seekable_stream,
    invalidate_comparison_for_input,
    prepare_cache_scope,
    read_csv_range,
    resolve_eda_range,
    scan_csv_stream,
    store_upload_metadata,
)
from clafact.experiment_eda_view import (
    filter_articles,
    selected_article_rows,
)
from clafact.experiment_input import clean_uploaded_article_body
from clafact.experiment_export import (
    MAX_FILTERED_EXPORT_ROWS,
    export_filtered_csv,
    export_run_csv,
)
from clafact.experiment_history import (
    DISAGREEMENT_ORDER,
    HistoryFilters,
    PreparedHistoryExport,
    build_history_action_target,
    build_history_page,
    filter_signature,
    prepared_export_for_filters,
)
from clafact.experiment_review import (
    build_reviewed_evaluation,
    pop_review_feedback,
    promote_reviewed_sentence,
    reviewable_sentences,
    save_human_review,
    store_review_feedback,
)
from clafact.experiment_research import (
    build_run_context,
    input_matches_context,
    save_comparison_run,
    semantic_disagreement_count,
)
from clafact.experiment_store import ExperimentStore
from clafact.llm import HcxClient
from clafact.pipeline.detect_llm import SYSTEM as HCX_CANDIDATE_SYSTEM
from clafact.pipeline.detect_llm import judge_decision as hcx_judge
from clafact.pipeline.retrieve_kosis import KosisSearchIndex
from clafact.pipeline.run import verify_article, verify_sentence
from clafact.shadow_export import export_shadow_run_csv, export_shadow_run_json
from clafact.shadow_policy import ShadowPolicy
from clafact.shadow_service import ShadowLabService
from clafact.shadow_ui import (
    download_filenames, execution_status_summary, shadow_database_path, shadow_input_defaults, shadow_result_rows, summary_metrics, validate_shadow_input,
)

ROOT = Path(__file__).resolve().parent


def format_elapsed_ms(elapsed_ms: int) -> str:
    return f"{elapsed_ms / 1000:,.3f}초 ({elapsed_ms:,} ms)"


def _hcx_candidate_display(candidate, status: str) -> str:
    if status != "success":
        return f"실행 실패 ({status})"
    return "탐지" if candidate is True else "미탐지"


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
            if row["failure_kind"] == "KOSIS_CONNECTION" and row["next_retry_at"]:
                st.warning(
                    "KOSIS 연결이 지연되고 있습니다. "
                    f"다음 재시도 가능 시각: {row['next_retry_at']}"
                )
                return
            st.info("아직 판정 전입니다. 아래 버튼으로 이 수치 주장만 KOSIS 검증합니다.")
            if st.button("KOSIS 검증 실행", key=f"verify_{row['claim_id']}", type="primary"):
                verify_store = Store(ROOT / "data/service/clafact.db")
                try:
                    index, client = load_engine()
                    stats = process_pending(verify_store, index, client, claim_ids=[row["claim_id"]])
                    st.session_state["retry_feedback"] = {
                        "processed": stats["processed"],
                        "failed": stats["failed"],
                        "deferred": stats.get("deferred", 0),
                        "code_version": audit.code_version(),
                    }
                except Exception as error:
                    st.session_state["retry_feedback"] = {
                        "error": str(error), "code_version": audit.code_version(),
                    }
                finally:
                    verify_store.close()
                st.rerun()
            return
        if status == "FAILED":
            if row["failure_kind"] == "KOSIS_CONNECTION":
                st.error("KOSIS 연결 재시도가 3회 실패했습니다. 잠시 후 다시 검증해 주세요.")
            else:
                message = row["error"] or "처리 중 오류가 발생했습니다."
                st.error(message)
            if st.button("KOSIS 재검증 실행", key=f"retry_{row['claim_id']}", type="primary"):
                with st.spinner("KOSIS 재검증 중…"):
                    retry_store = Store(ROOT / "data/service/clafact.db")
                    try:
                        retry_store.retry_failed(row["claim_id"])
                        index, client = load_engine()
                        stats = process_pending(retry_store, index, client, claim_ids=[row["claim_id"]])
                        st.session_state["retry_feedback"] = {
                            "processed": stats["processed"],
                            "failed": stats["failed"],
                            "deferred": stats.get("deferred", 0),
                            "code_version": audit.code_version(),
                        }
                    except Exception as error:
                        st.session_state["retry_feedback"] = {
                            "error": str(error), "code_version": audit.code_version(),
                        }
                    finally:
                        retry_store.close()
                st.rerun()
            return
        audit_data = _stored_json(row["audit_json"])
        engine_labels = {
            "HttpKosisClient": "실 KOSIS Open API 검증",
            "FixtureKosisClient": "데모 Fixture 검증 · 실제 API 미호출",
        }
        engine_label = engine_labels.get(audit_data.get("engine"), "검증 엔진 미기록 · 이전 저장 결과")
        processed_at = row["processed_at"] or "처리 시각 미기록"
        st.caption(f"검증 엔진: {engine_label} · 처리 시각: {processed_at}")
        evidence = _stored_json(row["evidence_json"])
        if evidence:
            st.markdown(
                f"**KOSIS 근거:** {evidence.get('tbl', '통계표 정보 없음')} "
                f"→ `{evidence.get('value', '값 없음')}`"
            )
        elif audit_data.get("tbl_name"):
            st.caption(f"선택 통계표: {audit_data['tbl_name']} · 근거 행 미선택")
            if audit_data.get("params"):
                st.caption(f"KOSIS 검색·조회 조건: {audit_data['params']}")
        else:
            st.caption("KOSIS 근거: 대응 통계표를 찾지 못했습니다.")
        if row["calculation"]:
            st.markdown(f"**계산:** `{row['calculation']}`")
        if row["reason"]:
            st.caption(f"판정 근거: {row['reason']}")
        st.markdown("**HCX 설명**")
        st.write(row["explanation"] or "저장된 설명이 없습니다.")

        if audit:
            with st.expander("검증 근거 보기 · KOSIS 조회 조건"):
                st.json(audit_data, expanded=False)
CONF_ORDER = {"low": 0, "medium": 1, "high": 2, None: 3}


@st.cache_resource
def load_engine():
    client = HttpKosisClient(api_key=os.environ["KOSIS_API_KEY"])
    return KosisSearchIndex(client), client


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
  .verification-summary-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.75rem; margin:.9rem 0 1.25rem; }
  .verification-summary-card { background:var(--ops-surface); border:1px solid var(--ops-border); border-top:3px solid var(--verify-accent); border-radius:.8rem; padding:.85rem 1rem; min-height:5.8rem; }
  .verification-summary-label { color:var(--ops-muted); font-size:.76rem; font-weight:680; }
  .verification-summary-value { color:var(--ops-text); font-size:1.8rem; font-weight:780; letter-spacing:-.04em; margin-top:.3rem; }
  .verification-summary-note { color:var(--ops-muted); font-size:.73rem; margin-top:.2rem; }
  .verification-workspace { background:var(--ops-surface); border:1px solid var(--ops-border); border-radius:1rem; padding:1rem 1.15rem 1.25rem; margin:0 0 1.2rem; }
  .verification-section-title { color:var(--ops-text); font-size:1.15rem; font-weight:750; margin:0; }
  .verification-section-copy { color:var(--ops-muted); font-size:.82rem; line-height:1.5; margin:.25rem 0 .8rem; }
  .verification-action-bar { display:flex; align-items:center; justify-content:space-between; gap:1rem; background:color-mix(in srgb,#087f73 9%,var(--ops-surface)); border:1px solid color-mix(in srgb,#087f73 30%,var(--ops-border)); border-radius:.75rem; padding:.75rem .9rem; margin:.7rem 0 .85rem; }
  .verification-action-label { color:var(--ops-text); font-size:.84rem; font-weight:700; }
  .verification-action-note { color:var(--ops-muted); font-size:.75rem; }
  .verification-controls { background:var(--ops-page); border:1px solid var(--ops-border); border-radius:.75rem; padding:.75rem .9rem .85rem; margin:.25rem 0 1rem; }
  .verification-controls-title { color:var(--ops-text); font-size:.86rem; font-weight:740; margin:0 0 .25rem; }
  .verification-controls-copy { color:var(--ops-muted); font-size:.74rem; margin:0 0 .5rem; }
  .verification-claim-context { display:flex; align-items:center; justify-content:space-between; gap:.75rem; background:color-mix(in srgb,var(--primary-color) 7%,var(--ops-surface)); border:1px solid color-mix(in srgb,var(--primary-color) 25%,var(--ops-border)); border-radius:.65rem; padding:.65rem .8rem; margin:.55rem 0 .8rem; }
  .verification-claim-context strong { color:var(--ops-text); font-size:.8rem; }
  .verification-claim-context span { color:var(--ops-muted); font-size:.74rem; }
  .verification-reason { margin:.85rem 0 1rem; }
  @media (max-width:900px) { .verification-summary-grid { grid-template-columns:repeat(2,minmax(0,1fr)); } .verification-action-bar { display:block; } }
  @media (max-width:640px) { .verification-summary-grid { grid-template-columns:1fr 1fr; } .verification-workspace { padding:.85rem; } }
  @media (max-width:900px) { .ops-summary-grid { grid-template-columns:repeat(2,minmax(0,1fr)); } .ops-route-grid { grid-template-columns:1fr; } }
  @media (max-width:640px) { .ops-summary-grid { grid-template-columns:1fr 1fr; } .ops-workspace { padding:.9rem; } .ops-next-action { display:block; } }
  @media (max-width:640px) { .block-container { padding-inline:1rem; } .ops-card { min-height:6.5rem; } }
</style>
""", unsafe_allow_html=True)
st.markdown("""<section class="ops-hero"><div class="ops-kicker">ClaFact · Evidence Operations</div><h1 class="ops-title">국가통계 기반 뉴스 검증 운영</h1><p class="ops-copy">기사 등록부터 판정 근거 확인까지, 근거가 남는 검증 흐름을 한 화면에서 관리합니다.</p><span class="ops-chip">● KOSIS 연결 기준 · 검증 근거 보존</span></section>""", unsafe_allow_html=True)

NAV_ITEMS = ("운영 홈", "검증", "검증자 리뷰", "플라이휠", "자산 현황", "검증 실험실")
st.sidebar.markdown('<div class="ops-kicker">ClaFact</div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="sidebar-brand">검증 운영 콘솔</div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="sidebar-caption">근거 기반 뉴스 수치 검증과 리뷰 흐름을 관리합니다.</div>', unsafe_allow_html=True)
view = st.sidebar.radio("주요 화면", NAV_ITEMS, label_visibility="collapsed")

if view == "운영 홈":
    dashboard_initialized = st.session_state.setdefault("dashboard_initialized", False)
    if dashboard_initialized:
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
    uploader_key = st.session_state.setdefault("uploader_key", 0)
    upload_file_col, reset_upload_col = st.columns([5, 1])
    with upload_file_col:
        uploaded_csv = st.file_uploader(
            "CSV 기사 파일", type=["csv"],
            help="UTF-8 또는 UTF-8 BOM CSV 파일을 선택하세요.",
            key=f"article_csv_{uploader_key}",
        )
    with reset_upload_col:
        st.markdown("<div style='height:1.65rem'></div>", unsafe_allow_html=True)
        if st.button("새 업로드 시작", use_container_width=True, key="reset_current_upload"):
            st.session_state["dashboard_initialized"] = False
            for state_key in ("uploaded_article_ids", "upload_summary", "_upload_file_signature"):
                st.session_state.pop(state_key, None)
            st.session_state["uploader_key"] = uploader_key + 1
            st.rerun()

    if uploaded_csv is not None:
        upload_file_signature = (uploaded_csv.name, uploaded_csv.size)
        previous_file_signature = st.session_state.get("_upload_file_signature")
        if previous_file_signature is not None and previous_file_signature != upload_file_signature:
            st.session_state.pop("uploaded_article_ids", None)
            st.session_state.pop("upload_summary", None)
        st.session_state["_upload_file_signature"] = upload_file_signature

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
                st.session_state["dashboard_initialized"] = True
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
        claim_previews = upload.get("claim_previews", [])
        if claim_previews:
            st.markdown("#### KOSIS 수치 주장 추출 결과")
            st.caption("업로드한 기사 본문에서 KOSIS 분석 대상으로 분류된 문장을 모두 보여줍니다. 추출 수치가 없으면 수치 미검출로 표시합니다.")
            source_type_labels = {
                "KOSIS_DOMESTIC": "직접 조회형 KOSIS",
                "KOSIS_BUT_COMPLEX": "복합 KOSIS",
            }
            extraction_rows = [
                {
                    "기사": preview.get("title") or "제목 없음",
                    "기사 등록일": preview.get("article_date") or preview.get("date") or "미확인",
                    "수치 주장 문장": preview.get("sentence", ""),
                    "추출 수치": preview.get("quantity_display", "수치 미검출"),
                    "시점": preview.get("period") or "미검출",
                    "출처 분류": source_type_labels.get(preview.get("source_type"), preview.get("source_type", "")),
                }
                for preview in claim_previews
            ]
            st.dataframe(extraction_rows, hide_index=True, use_container_width=True)
            csv_buffer = io.StringIO()
            csv_writer = csv.DictWriter(csv_buffer, fieldnames=extraction_rows[0].keys())
            csv_writer.writeheader()
            for row in extraction_rows:
                csv_writer.writerow(row)
            st.download_button(
                "추출 결과 CSV 다운로드",
                data=csv_buffer.getvalue().encode("utf-8-sig"),
                file_name=f"clafact_kosis_claims_{datetime.now():%Y%m%d}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.info("이번 업로드에서 KOSIS 분석 대상으로 추출된 수치 주장이 없습니다.")
        st.markdown("""<div class="ops-next-action"><span class="ops-next-label">다음 행동</span><span>검증 탭에서 현재 페이지 50건을 일괄 검증하거나, 위험 Claim은 검증자 리뷰에서 확인하세요.</span></div>""", unsafe_allow_html=True)
    else:
        st.info("CSV를 등록하면 전처리·분류 요약이 표시됩니다.")# ═════════════ 탭 1: 검증 (WF-1) ═════════════
if view == "검증":
    st.markdown("""<div class="ops-section-head"><div class="ops-section-kicker">WORKFLOW 03</div><h2 class="ops-section-title">이번 업로드 검증 결과</h2><p class="ops-section-copy">저장된 KOSIS 판정과 HCX 설명을 확인하고, 필요한 Claim만 다시 검증합니다.</p></div>""", unsafe_allow_html=True)
    st.caption(f"현재 실행 코드: {audit.code_version()}")
    retry_feedback = st.session_state.pop("retry_feedback", None)
    if retry_feedback:
        if retry_feedback.get("error"):
            st.error(f"재검증 실행 오류: {retry_feedback['error']}")
        elif retry_feedback.get("deferred", 0):
            st.warning(f"KOSIS 연결이 지연되어 {retry_feedback['deferred']}건을 재시도 대기 상태로 예약했습니다.")
        elif retry_feedback["failed"]:
            st.warning(f"재검증 완료 · 처리 {retry_feedback['processed']}건 · 실패 {retry_feedback['failed']}건")
        else:
            st.success(f"재검증 완료 · 처리 {retry_feedback['processed']}건 · 실패 0건")
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
            st.markdown("""<div class="verification-reason"><h3 class="verification-section-title">판단불가 사유</h3><p class="verification-section-copy">자동 검증으로 결론을 내리지 못한 Claim을 사유별로 묶었습니다.</p></div>""", unsafe_allow_html=True)
            st.dataframe(
                [{"사유": reason, "건수": count} for reason, count in sorted(reason_counts.items())],
                hide_index=True,
                use_container_width=True,
            )

        if official_announcements:
            st.markdown("""<div class="verification-reason"><h3 class="verification-section-title">공식 공지 확인 필요</h3><p class="verification-section-copy">KOSIS 표 해당 없음 · 공식 공지 검증 · 공식 기관 공지는 별도 근거를 등록합니다.</p></div>""", unsafe_allow_html=True)
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
            st.markdown("""<h3 class="verification-section-title">검증 현황</h3>""", unsafe_allow_html=True)
            st.markdown(f"""<div class="verification-summary-grid">
              <div class="verification-summary-card" style="--verify-accent:#46d5c7"><div class="verification-summary-label">이번 업로드 수치 주장</div><div class="verification-summary-value">{len(upload_results):,}</div><div class="verification-summary-note">전체 검증 후보</div></div>
              <div class="verification-summary-card" style="--verify-accent:#087f73"><div class="verification-summary-label">판정 완료</div><div class="verification-summary-value">{completed:,}</div><div class="verification-summary-note">검증 결과 저장</div></div>
              <div class="verification-summary-card" style="--verify-accent:#d99718"><div class="verification-summary-label">처리 대기</div><div class="verification-summary-value">{pending:,}</div><div class="verification-summary-note">다음 검증 대상</div></div>
              <div class="verification-summary-card" style="--verify-accent:#ed7b72"><div class="verification-summary-label">처리 실패</div><div class="verification-summary-value">{failed:,}</div><div class="verification-summary-note">오류 확인 필요</div></div>
            </div>""", unsafe_allow_html=True)
            st.markdown("""<div class="verification-workspace"><h3 class="verification-section-title">검증 작업</h3><p class="verification-section-copy">기사 단위로 확인하거나 전체 Claim을 필터링해 일괄 검증할 수 있습니다.</p>
            <div class="verification-controls"><div class="verification-controls-title">검증 대상 선택</div><p class="verification-controls-copy">선택한 기사만 보거나 전체 수치 주장을 검색할 수 있습니다.</p></div>""", unsafe_allow_html=True)
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
                st.markdown(f"""<div class="verification-action-bar"><span class="verification-action-label">일괄 검증</span><span class="verification-action-note">현재 페이지 대기 Claim {len(pending_ids):,}건 · 최대 50건 처리</span></div>""", unsafe_allow_html=True)
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
                pending_selected_ids = [row["claim_id"] for row in selected if row["status"] == "PENDING"]
                st.markdown(f"""<div class="verification-claim-context"><strong>선택한 기사</strong><span>수치 주장 {len(selected):,}건 · 대기 {len(pending_selected_ids):,}건</span></div>""", unsafe_allow_html=True)
                if pending_selected_ids:
                    st.markdown(f"""<div class="verification-action-bar"><span class="verification-action-label">선택 기사 검증</span><span class="verification-action-note">이 기사에서 대기 중인 Claim {len(pending_selected_ids):,}건을 검증합니다.</span></div>""", unsafe_allow_html=True)
                    if st.button("선택 기사 검증 실행", key="verify_selected_article", type="primary", use_container_width=True):
                        selected_store = Store(ROOT / "data/service/clafact.db")
                        try:
                            index, client = load_engine()
                            stats = process_pending(selected_store, index, client, claim_ids=pending_selected_ids)
                            st.success(f"기사 검증 완료 · 처리 {stats['processed']}건 · 실패 {stats['failed']}건")
                        except Exception as error:
                            st.error(f"검증 실패: {error}")
                        finally:
                            selected_store.close()
                        st.rerun()
                else:
                    st.success("선택한 기사의 대기 Claim이 없습니다. 아래에서 저장된 결과를 확인하세요.")
                for number, row in enumerate(selected, start=1):
                    render_stored_claim(row, number)
            st.markdown("</div>", unsafe_allow_html=True)
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

# ═════════════ 검증 실험실: 운영과 분리된 엔진 비교 ═════════════
if view == "검증 실험실":
    st.markdown("#### 검증 실험실")
    st.info("이 화면은 운영 Claim·리뷰 큐·판정 이력을 변경하지 않는 연구 전용 공간입니다.")
    existing_lab_tab, shadow_lab_tab = st.tabs(("기존 비교 실험", "Shadow Mode"))

    with existing_lab_tab:
        st.markdown("#### 검증 실험실")
        st.info("이 화면은 운영 Claim·리뷰 큐·판정 이력을 변경하지 않습니다. 동일한 문장을 Python 규칙만, HCX-005만, 하이브리드 방식으로 비교합니다.")
        st.caption("최종 KOSIS 판정 화면이 아니라 수치 주장 탐지·문맥 판별의 연구용 비교 화면입니다.")

        lab_csv = st.file_uploader("검증 실험실 CSV 파일", type=["csv"], key="experiment_lab_csv", help="기존 기사 CSV의 body/본문/content/text 열을 사용하며 운영 데이터에는 저장하지 않습니다.")
        selected_lab_article = None
        lab_source_row_count = 1
        lab_signature = ""
        upload_identity = None
        selected_eda_range = None
        if lab_csv is not None:
            upload_identity = UploadIdentity(
                file_id=str(getattr(lab_csv, "file_id", "")),
                name=str(lab_csv.name),
                size=int(lab_csv.size),
            )
            upload_metadata = cached_upload_metadata(st.session_state, upload_identity)
            scan = None
            if upload_metadata is None:
                try:
                    lab_signature = hash_seekable_stream(lab_csv)
                    scan = scan_csv_stream(lab_csv)
                except UnicodeDecodeError:
                    st.error("CSV 파일은 UTF-8 또는 UTF-8 BOM 인코딩이어야 합니다.")
                except EdaCsvReadError as error:
                    st.error(error.user_message)
                else:
                    upload_metadata = UploadMetadata(
                        identity=upload_identity,
                        signature=lab_signature,
                        row_count=scan.row_count,
                    )
                    store_upload_metadata(st.session_state, upload_metadata)
            else:
                lab_signature = upload_metadata.signature

            lab_source_row_count = upload_metadata.row_count if upload_metadata else 0
            selected_eda_range = None
            range_submitted = False

            if upload_metadata and lab_source_row_count > MAX_EDA_ROWS:
                st.info(
                    f"CSV가 {MAX_EDA_ROWS:,}행을 초과합니다. 자동 분석하지 않으며 "
                    f"한 번에 최대 {MAX_EDA_ROWS:,}행의 범위를 확정해 분석합니다."
                )
                with st.form("experiment_eda_range_form"):
                    range_start = st.number_input(
                        "분석 시작 행",
                        min_value=1,
                        max_value=lab_source_row_count,
                        value=1,
                        step=1,
                        key=EDA_RANGE_START_KEY,
                    )
                    range_end = st.number_input(
                        "분석 종료 행",
                        min_value=1,
                        max_value=lab_source_row_count,
                        value=min(MAX_EDA_ROWS, lab_source_row_count),
                        step=1,
                        key=EDA_RANGE_END_KEY,
                    )
                    range_submitted = st.form_submit_button("분석 범위 확정", width="stretch")
                if range_submitted:
                    try:
                        st.session_state[EDA_RANGE_KEY] = resolve_eda_range(
                            lab_source_row_count,
                            EdaRange(int(range_start), int(range_end)),
                            confirmed=range_submitted,
                        )
                    except ValueError as error:
                        st.session_state.pop(EDA_RANGE_KEY, None)
                        st.error(str(error))
                selected_eda_range = st.session_state.get(EDA_RANGE_KEY)
            elif upload_metadata:
                selected_eda_range = resolve_eda_range(lab_source_row_count)

            eda_report = None
            eda_view = None
            if upload_metadata and lab_source_row_count == 0:
                empty_preparation = prepare_eda(())
                if empty_preparation.status == "empty":
                    st.warning(empty_preparation.user_message)
            elif selected_eda_range is not None:
                current_cache_key = eda_cache_key(lab_signature, selected_eda_range)
                same_cache_scope = st.session_state.get(EDA_CACHE_KEY) == current_cache_key
                if not same_cache_scope:
                    prepare_cache_scope(st.session_state, current_cache_key)
                    selected_rows = None
                    try:
                        if lab_source_row_count > MAX_EDA_ROWS:
                            selected_rows = read_csv_range(lab_csv, selected_eda_range)
                        else:
                            small_scan = scan if scan is not None else scan_csv_stream(lab_csv)
                            selected_rows = small_scan.rows
                    except UnicodeDecodeError:
                        st.error("CSV 파일은 UTF-8 또는 UTF-8 BOM 인코딩이어야 합니다.")
                        st.session_state.pop(EDA_CACHE_KEY, None)
                    except EdaCsvReadError as error:
                        st.error(error.user_message)
                        st.session_state.pop(EDA_CACHE_KEY, None)
                    if selected_rows is not None:
                        prepared = prepare_eda(
                            selected_rows,
                            row_number_start=selected_eda_range.start,
                        )
                        if prepared.status == "empty":
                            st.warning(prepared.user_message)
                        else:
                            eda_report = prepared.report
                            eda_view = prepared.view
                            st.session_state[EDA_REPORT_KEY] = eda_report
                            st.session_state[EDA_VIEW_KEY] = eda_view
                else:
                    eda_report = st.session_state.get(EDA_REPORT_KEY)
                    eda_view = st.session_state.get(EDA_VIEW_KEY)
            if eda_report is not None and eda_view is not None:
                csv_articles = [
                    {
                        "row_number": article.row_number,
                        "title": article.title,
                        "date": article.article_date,
                        "body": article.cleaned_body,
                    }
                    for article in eda_report.articles
                ]
                st.caption(
                    f"CSV 유효 기사 {eda_report.valid_article_count:,}건 · "
                    f"제외 {eda_report.excluded_article_count:,}건 · 자동 일괄 실행하지 않습니다. "
                    "비교할 기사 한 건을 선택하세요."
                )
                st.caption(analysis_scope_caption(
                    lab_source_row_count,
                    selected_eda_range,
                ))
                with st.expander("CSV 통합 EDA", expanded=True):
                    st.caption(
                        "EDA는 Python 규칙만 사용하며 HCX를 자동 호출하지 않습니다. "
                        "body, 본문, 기사 본문 전체, content, text 열에서 읽은 업로드 데이터만 분석합니다."
                    )

                    st.markdown("##### 1. 데이터 품질")
                    quality_columns = st.columns(len(eda_view.quality_kpis))
                    for column, card in zip(quality_columns, eda_view.quality_kpis):
                        column.metric(card.label, f"{card.value:,}")
                        column.caption(card.note)
                    if eda_view.issue_reason_rows:
                        st.caption("제외·경고 사유")
                        st.bar_chart(
                            [
                                {"사유": row.label, "건수": row.value}
                                for row in eda_view.issue_reason_rows
                            ],
                            x="사유",
                            y="건수",
                            horizontal=True,
                            width="stretch",
                        )
                    if eda_view.problem_rows.rows:
                        st.dataframe(
                            [
                                {
                                    "원본 행": row.row_number,
                                    "제목": row.title or "제목 없음",
                                    "문제": row.issue,
                                }
                                for row in eda_view.problem_rows.rows
                            ],
                            hide_index=True,
                            width="stretch",
                        )
                        if eda_view.problem_rows.truncated:
                            st.caption(
                                f"문제 {eda_view.problem_rows.total:,}건 중 "
                                f"앞 {eda_view.problem_rows.limit:,}건만 표시합니다."
                            )

                    st.markdown("##### 2. 기사 구조")
                    body_stats = eda_view.structure_stats.body_length
                    sentence_stats = eda_view.structure_stats.sentence_count
                    structure_columns = st.columns(4)
                    structure_columns[0].metric("본문 길이 중앙값", f"{body_stats.median:,.0f}자")
                    structure_columns[1].metric("본문 길이 평균", f"{body_stats.mean:,.1f}자")
                    structure_columns[2].metric("문장 수 중앙값", f"{sentence_stats.median:,.0f}개")
                    structure_columns[3].metric("문장 수 평균", f"{sentence_stats.mean:,.1f}개")
                    st.caption(
                        f"본문 Q1~Q3 {body_stats.q1:,.0f}~{body_stats.q3:,.0f}자 · "
                        f"문장 Q1~Q3 {sentence_stats.q1:,.0f}~{sentence_stats.q3:,.0f}개"
                    )
                    if eda_view.structure_chart_mode == "single" and eda_report.articles:
                        only_article = eda_report.articles[0]
                        single_columns = st.columns(4)
                        single_columns[0].metric("정제 전", f"{only_article.raw_length:,}자")
                        single_columns[1].metric("정제 후", f"{only_article.clean_length:,}자")
                        single_columns[2].metric("제거 문자", f"{only_article.removed_length:,}자")
                        single_columns[3].metric("문장", f"{len(only_article.sentences):,}개")
                        st.caption("기사 1건은 의미 없는 분포 차트 대신 실제 정제·문장 지표를 표시합니다.")
                    elif eda_view.structure_chart_mode == "distribution":
                        body_chart, sentence_chart = st.columns(2)
                        body_chart.caption("정제 후 본문 길이 분포")
                        body_chart.bar_chart(
                            [{"구간": row.label, "기사": row.value} for row in eda_view.body_length_bins],
                            x="구간",
                            y="기사",
                            width="stretch",
                        )
                        sentence_chart.caption("기사별 문장 수 분포")
                        sentence_chart.bar_chart(
                            [{"구간": row.label, "기사": row.value} for row in eda_view.sentence_count_bins],
                            x="구간",
                            y="기사",
                            width="stretch",
                        )

                    st.markdown("##### 3. 수치 주장 특성")
                    for offset in range(0, len(eda_view.claim_kpis), 3):
                        claim_columns = st.columns(3)
                        for column, card in zip(claim_columns, eda_view.claim_kpis[offset:offset + 3]):
                            column.metric(card.label, f"{card.value:,}")
                    st.caption("서로 겹칠 수 있는 독립 집계이며 단계별 퍼널이 아닙니다.")
                    category_specs = (
                        ("수치 유형", eda_view.quantity_rows),
                        ("해석 시점", eda_view.period_rows),
                        ("주장 유형", eda_view.claim_type_rows),
                        ("라우팅", eda_view.route_rows),
                    )
                    category_columns = st.columns(2)
                    for index, (label, rows) in enumerate(category_specs):
                        category_columns[index % 2].caption(label)
                        category_columns[index % 2].bar_chart(
                            [{"유형": row.label, "건수": row.value} for row in rows],
                            x="유형",
                            y="건수",
                            horizontal=True,
                            width="stretch",
                        )

                    st.markdown("##### 4. 기사 탐색·상세")
                    candidate_ceiling = max(
                        (sum(sentence.python_candidate for sentence in article.sentences) for article in eda_report.articles),
                        default=0,
                    )
                    with st.form("experiment_eda_article_filters"):
                        filter_columns = st.columns(4)
                        quality_filter = filter_columns[0].selectbox(
                            "품질",
                            options=("all", "warnings", "outliers", "clean"),
                            format_func=lambda value: {
                                "all": "전체",
                                "warnings": "품질 경고",
                                "outliers": "구조 이상치",
                                "clean": "문제 없음",
                            }[value],
                            key=EDA_FILTER_STATE_KEYS[0],
                        )
                        body_filter = filter_columns[1].selectbox(
                            "본문 길이",
                            options=("all", "short", "typical", "long"),
                            format_func=lambda value: {
                                "all": "전체",
                                "short": "짧음",
                                "typical": "보통",
                                "long": "김",
                            }[value],
                            key=EDA_FILTER_STATE_KEYS[1],
                        )
                        min_candidates = filter_columns[2].number_input(
                            "최소 Python 후보",
                            min_value=0,
                            max_value=candidate_ceiling,
                            value=0,
                            key=EDA_FILTER_STATE_KEYS[2],
                        )
                        max_candidates = filter_columns[3].number_input(
                            "최대 Python 후보",
                            min_value=0,
                            max_value=candidate_ceiling,
                            value=candidate_ceiling,
                            key=EDA_FILTER_STATE_KEYS[3],
                        )
                        st.form_submit_button("기사 필터 적용", width="stretch")

                    if int(max_candidates) < int(min_candidates):
                        st.warning("최대 Python 후보 수는 최소값 이상이어야 합니다.")
                        filtered_articles = ()
                    else:
                        filtered_articles = filter_articles(
                            eda_report,
                            quality=quality_filter,
                            body_band=body_filter,
                            min_candidates=int(min_candidates),
                            max_candidates=int(max_candidates),
                        )
                    if not filtered_articles:
                        st.warning("현재 필터에 맞는 기사가 없습니다.")
                        st.session_state.pop(EDA_SELECTED_ARTICLE_KEY, None)
                    else:
                        article_by_row = {article.row_number: article for article in filtered_articles}
                        selected_row_numbers = tuple(article_by_row)
                        if st.session_state.get(EDA_SELECTED_ARTICLE_KEY) not in selected_row_numbers:
                            st.session_state[EDA_SELECTED_ARTICLE_KEY] = selected_row_numbers[0]
                        selected_row_number = st.selectbox(
                            "기사 선택",
                            options=selected_row_numbers,
                            format_func=lambda row_number: (
                                f"{article_by_row[row_number].title or '제목 없음'} · "
                                f"{article_by_row[row_number].article_date or '날짜 없음'} "
                                f"(행 {row_number})"
                            ),
                            key=EDA_SELECTED_ARTICLE_KEY,
                        )
                        selected_article = article_by_row[selected_row_number]
                        selected_lab_article = {
                            "row_number": selected_article.row_number,
                            "title": selected_article.title,
                            "date": selected_article.article_date,
                            "body": selected_article.cleaned_body,
                        }
                        article_metrics = st.columns(4)
                        article_metrics[0].metric("정제 전", f"{selected_article.raw_length:,}자")
                        article_metrics[1].metric("정제 후", f"{selected_article.clean_length:,}자")
                        article_metrics[2].metric("문장", f"{len(selected_article.sentences):,}개")
                        article_metrics[3].metric(
                            "Python 후보",
                            f"{sum(sentence.python_candidate for sentence in selected_article.sentences):,}개",
                        )
                        evidence_rows = selected_article_rows(selected_article)
                        st.dataframe(
                            [
                                {
                                    "문장": row.sentence,
                                    "추출 수치": " · ".join(row.quantities),
                                    "수치 포함": row.numeric,
                                    "시점": row.period or row.period_class,
                                    "주장 유형": row.claim_type,
                                    "라우팅": row.route,
                                    "Python 후보": row.python_candidate,
                                    "적용 규칙": row.python_rule,
                                    "Python 근거": row.python_reason,
                                }
                                for row in evidence_rows
                            ],
                            hide_index=True,
                            width="stretch",
                        )
            elif lab_source_row_count and lab_source_row_count <= MAX_EDA_ROWS:
                st.warning("본문 열(body, 본문, 기사 본문 전체, content, text)이 있는 기사를 찾지 못했습니다.")
        lab_date = st.date_input("기사 발행일", value=datetime.now().date(), key="experiment_lab_date")
        lab_text = st.text_area("비교할 기사 본문", key="experiment_lab_text", height=180,
                                placeholder="예: 지난해 실업률은 2.7%였다. 내년에는 3%까지 오를 전망이다.")
        hcx_available = os.environ.get("CLAFACT_HCX_MODE", "fixture").lower() == "live" and bool(os.environ.get("HCX_API_KEY"))
        comparison_text = lab_text
        comparison_date = str(lab_date)
        comparison_title = "직접 입력"
        if selected_lab_article:
            comparison_text = selected_lab_article["body"]
            comparison_date = selected_lab_article["date"] or comparison_date
            comparison_title = selected_lab_article["title"] or "제목 없음"
            st.caption(f"CSV 선택 기사: {selected_lab_article['title'] or '제목 없음'} · 본문 직접 입력보다 우선해 비교합니다.")

        current_comparison_signature = comparison_input_signature(
            text=comparison_text,
            article_date=comparison_date,
            title=comparison_title,
            source_row=selected_lab_article["row_number"] if selected_lab_article else None,
            file_signature=lab_signature,
            upload_identity=upload_identity,
            analysis_range=selected_eda_range,
        )
        invalidate_comparison_for_input(st.session_state, current_comparison_signature)
        if hcx_available:
            st.caption("HCX 모드: HCX-005 실호출 · 호출 수와 처리시간을 함께 기록합니다.")
        else:
            st.warning("HCX 모드: 실 API 미설정 — Python 결과는 비교할 수 있지만 HCX 열은 ‘미사용’으로 표시됩니다.")

        all_button, python_button, llm_button, hybrid_button = st.columns(4)
        run_all = all_button.button("전체 비교 실행", type="primary", use_container_width=True, key="experiment_lab_run_all")
        run_python = python_button.button("Python만 실행", use_container_width=True, key="experiment_lab_run_python")
        run_llm = llm_button.button("HCX만 실행", use_container_width=True, key="experiment_lab_run_llm")
        run_hybrid = hybrid_button.button("하이브리드만 실행", use_container_width=True, key="experiment_lab_run_hybrid")
        requested_mode = "all" if run_all else ("python" if run_python else ("llm" if run_llm else ("hybrid" if run_hybrid else None)))
        if requested_mode:
            if not comparison_text.strip():
                st.error("비교할 기사 본문을 입력해 주세요.")
            else:
                if hcx_available:
                    client = HcxClient()
                    judge_fn = lambda sentence: hcx_judge(sentence, client)
                else:
                    def judge_fn(_sentence):
                        raise RuntimeError("HCX 실 API가 설정되지 않았습니다")
                with st.spinner("선택한 방식을 독립 실행 중…"):
                    if requested_mode == "all":
                        st.session_state["experiment_lab_result"] = run_comparison(comparison_text, comparison_date, judge_fn=judge_fn)
                        prompt_hash = hashlib.sha256(HCX_CANDIDATE_SYSTEM.encode("utf-8")).hexdigest()[:12]
                        st.session_state["experiment_lab_run_context"] = build_run_context(
                            article_text=comparison_text,
                            article_title=comparison_title,
                            article_date=comparison_date,
                            source_row_count=lab_source_row_count,
                            prompt_version=f"candidate-evidence-v2:{prompt_hash}",
                        )
                        st.session_state.pop("experiment_lab_saved_run_id", None)
                        st.session_state.pop("experiment_lab_mode_result", None)
                    else:
                        st.session_state["experiment_lab_mode_result"] = (requested_mode, run_mode(comparison_text, comparison_date, requested_mode, judge_fn=judge_fn))
                        st.session_state.pop("experiment_lab_result", None)
                        st.session_state.pop("experiment_lab_run_context", None)

        hcx_evidence_labels = {
            "sufficient": "기사 내부 근거 충분",
            "needs_retrieval": "검색 필요",
            "not_applicable": "해당 없음",
            "unknown": "확인 불가",
        }
        def hcx_evidence_label(status: str) -> str:
            return hcx_evidence_labels.get(status, "확인 불가")

        result = st.session_state.get("experiment_lab_result")
        mode_execution = st.session_state.get("experiment_lab_mode_result")
        if mode_execution:
            mode_name, mode_result = mode_execution
            candidate_count = sum(row.candidate is True for row in mode_result.rows)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Python 후보 문장", f"{candidate_count} / {len(mode_result.rows)}" if mode_name == "python" else "미실행")
            c2.metric("HCX 후보 문장", (f"{candidate_count} / {len(mode_result.rows)}" if hcx_available else "미사용") if mode_name == "llm" else "미실행")
            c3.metric("하이브리드 후보 문장", f"{candidate_count} / {len(mode_result.rows)}" if mode_name == "hybrid" else "미실행")
            c4.metric(f"{'HCX' if mode_name == 'llm' else mode_name.upper()} 처리 시간", format_elapsed_ms(mode_result.elapsed_ms))
            st.caption(f"문장 {len(mode_result.rows)}개 · 선택한 {'HCX' if mode_name == 'llm' else mode_name.upper()} 방식만 실행했습니다.")
            st.markdown("##### 방식별 판단 근거")
            for number, row in enumerate(mode_result.rows, start=1):
                with st.expander(f"{number}. {row.sentence}", expanded=False):
                    evidence_label = "Python 규칙 근거" if mode_name == "python" else ("HCX 판단 근거" if mode_name == "llm" else "하이브리드 결합 근거 · Python 1차 → LLM 2차")
                    st.write(f"**{evidence_label}:** {'탐지' if row.candidate is True else ('미탐지' if row.candidate is False else '미사용')} · {row.reason}")
                    if mode_name != "python":
                        st.write(f"**HCX 근거 상태:** {hcx_evidence_label(row.evidence_status)} · {row.evidence_reason}")
                        if row.quoted_spans:
                            st.caption(f"HCX 원문 인용: {' · '.join(row.quoted_spans)}")
                    st.caption(f"원문 수치: {' · '.join(row.quantities) or '-'} | 해석 시점: {row.parsed_period or '-'} | 주장 유형: {row.claim_type} | 후속 라우팅 (사실 검증 아님): {row.route}")

        if result:
            python_count = sum(row.python_candidate for row in result.rows)
            llm_count = sum(row.llm_verifiable is True for row in result.rows)
            hybrid_count = sum(row.hybrid_candidate for row in result.rows)
            semantic_differing_count = semantic_disagreement_count(result)
            mode_results = getattr(result, "mode_results", {})
            run_context = st.session_state.get("experiment_lab_run_context")
            if run_context:
                st.caption(f"실행 입력 지문: `{run_context.input_fingerprint}` · 실행 ID: `{run_context.run_id}`")
            if mode_results:
                st.markdown("##### 방식별 실행 시간")
                t1, t2, t3, t4 = st.columns(4)
                t1.metric("Python만", format_elapsed_ms(mode_results['python'].elapsed_ms))
                t2.metric("HCX-005만", format_elapsed_ms(mode_results['llm'].elapsed_ms))
                t3.metric("하이브리드만", format_elapsed_ms(mode_results['hybrid'].elapsed_ms))
                t4.metric("전체 비교 경과시간", format_elapsed_ms(result.elapsed_ms))

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Python 후보 문장", f"{python_count} / {len(result.rows)}")
            c2.metric("HCX 후보 문장", f"{llm_count} / {len(result.rows)}" if hcx_available else "미사용")
            c3.metric("하이브리드 후보 문장", f"{hybrid_count} / {len(result.rows)}")
            c4.metric("전체 비교 경과시간", format_elapsed_ms(result.elapsed_ms))
            st.caption(f"문장 {len(result.rows)}개 · HCX 호출 {result.llm_calls}회 · 의미 불일치 문장 {semantic_differing_count}개")

            st.markdown("##### Python × HCX 결과 매트릭스")
            disagreement_order = ("P+/H+", "P+/H-", "P-/H+", "P-/H-", "HCX_ERROR")
            disagreement_labels = {
                "P+/H+": "둘 다 탐지",
                "P+/H-": "Python만 탐지",
                "P-/H+": "HCX만 탐지",
                "P-/H-": "둘 다 미탐지",
                "HCX_ERROR": "HCX 오류",
            }
            outcome_columns = st.columns(5)
            outcome_total = len(result.rows)
            for column, outcome in zip(outcome_columns, disagreement_order):
                count = result.disagreement_counts.get(outcome, 0)
                percentage = (count / outcome_total * 100) if outcome_total else 0.0
                column.metric(f"{outcome} · {disagreement_labels[outcome]}", f"{count}건 · {percentage:.1f}%")
            st.caption("HCX_ERROR는 의미적 미탐지(H-)에서 제외합니다. 호출·파싱 실패를 P+/H- 또는 P-/H-로 해석하지 않습니다.")

            selected_outcome = st.selectbox("유형 필터", ["전체", *disagreement_order], key="experiment_lab_disagreement_filter")
            filtered_disagreement_rows = [
                (number, row) for number, row in enumerate(result.rows, start=1)
                if selected_outcome == "전체" or row.disagreement_class == selected_outcome
            ]
            display_rows = []
            for number, row in filtered_disagreement_rows:
                display_rows.append({
                    "#": number,
                    "유형": row.disagreement_class,
                    "문장": row.sentence,
                    "Python": "탐지" if row.python_candidate else "미탐지",
                    "Python 판단 근거": getattr(mode_results["python"].rows[number - 1], "reason", ""),
                    "HCX": _hcx_candidate_display(row.llm_verifiable, row.hcx_status),
                    "HCX 상태": row.hcx_status,
                    "HCX 판단 근거": row.llm_reason,
                    "HCX 근거 상태": hcx_evidence_label(row.hcx_evidence_status),
                })
            st.dataframe(display_rows, use_container_width=True, hide_index=True)

            st.markdown("##### 방식별 판단 근거")
            for number, row in filtered_disagreement_rows:
                with st.expander(f"{number}. {row.sentence}", expanded=False):
                    python_reason = mode_results["python"].rows[number - 1].reason
                    hcx_candidate_display = _hcx_candidate_display(row.llm_verifiable, row.hcx_status)
                    st.write(f"**Python 판단 근거:** {'탐지' if row.python_candidate else '미탐지'} · {python_reason}")
                    st.write(f"**HCX-005만:** {hcx_candidate_display}")
                    st.write(f"**HCX 실행 상태:** {row.hcx_status}")
                    st.write(f"**HCX 후보 판단 근거:** {row.llm_reason}")
                    st.write(f"**HCX 근거 판단:** {hcx_evidence_label(row.hcx_evidence_status)} · {row.hcx_evidence_reason}")
                    if row.hcx_quoted_spans:
                        st.caption(f"HCX 원문 인용: {' · '.join(row.hcx_quoted_spans)}")
                    st.write(f"**하이브리드:** {'탐지' if row.hybrid_candidate else '미탐지'} · {row.hybrid_reason}")
                    st.caption(f"원문 수치: {' · '.join(row.quantities) or '-'} | 해석 시점: {row.parsed_period or '-'} | 주장 유형: {row.claim_type} | 후속 라우팅 (사실 검증 아님): {row.route}")

            input_matches_run = bool(run_context) and input_matches_context(comparison_text, comparison_date, run_context)
            already_saved = bool(run_context) and st.session_state.get("experiment_lab_saved_run_id") == run_context.run_id
            save_disabled = not input_matches_run or already_saved
            if run_context and not input_matches_run:
                st.warning("현재 입력이 이 전체 비교 실행의 입력과 달라 저장할 수 없습니다. 전체 비교를 다시 실행해 주세요.")
            if already_saved:
                st.info(f"이 실행은 이미 연구 이력에 저장되었습니다. 실행 ID: {run_context.run_id}")
            save_research = st.button(
                "연구 이력 저장",
                key="experiment_lab_save_research",
                disabled=save_disabled,
            )
            if save_research:
                try:
                    save_outcome = save_comparison_run(
                        ROOT / "data/research/verification_lab.db", result, run_context
                    )
                except Exception as error:
                    st.error(f"연구 이력 저장 실패: {error}")
                else:
                    st.session_state["experiment_lab_saved_run_id"] = save_outcome.run_id
                    if save_outcome.created:
                        st.success(f"연구 전용 이력에 저장했습니다. 실행 ID: {save_outcome.run_id}")
                    else:
                        st.info(f"이미 저장된 실행입니다. 실행 ID: {save_outcome.run_id}")
            saved_run_id = st.session_state.get("experiment_lab_saved_run_id")
            saved_current_run = bool(run_context) and saved_run_id == run_context.run_id
            if saved_current_run:
                research_feedback = pop_review_feedback(st.session_state)
                if research_feedback:
                    st.success(research_feedback)
                research_database = ROOT / "data/research/verification_lab.db"
                try:
                    with ExperimentStore(research_database) as research_store:
                        saved_run = research_store.get_run(saved_run_id)
                        if saved_run is None:
                            raise KeyError(saved_run_id)
                        saved_sentences = research_store.get_sentences(saved_run_id)
                        csv_payload = export_run_csv(research_store, saved_run_id)
                except Exception as error:
                    st.error(f"저장된 연구 이력을 불러오지 못했습니다: {error}")
                else:
                    evaluation_display = build_reviewed_evaluation(saved_sentences, saved_run)
                    if evaluation_display is not None:
                        st.subheader("사람 검토 기반 평가")
                        st.caption(
                            f"{evaluation_display.metric_scope_label} · "
                            f"{evaluation_display.run_label} · "
                            "전체 기사 문장 성능이 아닙니다."
                        )
                        st.caption(
                            f"사람 검토 완료 정답 표본: {evaluation_display.reviewed_count}건 · "
                            "방식별 평가 표본은 아래 표에 별도 표시합니다."
                        )
                        st.dataframe(
                            list(evaluation_display.rows),
                            use_container_width=True,
                            hide_index=True,
                        )
                        st.caption(
                            "TP·FP·FN·TN을 함께 표시합니다. 정밀도 또는 재현율의 "
                            "분모가 0이면 0%가 아니라 ‘산출 불가’입니다."
                        )
                        st.caption(
                            "독립 HCX 문장 판정 응답률: "
                            f"{evaluation_display.independent_hcx_response_success} / "
                            f"{evaluation_display.independent_hcx_response_total} "
                            f"({evaluation_display.independent_hcx_response_rate})"
                        )
                        st.caption(
                            "HCX 오류 행은 HCX 정밀도·재현율 표본에서 제외합니다. "
                            "Python OR HCX는 HCX 오류 시 Python 결과를 유지합니다."
                        )

                    st.markdown("##### 저장된 실행 검토·내보내기")
                    st.download_button(
                        "현재 실행 CSV 다운로드",
                        data=csv_payload,
                        file_name=f"verification_lab_{saved_run_id}.csv",
                        mime="text/csv; charset=utf-8",
                        key="experiment_lab_download_saved_csv",
                    )
                    review_sentences = reviewable_sentences(saved_sentences)
                    review_choices = {
                        f"{row['sentence_index']}. {row['sentence_text'][:90]}": row["sentence_index"]
                        for row in review_sentences
                    }
                    if not review_choices:
                        st.info("사람 검토 대상 P+/H- 또는 P-/H+ 문장이 없습니다.")
                    else:
                        selected_review_text = st.selectbox(
                            "사람 검토 문장",
                            list(review_choices),
                            key="experiment_lab_review_sentence",
                        )
                        selected_review_index = review_choices[selected_review_text]
                        selected_saved_sentence = next(
                            row for row in saved_sentences
                            if row["sentence_index"] == selected_review_index
                        )
                        review_labels = ["true_candidate", "false_positive", "hold"]
                        current_label = selected_saved_sentence.get("human_label")
                        review_label = st.selectbox(
                            "사람 검토 라벨",
                            review_labels,
                            index=review_labels.index(current_label) if current_label in review_labels else 2,
                            format_func=lambda value: {
                                "true_candidate": "실제 검증 후보",
                                "false_positive": "오탐",
                                "hold": "보류",
                            }[value],
                            key=f"experiment_lab_review_label_{selected_review_index}",
                        )
                        review_note = st.text_area(
                            "검토 메모",
                            value=selected_saved_sentence.get("review_note") or "",
                            key=f"experiment_lab_review_note_{selected_review_index}",
                        )
                        save_human_review_clicked = st.button(
                            "사람 검토 저장",
                            key=f"experiment_lab_save_review_{selected_review_index}",
                        )
                        if save_human_review_clicked:
                            try:
                                review_message = save_human_review(
                                    research_database,
                                    saved_run_id,
                                    selected_review_index,
                                    human_label=review_label,
                                    review_note=review_note,
                                    reviewed_at=datetime.now().astimezone().isoformat(timespec="milliseconds"),
                                )
                            except Exception as error:
                                st.error(f"사람 검토 저장 실패: {error}")
                            else:
                                store_review_feedback(st.session_state, review_message)
                                st.rerun()

                        promotable = selected_saved_sentence.get("human_label") in {
                            "true_candidate", "false_positive"
                        }
                        promote_golden = st.button(
                            "승인 사례를 골든셋으로 승격",
                            key=f"experiment_lab_promote_golden_{selected_review_index}",
                            disabled=not promotable,
                        )
                        if not promotable:
                            st.caption("실제 검증 후보 또는 오탐으로 저장된 문장만 골든셋에 승격할 수 있습니다.")
                        if promote_golden:
                            try:
                                promote_reviewed_sentence(
                                    research_database,
                                    saved_run_id,
                                    selected_review_index,
                                    ROOT / "data/goldenset/hybrid_disagreements_v0.jsonl",
                                )
                            except Exception as error:
                                st.error(f"골든셋 승격 실패: {error}")
                            else:
                                st.success("사람이 승인한 사례를 하이브리드 불일치 골든셋에 추가했습니다.")
        st.subheader("누적 연구 이력")
        history_feedback = pop_review_feedback(st.session_state, scope="history")
        if history_feedback:
            st.success(history_feedback)
        st.caption(
            "현재 업로드 입력은 재사용하지 않으며 연구 DB에 저장된 문장만 조회합니다."
        )
        history_database = ROOT / "data/research/verification_lab.db"
        try:
            with ExperimentStore(history_database) as history_store:
                history_facets = history_store.get_history_filter_facets()
                history_revision = history_store.get_revision()
        except Exception as error:
            st.error(f"누적 연구 이력 필터를 불러오지 못했습니다: {error}")
            history_facets = {"date_min": None, "date_max": None}
            history_revision = 0

        if history_facets.get("date_min") is None:
            st.info("저장된 연구 실행이 없습니다. 전체 비교 후 ‘연구 이력 저장’을 눌러 주세요.")
        else:
            with st.form("experiment_lab_history_filters"):
                date_column, provider_column, model_column, prompt_column = st.columns(4)
                history_date_range = date_column.date_input(
                    "실행 기간",
                    value=(
                        datetime.fromisoformat(history_facets["date_min"]).date(),
                        datetime.fromisoformat(history_facets["date_max"]).date(),
                    ),
                    key="experiment_lab_history_dates",
                )
                history_provider = provider_column.selectbox(
                    "제공자",
                    ["전체", *history_facets["providers"]],
                    key="experiment_lab_history_provider",
                )
                history_model = model_column.selectbox(
                    "모델",
                    ["전체", *history_facets["models"]],
                    key="experiment_lab_history_model",
                )
                history_prompt = prompt_column.selectbox(
                    "프롬프트",
                    ["전체", *history_facets["prompt_versions"]],
                    key="experiment_lab_history_prompt",
                )
                st.form_submit_button("누적 이력 필터 적용", width="stretch")

            if isinstance(history_date_range, tuple) and len(history_date_range) == 2:
                history_date_from, history_date_to = map(str, history_date_range)
            else:
                history_date_from = history_date_to = str(history_date_range)
            history_filter_values = HistoryFilters(
                date_from=history_date_from,
                date_to=history_date_to,
                provider=None if history_provider == "전체" else history_provider,
                model=None if history_model == "전체" else history_model,
                prompt_version=None if history_prompt == "전체" else history_prompt,
                revision=history_revision,
            )
            history_filters = history_filter_values.as_kwargs()
            history_filter_signature = filter_signature(history_filter_values)
            try:
                with ExperimentStore(history_database) as history_store:
                    exact_history_summary = history_store.get_history_summary(
                        **history_filters
                    )
            except Exception as error:
                st.error(f"누적 연구 이력 집계에 실패했습니다: {error}")
                exact_history_summary = {
                    "run_count": 0,
                    "sentence_count": 0,
                    "counts": {outcome: 0 for outcome in DISAGREEMENT_ORDER},
                }

            st.caption(
                f"필터 결과: 실행 {exact_history_summary['run_count']:,}건 · "
                f"문장 {exact_history_summary['sentence_count']:,}건"
            )
            history_count_columns = st.columns(5)
            for count_column, outcome in zip(history_count_columns, DISAGREEMENT_ORDER):
                count_column.metric(outcome, f"{exact_history_summary['counts'][outcome]:,}건")
            st.caption(
                "누적 화면은 모델·프롬프트 버전이 섞일 수 있어 5유형 건수만 표시합니다. "
                "정밀도·재현율은 선택한 단일 실행의 사람 검토 표본에만 표시합니다."
            )

            prepared_export_key = "experiment_lab_history_prepared_export"
            prepared_export = prepared_export_for_filters(
                st.session_state.get(prepared_export_key), history_filter_values
            )
            if prepared_export is None:
                st.session_state.pop(prepared_export_key, None)
            if st.button(
                "필터 CSV 준비",
                key=f"experiment_lab_history_prepare_csv_{history_filter_signature[:12]}",
            ):
                if exact_history_summary["sentence_count"] > MAX_FILTERED_EXPORT_ROWS:
                    st.error(
                        f"CSV는 최대 {MAX_FILTERED_EXPORT_ROWS:,}문장까지 준비할 수 있습니다. "
                        "필터를 좁혀 주세요."
                    )
                else:
                    try:
                        with ExperimentStore(history_database) as history_store:
                            filtered_export = export_filtered_csv(
                                history_store, history_filters
                            )
                    except Exception as error:
                        st.error(f"필터 CSV 준비 실패: {error}")
                    else:
                        prepared_export = PreparedHistoryExport(
                            signature=history_filter_signature,
                            payload=filtered_export.payload,
                            row_count=filtered_export.row_count,
                        )
                        st.session_state[prepared_export_key] = prepared_export
                        st.success(
                            f"CSV {prepared_export.row_count:,}문장을 준비했습니다."
                        )
            if prepared_export is not None:
                st.download_button(
                    "준비된 필터 CSV 다운로드",
                    data=prepared_export.payload,
                    file_name=(
                        f"verification_lab_history_"
                        f"{history_date_from}_{history_date_to}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key=f"experiment_lab_history_download_{history_filter_signature[:12]}",
                    width="stretch",
                )

            base_page = build_history_page(
                total_runs=exact_history_summary["run_count"],
                requested_page=1,
                page_size=50,
            )
            selected_history_page = st.number_input(
                "이력 페이지 (페이지당 50개 실행)",
                min_value=1,
                max_value=base_page["page_count"],
                value=1,
                step=1,
                key=f"experiment_lab_history_page_{history_filter_signature[:12]}",
            )
            history_page = build_history_page(
                total_runs=exact_history_summary["run_count"],
                requested_page=selected_history_page,
                page_size=50,
            )
            try:
                with ExperimentStore(history_database) as history_store:
                    filtered_history_runs = history_store.list_runs(
                        **history_filters,
                        limit=50,
                        offset=history_page["offset"],
                    )
                    filtered_history_sentences = history_store.get_sentences_for_runs(
                        [run["run_id"] for run in filtered_history_runs]
                    )
            except Exception as error:
                st.error(f"과거 실행 페이지를 불러오지 못했습니다: {error}")
                filtered_history_runs = []
                filtered_history_sentences = []

            st.caption(
                f"{history_page['page']} / {history_page['page_count']}페이지"
            )
            if filtered_history_runs:
                historical_run_by_label = {
                    (
                        f"{run['created_at']} · {run['provider']}/{run['model']} · "
                        f"{run['prompt_version']} · {run['run_id']}"
                    ): run["run_id"]
                    for run in filtered_history_runs
                }
                selected_historical_label = st.selectbox(
                    "과거 실행 선택",
                    list(historical_run_by_label),
                    key=(
                        f"experiment_lab_historical_run_"
                        f"{history_filter_signature[:12]}_{history_page['page']}"
                    ),
                )
                selected_historical_run_id = historical_run_by_label[
                    selected_historical_label
                ]
                selected_historical_run = next(
                    run for run in filtered_history_runs
                    if run["run_id"] == selected_historical_run_id
                )
                selected_historical_sentences = [
                    sentence for sentence in filtered_history_sentences
                    if sentence["run_id"] == selected_historical_run_id
                ]
                historical_evaluation = build_reviewed_evaluation(
                    selected_historical_sentences, selected_historical_run
                )
                if historical_evaluation is not None:
                    st.markdown("###### 선택 실행의 사람 검토 기반 평가")
                    st.caption(
                        f"{historical_evaluation.metric_scope_label} · "
                        f"{historical_evaluation.run_label} · 단일 실행 조건부 지표"
                    )
                    st.dataframe(
                        list(historical_evaluation.rows),
                        width="stretch",
                        hide_index=True,
                    )
                st.dataframe(
                    [
                        {
                            "문장 번호": sentence["sentence_index"],
                            "유형": sentence["disagreement_class"],
                            "문장": sentence["sentence_text"],
                            "HCX 상태": sentence["hcx_status"],
                            "사람 검토": sentence.get("human_label") or "미검토",
                        }
                        for sentence in selected_historical_sentences
                    ],
                    width="stretch",
                    hide_index=True,
                )
                historical_review_rows = reviewable_sentences(
                    selected_historical_sentences
                )
                if historical_review_rows:
                    historical_review_by_label = {
                        f"{row['sentence_index']}. {row['sentence_text'][:90]}": row
                        for row in historical_review_rows
                    }
                    historical_review_label = st.selectbox(
                        "과거 실행 검토 문장",
                        list(historical_review_by_label),
                        key=(
                            f"experiment_lab_history_review_sentence_"
                            f"{selected_historical_run_id}"
                        ),
                    )
                    historical_sentence = historical_review_by_label[
                        historical_review_label
                    ]
                    history_action_target = build_history_action_target(
                        selected_historical_run_id,
                        historical_sentence["sentence_index"],
                    )
                    historical_labels = ["true_candidate", "false_positive", "hold"]
                    historical_current_label = historical_sentence.get("human_label")
                    historical_human_label = st.selectbox(
                        "과거 실행 사람 검토 라벨",
                        historical_labels,
                        index=(
                            historical_labels.index(historical_current_label)
                            if historical_current_label in historical_labels else 2
                        ),
                        format_func=lambda value: {
                            "true_candidate": "실제 검증 후보",
                            "false_positive": "오탐",
                            "hold": "보류",
                        }[value],
                        key=(
                            f"experiment_lab_history_review_label_"
                            f"{history_action_target.run_id}_"
                            f"{history_action_target.sentence_index}"
                        ),
                    )
                    historical_review_note = st.text_area(
                        "과거 실행 검토 메모",
                        value=historical_sentence.get("review_note") or "",
                        key=(
                            f"experiment_lab_history_review_note_"
                            f"{history_action_target.run_id}_"
                            f"{history_action_target.sentence_index}"
                        ),
                    )
                    if st.button(
                        "과거 실행 사람 검토 저장",
                        key=(
                            f"experiment_lab_history_save_review_"
                            f"{history_action_target.run_id}_"
                            f"{history_action_target.sentence_index}"
                        ),
                    ):
                        try:
                            history_review_message = save_human_review(
                                history_database,
                                history_action_target.run_id,
                                history_action_target.sentence_index,
                                human_label=historical_human_label,
                                review_note=historical_review_note,
                                reviewed_at=datetime.now().astimezone().isoformat(
                                    timespec="milliseconds"
                                ),
                            )
                        except Exception as error:
                            st.error(f"과거 실행 사람 검토 저장 실패: {error}")
                        else:
                            store_review_feedback(
                                st.session_state,
                                history_review_message,
                                scope="history",
                            )
                            st.rerun()

                    historical_promotable = historical_sentence.get("human_label") in {
                        "true_candidate", "false_positive"
                    }
                    if st.button(
                        "과거 실행 승인 사례를 골든셋으로 승격",
                        disabled=not historical_promotable,
                        key=(
                            f"experiment_lab_history_promote_"
                            f"{history_action_target.run_id}_"
                            f"{history_action_target.sentence_index}"
                        ),
                    ):
                        try:
                            promote_reviewed_sentence(
                                history_database,
                                history_action_target.run_id,
                                history_action_target.sentence_index,
                                ROOT / "data/goldenset/hybrid_disagreements_v0.jsonl",
                            )
                        except Exception as error:
                            st.error(f"과거 실행 골든셋 승격 실패: {error}")
                        else:
                            st.success("선택한 과거 사례를 골든셋에 추가했습니다.")


    with shadow_lab_tab:
        st.markdown("##### Shadow Mode")
        st.caption("운영 판정을 바꾸지 않고 Python·LLM·Hybrid 비교 결과와 위험 신호를 연구 기록으로 남깁니다.")
        selected_shadow_source = shadow_input_defaults(
            selected_lab_article, fallback_date=str(datetime.now().date())
        )
        if selected_shadow_source is None:
            st.session_state.pop("shadow_lab_source_signature", None)
        else:
            source_signature = (
                f"{selected_shadow_source['title']}\n"
                f"{selected_shadow_source['article_date']}\n"
                f"{selected_shadow_source['text']}"
            )
            if st.session_state.get("shadow_lab_source_signature") != source_signature:
                st.session_state["shadow_lab_text"] = selected_shadow_source["text"]
                try:
                    st.session_state["shadow_lab_date"] = datetime.fromisoformat(
                        selected_shadow_source["article_date"]
                    ).date()
                except ValueError:
                    st.session_state["shadow_lab_date"] = datetime.now().date()
                st.session_state["shadow_lab_source_signature"] = source_signature
                st.session_state.pop("shadow_lab_run_id", None)
            st.caption(
                f"CSV 선택 기사: {selected_shadow_source['title']} · "
                "본문과 발행일을 Shadow 입력에 반영했습니다. 필요하면 수정할 수 있습니다."
            )

        shadow_date = st.date_input("Shadow 기사 발행일", key="shadow_lab_date")
        shadow_text = st.text_area(
            "Shadow 분석 기사 본문",
            key="shadow_lab_text",
            height=180,
            placeholder="예: 2025년 인구는 5,000만 명이다.",
        )
        if st.button("Shadow 실행", type="primary", key="shadow_lab_execute"):
            input_error = validate_shadow_input(shadow_text)
            if input_error:
                st.warning(input_error)
            else:
                try:
                    with ShadowLabService(shadow_database_path(ROOT)) as shadow_service:
                        response = shadow_service.execute(
                            shadow_text,
                            str(shadow_date),
                            ShadowPolicy.default(),
                        )
                    st.session_state["shadow_lab_run_id"] = response["run_id"]
                    st.success("Shadow 실행 결과를 연구 전용 기록으로 저장했습니다.")
                except Exception as error:
                    st.error(f"Shadow 실행을 저장하지 못했습니다: {error}")

        shadow_run_id = st.session_state.get("shadow_lab_run_id")
        if shadow_run_id:
            try:
                with ShadowLabService(shadow_database_path(ROOT)) as shadow_service:
                    shadow_run = shadow_service.get_run(shadow_run_id)
            except Exception as error:
                shadow_run = None
                st.error(f"Shadow 실행 결과를 불러오지 못했습니다: {error}")
            if shadow_run:
                metrics = summary_metrics(shadow_run["summary"])
                execution_status = execution_status_summary(shadow_run)
                metric_columns = st.columns(5)
                metric_columns[0].metric("분석 문장", metrics["row_count"])
                metric_columns[1].metric("검토 필요", metrics["review_count"])
                metric_columns[2].metric("LLM 비교 경로", f"{metrics['llm_calls']}회")
                metric_columns[3].metric(
                    "실제 HCX 응답", f"{execution_status['response_rows']} / {execution_status['total_rows']} 문장"
                )
                metric_columns[4].metric("실행 시간", f"{metrics['elapsed_ms']:,} ms")
                execution_message = f"실행 상태: {execution_status['label']} · {execution_status['detail']}"
                if execution_status["severity"] == "success":
                    st.success(execution_message)
                elif execution_status["severity"] == "warning":
                    st.warning(execution_message)
                else:
                    st.error(execution_message)
                st.dataframe(shadow_result_rows(shadow_run), width="stretch", hide_index=True)

                reviewable_rows = [
                    row for row in shadow_run["rows"]
                    if row["review_state"] == "needs_review"
                ]
                if reviewable_rows:
                    st.markdown("##### Shadow 검토")
                    review_options = {
                        f"#{row['row_index']} · {row['sentence'][:70]}": row
                        for row in reviewable_rows
                    }
                    selected_review_label = st.selectbox(
                        "검토할 문장", list(review_options), key=f"shadow_review_row_{shadow_run_id}"
                    )
                    selected_review_row = review_options[selected_review_label]
                    review_action = st.selectbox(
                        "검토 결정", ("approve", "correct", "hold"),
                        format_func=lambda action: {"approve": "승인", "correct": "보정", "hold": "보류"}[action],
                        key=f"shadow_review_action_{shadow_run_id}",
                    )
                    review_note = st.text_area(
                        "검토 메모", key=f"shadow_review_note_{shadow_run_id}",
                        placeholder="예: 시간 기준 또는 단위 확인 필요",
                    )
                    if st.button("Shadow 검토 저장", key=f"shadow_review_save_{shadow_run_id}"):
                        try:
                            with ShadowLabService(shadow_database_path(ROOT)) as shadow_service:
                                shadow_service.review(
                                    shadow_run_id, selected_review_row["row_index"],
                                    action=review_action, note=review_note,
                                    reviewed_at=datetime.now().astimezone().isoformat(),
                                )
                            st.success("Shadow 검토 이력을 연구 전용 저장소에 기록했습니다.")
                            st.rerun()
                        except Exception as error:
                            st.error(f"Shadow 검토를 저장하지 못했습니다: {error}")

                st.markdown("##### 실행 기록 다운로드")
                json_name, csv_name = download_filenames(shadow_run["run_id"])
                download_columns = st.columns(2)
                download_columns[0].download_button(
                    "JSON 다운로드", data=export_shadow_run_json(shadow_run),
                    file_name=json_name, mime="application/json", key=f"shadow_json_{shadow_run_id}",
                    use_container_width=True,
                )
                download_columns[1].download_button(
                    "CSV 다운로드", data=export_shadow_run_csv(shadow_run),
                    file_name=csv_name, mime="text/csv; charset=utf-8", key=f"shadow_csv_{shadow_run_id}",
                    use_container_width=True,
                )

                st.markdown("##### 과거 Shadow 실행 비교")
                with ShadowLabService(shadow_database_path(ROOT)) as shadow_service:
                    history_runs = shadow_service.list_runs(limit=20)
                history_options = {
                    f"{run['created_at']} · {run['run_id'][:12]}": run["run_id"]
                    for run in history_runs
                }
                selected_history_labels = st.multiselect(
                    "비교할 실행 선택 (최대 5개)", list(history_options), max_selections=5,
                    key="shadow_history_selected_runs",
                )
                if selected_history_labels:
                    comparison_rows = []
                    with ShadowLabService(shadow_database_path(ROOT)) as shadow_service:
                        for label in selected_history_labels:
                            history_run = shadow_service.get_run(history_options[label])
                            if history_run is None:
                                continue
                            history_metrics = summary_metrics(history_run["summary"])
                            history_status = execution_status_summary(history_run)
                            comparison_rows.append({
                                "실행 시각": history_run["created_at"],
                                "실행 ID": history_run["run_id"],
                                "정책": history_run["policy"].get("version", "-"),
                                "분석 문장": history_metrics["row_count"],
                                "검토 필요": history_metrics["review_count"],
                                "LLM 비교 경로": history_metrics["llm_calls"],
                                "실제 HCX 응답": f"{history_status['response_rows']} / {history_status['total_rows']}",
                                "HCX 상태": history_status["label"],
                                "불일치 유형": " | ".join(f"{key}: {value}" for key, value in history_run["summary"].get("disagreement_counts", {}).items()) or "-",
                            })
                    st.dataframe(comparison_rows, width="stretch", hide_index=True)
# ═════════════ 탭 2: 검증자 리뷰 (WF-2) ═════════════
if view == "검증자 리뷰":
    persisted_store = Store(ROOT / "data/service/clafact.db")
    try:
        persisted_queue = persisted_store.review_queue()
    finally:
        persisted_store.close()
    review_feedback = st.session_state.pop("review_feedback", "")
    if review_feedback:
        st.success(review_feedback)
    if persisted_queue:
        st.markdown("#### 저장된 검증자 리뷰 큐")
        for row in persisted_queue:
            with st.expander(f"{row['label'] or '판정 확인'} · {row['sentence'][:64]}"):
                st.write(row["sentence"])
                st.caption(row["reason"] or "자동 판정 근거 확인 필요")
                if row["source_type"] == "OFFICIAL_ANNOUNCEMENT":
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
                            st.error(response.json().get("detail", "공식 공지 등록에 실패했습니다."))
                approve, hold = st.columns(2)
                if approve.button("자동 판정 승인", key=f"approve_{row['claim_id']}"):
                    review_store = Store(ROOT / "data/service/clafact.db")
                    try:
                        review_store.apply_review(row["claim_id"], "approve")
                        st.session_state["review_feedback"] = "자동 판정을 승인했습니다."
                    finally:
                        review_store.close()
                    st.rerun()
                if hold.button("판단 보류", key=f"hold_{row['claim_id']}"):
                    hold_store = Store(ROOT / "data/service/clafact.db")
                    try:
                        hold_store.apply_review(row["claim_id"], "hold", note="공식 근거 확인 필요")
                        st.session_state["review_feedback"] = "판정을 보류했습니다."
                    finally:
                        hold_store.close()
                    st.rerun()
    results = st.session_state.get("results", [])
    reviews = st.session_state.setdefault("reviews", {})
    if not results:
        if not persisted_queue:
            if review_feedback:
                st.info("현재 검증자 리뷰 대기 항목이 없습니다.")
            else:
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
