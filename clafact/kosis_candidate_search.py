"""Explainable KOSIS table candidate ranking for Shadow research."""
from __future__ import annotations

from dataclasses import dataclass

from clafact.claim_profile import ClaimProfile, build_claim_profile
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


def _title_matches_period(title: str, period: str) -> bool:
    tokens = {
        "월": ("월별", "월간", "전년동월비", "전월비"),
        "분기": ("분기",),
        "연": ("연도별", "연간", "연별", "년간"),
    }
    return any(token in title for token in tokens.get(period, ()))


def _title_matches_rate(title: str) -> bool:
    return any(token in title for token in ("등락률", "증감률", "상승률", "전년동월비", "전월비", "률"))


def _title_matches_comparison(title: str, comparison: str) -> bool:
    if comparison == "전년동월비":
        return "전년동월비" in title or "전년비" in title
    if comparison == "전월비":
        return "전월비" in title
    if comparison == "전년 대비":
        return "전년" in title
    return False


def _official_item_score(item: str, profile: ClaimProfile) -> int:
    """Rank a table item by canonical indicator, comparison, and unit signals."""
    compact_item = _compact(item)
    score = 0
    if profile.indicator and _compact(profile.indicator) in compact_item:
        score += 100
    if profile.comparison and _title_matches_comparison(compact_item, profile.comparison):
        score += 10
    if profile.unit in ("%", "%p") and "%" in item:
        score += 2
    return score


def _select_official_item(item_names: tuple[str, ...], profile: ClaimProfile) -> str:
    if not item_names:
        return ""
    return max(item_names, key=lambda item: _official_item_score(item, profile))


def _is_trade_item_conflict(item: str, profile: ClaimProfile) -> bool:
    compact_item = _compact(item)
    return (
        profile.indicator == "수출액" and "수출물량" in compact_item
    ) or (
        profile.indicator == "수입액" and "수입물량" in compact_item
    )


def evaluate_kosis_candidate(
    sentence: str,
    hit: TableHit,
    *,
    item_names: tuple[str, ...] = (),
    profile: ClaimProfile | None = None,
) -> KosisCandidate:
    """Score one candidate from an explainable numeric-claim profile."""
    profile = profile or build_claim_profile(sentence)
    title = _compact(hit.tbl_name)
    score = 0
    max_score = 0
    reasons: list[str] = []
    penalties: list[str] = []
    score_breakdown: list[str] = []

    if profile.indicator:
        max_score += 50
        if _compact(profile.indicator) in title:
            score += 50
            reasons.append("지표 일치")
            score_breakdown.append("+50 지표 일치")
        else:
            penalties.append("지표명 직접 일치 없음")

    if profile.period:
        max_score += 20
        if _title_matches_period(title, profile.period):
            score += 20
            reasons.append(f"{profile.period} 단위 일치")
            score_breakdown.append(f"+20 {profile.period} 단위 일치")
        else:
            penalties.append(f"{profile.period} 단위 표현 없음")

    expects_rate = profile.unit in ("%", "%p")
    if expects_rate:
        max_score += 20
        if _title_matches_rate(title):
            score += 20
            reasons.append("등락률/증감률 단위 일치")
            score_breakdown.append("+20 등락률/증감률 단위 일치")
        else:
            penalties.append("등락률/증감률 표현 없음")

    if profile.comparison:
        max_score += 10
        if _title_matches_comparison(title, profile.comparison):
            score += 10
            reasons.append(f"{profile.comparison} 일치")
            score_breakdown.append(f"+10 {profile.comparison} 일치")
        else:
            penalties.append(f"{profile.comparison} 표현 없음")

    selected_item = _select_official_item(item_names, profile)
    official_items = " ".join(item_names)
    if selected_item and profile.indicator and _compact(profile.indicator) in _compact(selected_item):
        max_score += 20
        score += 20
        reasons.append(f"공식 항목 {profile.indicator} 일치")
        score_breakdown.append(f"+20 공식 항목 {profile.indicator} 일치")
    elif selected_item and _is_trade_item_conflict(selected_item, profile):
        penalties.append(f"공식 항목 {selected_item} 의미 충돌")

    if profile.comparison == "전년동월비":
        max_score += 20
        if "전월비" in official_items and "전년" not in official_items:
            deduction = min(40, score)
            score -= deduction
            penalties.append("공식 항목 전월비 불일치")
            score_breakdown.append(f"-{deduction} 공식 항목 전월비 불일치")
        elif "전년비" in official_items or "전년동월비" in official_items:
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


def suggest_kosis_candidates(
    sentence: str,
    search_index: object,
    *,
    top_k: int = 3,
    metadata_client: object | None = None,
    previous_profile: ClaimProfile | None = None,
    metadata_limit: int = 3,
) -> list[KosisCandidate]:
    """Search supported KOSIS candidates using a structured numeric claim profile."""
    profile = build_claim_profile(sentence, previous=previous_profile)
    if not profile.search_query:
        return []
    hits = search_index.search(profile.search_query, top_k=10)
    candidates = []
    for hit_index, hit in enumerate(hits):
        item_names: tuple[str, ...] = ()
        if metadata_client is not None and hit_index < metadata_limit:
            try:
                rows = metadata_client.fetch_data(hit.org_id, hit.tbl_id, recent_n=1)
                item_names = tuple(dict.fromkeys(str(row.get("ITM_NM", "")) for row in rows if row.get("ITM_NM")))
            except Exception:
                pass
        candidates.append(evaluate_kosis_candidate(sentence, hit, item_names=item_names, profile=profile))
    return sorted(candidates, key=lambda candidate: -candidate.score)[:top_k]