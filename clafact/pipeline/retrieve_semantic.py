"""경로 B — 의미 기반 검색 프로토타입 (문서 12 §4 확률적 계획, EXP-001).

Embedder 인터페이스로 임베딩 백엔드를 추상화한다:
  - CharNgramEmbedder: 지금 (순수 파이썬 문자 n-gram TF-IDF, 외부 의존성 0)
  - HcxEmbedder:       나중 (제공 임베딩 모델 — 인터페이스만 교체하면 됨)

⚠️ 문자 n-gram 은 '진짜 임베딩'의 프록시일 뿐이다. 글자가 겹치지 않는 동의어
   ('출생아' vs '새로 태어난 아기')는 못 잡는다 — 이 한계를 실험으로 측정해
   "왜 진짜 의미 임베딩(HCX)이 필요한가"를 데이터로 입증하는 것이 EXP-001의 목적.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Protocol

RE_KO = re.compile(r"[가-힣A-Za-z0-9]+")


def char_ngrams(text: str, lo: int = 2, hi: int = 3) -> list[str]:
    """공백·조사 무시 후 단어별 문자 n-gram (한글 형태 유사도 포착)."""
    grams = []
    for w in RE_KO.findall(text):
        grams.append(w)  # 단어 원형도 토큰
        for n in range(lo, hi + 1):
            for i in range(len(w) - n + 1):
                grams.append(w[i:i + n])
    return grams


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[dict[str, float]]:
        """텍스트 → 벡터(희소 dict). HCX 는 밀집 벡터를 반환하지만
        cosine 인터페이스는 동일하게 맞춘다."""
        ...


class CharNgramEmbedder:
    """문자 n-gram TF-IDF (코퍼스에 fit 후 transform)."""

    def __init__(self):
        self.idf: dict[str, float] = {}
        self._fitted = False

    def fit(self, corpus: list[str]) -> "CharNgramEmbedder":
        n = len(corpus)
        df: Counter = Counter()
        for doc in corpus:
            for g in set(char_ngrams(doc)):
                df[g] += 1
        self.idf = {g: math.log((n + 1) / (c + 1)) + 1 for g, c in df.items()}
        self._fitted = True
        return self

    def embed(self, texts: list[str]) -> list[dict[str, float]]:
        out = []
        for t in texts:
            tf = Counter(char_ngrams(t))
            vec = {g: c * self.idf.get(g, 0.0) for g, c in tf.items() if self.idf.get(g)}
            out.append(vec)
        return out


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[k] * b[k] for k in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


class SemanticIndex:
    """경로 B: 통계표 메타를 임베딩해두고 질의를 의미 유사도로 검색."""

    def __init__(self, tables: list[dict], embedder: Embedder | None = None, aliases=None):
        self.tables = tables
        self.aliases = aliases  # 하이브리드용 (경로 A+B): 질의 별칭 치환
        docs = [f"{t['TBL_NM']} {t['SURVEY']} {t.get('KEYWORDS','')}" for t in tables]
        self.embedder = embedder or CharNgramEmbedder()
        if hasattr(self.embedder, "fit"):
            self.embedder.fit(docs + [t.get("KEYWORDS", "") for t in tables])
        self.doc_vecs = self.embedder.embed(docs)

    def search(self, query: str, top_k: int = 3, use_alias: bool = False):
        q = self.aliases.substitute(query) if (use_alias and self.aliases) else query
        qv = self.embedder.embed([q])[0]
        scored = [(t["TBL_ID"], cosine(qv, dv)) for t, dv in zip(self.tables, self.doc_vecs)]
        scored = [(tid, s) for tid, s in scored if s > 0]
        return sorted(scored, key=lambda x: -x[1])[:top_k]
