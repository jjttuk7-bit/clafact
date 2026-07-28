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


def _compact(text: str) -> str:
    return "".join(text.lower().split())


def evaluate_kosis_candidate(sentence: str, hit: TableHit) -> KosisCandidate:
    """Score a candidate table from title signals only; never assert factual truth."""
    claim = _compact(sentence)
    title = _compact(hit.tbl_name)
    score = 0
    reasons: list[str] = []
    penalties: list[str] = []

    if "소비자물가" in claim and "소비자물가" in title:
        score += 50
        reasons.append("지표 일치")

    expects_month = "지난달" in claim or "이번달" in claim or "전년동월" in claim
    monthly_title = any(token in title for token in ("월별", "월간", "전년동월비", "전월비"))
    if expects_month and monthly_title:
        score += 20
        reasons.append("월 단위 일치")
    elif expects_month:
        penalties.append("월 단위 표현 없음")

    expects_rate = "%" in sentence or "퍼센트" in sentence
    rate_title = any(token in title for token in ("등락률", "증감률", "상승률", "전년동월비", "전월비"))
    if expects_rate and rate_title:
        score += 20
        reasons.append("등락률/증감률 단위 일치")
    elif expects_rate:
        penalties.append("등락률/증감률 표현 없음")

    expects_year_over_year = any(token in claim for token in ("지난해같은달", "전년동월", "전년동월비"))
    if expects_year_over_year and "전년동월비" in title:
        score += 10
        reasons.append("전년동월비 일치")
    elif expects_year_over_year:
        penalties.append("전년동월비 표현 없음")

    return KosisCandidate(hit, score, tuple(reasons), tuple(penalties))


def suggest_kosis_candidates(sentence: str, search_index: object, *, top_k: int = 3) -> list[KosisCandidate]:
    """Search and return the best explainable table candidates for one sentence."""
    query = "소비자물가" if "소비자물가" in _compact(sentence) else sentence
    hits = search_index.search(query, top_k=10)
    candidates = [evaluate_kosis_candidate(sentence, hit) for hit in hits]
    return sorted(candidates, key=lambda candidate: -candidate.score)[:top_k]
