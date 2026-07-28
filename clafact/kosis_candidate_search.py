"""Explainable KOSIS table candidate ranking for Shadow research."""
from __future__ import annotations

from dataclasses import dataclass

from clafact.pipeline.retrieve import TableHit


@dataclass(frozen=True)
class KosisCandidate:
    """A search hit with transparent applicability signals."""

    hit: TableHit
    score: int
    reasons: tuple[str, ...]
    penalties: tuple[str, ...]
    selected_item: str = ""
    score_breakdown: tuple[str, ...] = ()
    max_score: int = 0

    @property
    def fit_score(self) -> int:
        """Return the candidate suitability normalized to a 100-point scale."""
        if self.max_score <= 0:
            return 0
        return max(0, min(100, round(self.score / self.max_score * 100)))


def _compact(text: str) -> str:
    return "".join(text.lower().split())


def evaluate_kosis_candidate(sentence: str, hit: TableHit, *, item_names: tuple[str, ...] = ()) -> KosisCandidate:
    """Score a candidate table from title signals only; never assert factual truth."""
    claim = _compact(sentence)
    title = _compact(hit.tbl_name)
    score = 0
    reasons: list[str] = []
    penalties: list[str] = []
    score_breakdown: list[str] = []
    max_score = 0

    if "소비자물가" in claim:
        max_score += 50
    if "소비자물가" in claim and "소비자물가" in title:
        score += 50
        reasons.append("지표 일치")
        score_breakdown.append("+50 지표 일치")

    expects_month = "지난달" in claim or "이번달" in claim or "전년동월" in claim
    monthly_title = any(token in title for token in ("월별", "월간", "전년동월비", "전월비"))
    if expects_month:
        max_score += 20
    if expects_month and monthly_title:
        score += 20
        reasons.append("월 단위 일치")
        score_breakdown.append("+20 월 단위 일치")
    elif expects_month:
        penalties.append("월 단위 표현 없음")

    expects_rate = "%" in sentence or "퍼센트" in sentence
    rate_title = any(token in title for token in ("등락률", "증감률", "상승률", "전년동월비", "전월비"))
    if expects_rate:
        max_score += 20
    if expects_rate and rate_title:
        score += 20
        reasons.append("등락률/증감률 단위 일치")
        score_breakdown.append("+20 등락률/증감률 단위 일치")
    elif expects_rate:
        penalties.append("등락률/증감률 표현 없음")

    expects_year_over_year = any(token in claim for token in ("지난해같은달", "전년동월", "전년동월비"))
    if expects_year_over_year:
        max_score += 30
    if expects_year_over_year and "전년동월비" in title:
        score += 10
        reasons.append("전년동월비 일치")
        score_breakdown.append("+10 전년동월비 일치")
    elif expects_year_over_year:
        penalties.append("전년동월비 표현 없음")

    selected_item = next((item for item in item_names if "전년" in item), "")
    official_items = " ".join(item_names)
    if expects_year_over_year and "전월비" in official_items and "전년" not in official_items:
        deduction = min(40, score)
        score -= deduction
        penalties.append("공식 항목 전월비 불일치")
        score_breakdown.append(f"-{deduction} 공식 항목 전월비 불일치")
    elif expects_year_over_year and ("전년비" in official_items or "전년동월비" in official_items):
        score += 20
        reasons.append("공식 항목 전년동월비 일치")
        score_breakdown.append("+20 공식 항목 전년동월비 일치")
    return KosisCandidate(
        hit=hit,
        score=score,
        reasons=tuple(reasons),
        penalties=tuple(penalties),
        selected_item=selected_item,
        score_breakdown=tuple(score_breakdown),
        max_score=max_score,
    )


def suggest_kosis_candidates(sentence: str, search_index: object, *, top_k: int = 3, metadata_client: object | None = None) -> list[KosisCandidate]:
    """Search and return the best explainable table candidates for one sentence."""
    query = "소비자물가" if "소비자물가" in _compact(sentence) else sentence
    hits = search_index.search(query, top_k=10)
    candidates = []
    for hit in hits:
        item_names: tuple[str, ...] = ()
        if metadata_client is not None:
            try:
                rows = metadata_client.fetch_data(hit.org_id, hit.tbl_id, recent_n=1)
                item_names = tuple(dict.fromkeys(str(row.get("ITM_NM", "")) for row in rows if row.get("ITM_NM")))
            except Exception:
                pass
        candidates.append(evaluate_kosis_candidate(sentence, hit, item_names=item_names))
    return sorted(candidates, key=lambda candidate: -candidate.score)[:top_k]