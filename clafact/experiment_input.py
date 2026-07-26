"""검증 실험실에 전달할 업로드 원문을 경계 안에서 정제한다."""
from __future__ import annotations

from clafact.pipeline.ingest import clean_body, strip_site_chrome


ARTICLE_END_MARKERS = (
    "관련 기사",
    "기자 프로필",
    "기자 약력",
    "구독",
)


def clean_uploaded_article_body(raw_body: str) -> str:
    """업로드 행의 기사 본문만 반환하며 부속 기사·프로필은 포함하지 않는다."""
    body, _anchored = strip_site_chrome(raw_body)
    boundary = min(
        (position for marker in ARTICLE_END_MARKERS if (position := body.find(marker)) >= 0),
        default=-1,
    )
    if boundary >= 0:
        body = body[:boundary]
    return clean_body(body)
