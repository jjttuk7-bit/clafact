"""Fetch only official KOSIS source-page definition candidates for human review."""
from __future__ import annotations

import html
import re
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class KosisDefinitionCandidate:
    text: str
    source_url: str
    method: str


def validate_kosis_source_url(source_url: str) -> str:
    parsed = urlparse(source_url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not (host == "kosis.kr" or host.endswith(".kosis.kr")):
        raise ValueError("source URL must use https://kosis.kr")
    return source_url


def _clean_text(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def extract_definition_candidate(
    source_html: str, *, source_url: str
) -> KosisDefinitionCandidate | None:
    """Extract an explicit page description; never infer a statistical definition."""
    validate_kosis_source_url(source_url)
    meta_match = re.search(
        r"<meta\s+(?:name|property)=[\"'](?:description|og:description)[\"']\s+content=[\"']([^\"']+)[\"']",
        source_html,
        flags=re.IGNORECASE,
    )
    if not meta_match:
        meta_match = re.search(
            r"<meta\s+content=[\"']([^\"']+)[\"']\s+(?:name|property)=[\"'](?:description|og:description)[\"']",
            source_html,
            flags=re.IGNORECASE,
        )
    if not meta_match:
        return None
    text = _clean_text(meta_match.group(1))
    if not text:
        return None
    return KosisDefinitionCandidate(text=text, source_url=source_url, method="meta_description")


def fetch_definition_candidate(source_url: str, *, timeout: int = 10) -> KosisDefinitionCandidate | None:
    """Read an official KOSIS source page and return only its explicit description."""
    validate_kosis_source_url(source_url)
    request = urllib.request.Request(source_url, headers={"User-Agent": "ClaFact research evidence"})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        source_html = response.read().decode("utf-8", errors="replace")
    return extract_definition_candidate(source_html, source_url=source_url)