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
RE_REPORTER_TAIL = re.compile(r"\s+[가-힣]{2,4}\s*기자$")
RE_COPYRIGHT = re.compile(r"무단\s*전재|재배포\s*금지|저작권자|ⓒ|©|Copyright", re.I)
RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
RE_MULTISPACE = re.compile(r"[ \t ]+")

# 실물 데이터셋(2026-07 수령)은 크롤된 페이지 전체가 본문 컬럼에 담겨 있어
# 사이트 크롬(메뉴·헤더·크롤시점 날짜)이 기사 앞에 붙는다. 실제 본문은
# "입력 YYYY.MM.DD. HH:MM" 타임스탬프 뒤부터 시작한다 (표본 30건 중 29건 커버 실측).
RE_BYLINE_ANCHOR = re.compile(r"입력\s*20\d{2}\.\d{2}\.\d{2}\.?\s*\d{2}:\d{2}")
RE_UPDATE_STAMP = re.compile(r"^\s*업데이트\s*20\d{2}\.\d{2}\.\d{2}\.?\s*\d{2}:\d{2}\s*\d*\s*")
RE_CHOSUN_SECTION = re.compile(r"https?://www\.chosun\.com/([a-z_-]+)/")

# 페이지 푸터 절단 마커 — 기사 본문에 사실상 등장하지 않는 고정밀 문구만.
# 크롤 본문은 개행이 없는 한 줄이라, clean_body의 라인 단위 필터로는 푸터를
# 제거할 수 없고(기사 전체가 한 줄로 삭제되는 사고 — 실측으로 발견) 위치 절단이 필요하다.
FOOTER_MARKERS = (
    # 본문 종료 직후 순서: 기자 프로필(구독수 N) → 100자평(독자 댓글!) → AI 추천/멤버십
    # → Taboola 광고 → 사이트 푸터. 가장 먼저 등장하는 마커에서 절단한다.
    # 댓글이 본문으로 새면 독자 주장 수치가 검증 대상으로 오탐된다 (실측으로 발견).
    "구독수 ", "100자평", "AI 추천 오늘의 멤버십", "By Taboola", "당신이 좋아할 만한 콘텐츠",
    "무단 전재 및 재배포 금지", "Copyright 조선일보", "인터넷신문등록번호",
    "등록(발행)일자:", "청소년보호정책(책임자", "회사소개 기자채용 고객센터",
    "많이 본 뉴스", "당신이 관심있을 만한",
)

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


def strip_site_chrome(body: str) -> tuple[str, bool]:
    """크롤 페이지에서 사이트 크롬 제거 — 바이라인 앵커 뒤가 본문.

    반환: (본문, 앵커 발견 여부). 앵커가 없으면 원문 그대로 반환하며,
    호출 측은 anchor=False 기사를 수동 확인 대상으로 기록한다.
    """
    text = body or ""
    m = RE_BYLINE_ANCHOR.search(text)
    anchored = bool(m)
    if m:
        text = RE_UPDATE_STAMP.sub("", text[m.end():])
    # 푸터 절단: 마커 중 가장 먼저 등장하는 지점에서 자른다
    cut = min((i for i in (text.find(mk) for mk in FOOTER_MARKERS) if i >= 0), default=-1)
    if cut >= 0:
        text = text[:cut]
    return text.strip(), anchored


def section_from_url(url: str) -> str:
    """조선일보 URL 경로에서 섹션 유도 (섹션 컬럼이 없는 실물 데이터 대응)."""
    m = RE_CHOSUN_SECTION.match(url or "")
    return m.group(1) if m else ""


def clean_body(body: str) -> str:
    """비본문 요소 제거 + 공백 정규화."""
    lines = []
    for line in body.splitlines():
        # 이메일을 먼저 제거해야 "홍길동 기자 x@y.com" 줄이 기자명 패턴에 걸린다
        s = RE_REPORTER_TAIL.sub("", RE_EMAIL.sub("", line).strip()).strip()
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
        raw_body, _anchored = strip_site_chrome(_pick(row, "body"))
        body = clean_body(raw_body)
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
            section=_pick(row, "section") or section_from_url(url),
            url=url,
            body=body,
            label=_pick(row, "label"),
            sentences=split_sentences(body),
        ))
    return articles
