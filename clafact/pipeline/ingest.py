"""Ingest — 기사 데이터셋 로더·전처리·문장 분리 (FR-01).

클라비 제공 데이터셋 스키마(노션 공개): 기사 제목, 작성일, (섹션), URL, 기사 본문 전체, 검색 구분 레이블.
실물 파일이 오기 전에 스키마 기준으로 구현 — 파일 도착 시 컬럼명 매핑만 조정.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

# 실물 파일의 컬럼명이 다를 수 있어 별칭으로 흡수한다
FIELD_ALIASES = {
    "title": ["title", "제목", "기사 제목", "기사제목"],
    "date": ["date", "작성일", "게시일", "published_at"],
    "section": ["section", "섹션", "(섹션)"],
    "url": ["url", "URL", "링크"],
    "body": ["body", "본문", "기사 본문 전체", "기사본문", "content", "text"],
    "label": ["label", "레이블", "검색 구분 레이블", "검색구분"],
}

# 비본문 요소 제거 패턴 (문서 04 §1.3 전처리 규칙)
RE_REPORTER = re.compile(r"^[가-힣]{2,4}\s*기자\s*(=|$)|[가-힣]{2,4}\s*기자입니다\.?$")
RE_COPYRIGHT = re.compile(r"무단\s*전재|재배포\s*금지|저작권자|ⓒ|©|Copyright", re.I)
RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
RE_MULTISPACE = re.compile(r"[ \t ]+")

# 한국어 문장 분리 (v1: 규칙 기반 — kss 도입 전까지)
# 종결어미+마침표/물음표/느낌표 뒤 공백에서 분리. 소수점(7.2%)과 숫자 나열은 보호.
RE_SENT_SPLIT = re.compile(r"(?<=[다요임음됨함까죠네]\.)\s+|(?<=[?!])\s+")


@dataclass
class Article:
    article_id: str
    title: str = ""
    date: str = ""
    section: str = ""
    url: str = ""
    body: str = ""
    label: str = ""
    sentences: list[str] = field(default_factory=list)


def _pick(row: dict, key: str) -> str:
    for alias in FIELD_ALIASES[key]:
        if alias in row and row[alias] is not None:
            return str(row[alias]).strip()
    return ""


def clean_body(body: str) -> str:
    """비본문 요소 제거 + 공백 정규화."""
    lines = []
    for line in body.splitlines():
        # 이메일을 먼저 제거해야 "홍길동 기자 x@y.com" 줄이 기자명 패턴에 걸린다
        s = RE_EMAIL.sub("", line).strip()
        if not s or RE_COPYRIGHT.search(s) or RE_REPORTER.search(s):
            continue
        lines.append(s)
    return RE_MULTISPACE.sub(" ", " ".join(lines)).strip()


def split_sentences(text: str) -> list[str]:
    """규칙 기반 문장 분리. 문장 ID는 리스트 인덱스."""
    return [s.strip() for s in RE_SENT_SPLIT.split(text) if s.strip()]


def load_articles(path: str | Path) -> list[Article]:
    """JSONL 또는 CSV 데이터셋 로딩 → 정제·문장 분리까지 수행.

    중복 URL 제거, 본문 없는 레코드 제외 (문서 04 §1.3).
    """
    path = Path(path)
    rows: list[dict] = []
    if path.suffix == ".jsonl":
        with path.open(encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]
    elif path.suffix == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
    else:
        raise ValueError(f"지원하지 않는 형식: {path.suffix} (jsonl/csv)")

    articles: list[Article] = []
    seen_urls: set[str] = set()
    for i, row in enumerate(rows):
        body = clean_body(_pick(row, "body"))
        url = _pick(row, "url")
        if not body:
            continue  # 본문 없음 → 제외 + (운영 시 로그)
        if url and url in seen_urls:
            continue  # 중복 URL 제거
        seen_urls.add(url)
        articles.append(Article(
            article_id=f"A{i + 1:05d}",
            title=_pick(row, "title"),
            date=_pick(row, "date"),
            section=_pick(row, "section"),
            url=url,
            body=body,
            label=_pick(row, "label"),
            sentences=split_sentences(body),
        ))
    return articles
