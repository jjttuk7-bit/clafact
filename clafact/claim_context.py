"""Safe article-level context helpers for Claim Card review."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping

from clafact.pipeline.parse import extract_quantities, normalize_period


_STRONG_PERIOD = re.compile(r"\d{4}년\s*\d{1,2}월|지난\s*달|이번\s*달")


@dataclass(frozen=True)
class ArticlePeriodContext:
    period: str = ""
    row_index: int | None = None


def resolve_article_period(sentences: list[str], article_date: str) -> ArticlePeriodContext:
    """Return one article observation period only when strong cues agree."""
    candidates: list[tuple[str, int]] = []
    for position, sentence in enumerate(sentences, start=1):
        if not _STRONG_PERIOD.search(sentence):
            continue
        period = normalize_period(sentence, article_date)
        if period:
            candidates.append((period, position))
    unique_periods = {period for period, _ in candidates}
    if len(unique_periods) != 1:
        return ArticlePeriodContext()
    period = candidates[0][0]
    return ArticlePeriodContext(period=period, row_index=candidates[0][1])


def shadow_sentence_label(row: Mapping[str, object]) -> str:
    """Keep a Shadow sentence selector readable without changing its source text."""
    sentence = str(row["sentence"])
    row_index = int(row["row_index"])
    quantities = extract_quantities(sentence)
    if len(quantities) > 1:
        preview = sentence[:32].rstrip(" ,")
        return f"#{row_index} · 복수 수치 {len(quantities)}개 · {preview} …"
    return f"#{row_index} · {sentence[:70]}"
