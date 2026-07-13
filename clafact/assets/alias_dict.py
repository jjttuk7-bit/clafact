"""A1. 별칭 사전 — 기사 표현 ↔ KOSIS 통계 정식명 매핑.

축적 루틴(문서 11): 매핑 실패 리뷰 시 그 자리에서 add() 호출.
검색 전 substitute() 로 질의를 정규화해 즉시 효과를 낸다.
"""
from __future__ import annotations

import json
import time
from pathlib import Path


class AliasDict:
    def __init__(self, path: str | Path = "data/assets/aliases.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: list[dict] = []
        if self.path.exists():
            with self.path.open(encoding="utf-8") as f:
                self._entries = [json.loads(line) for line in f if line.strip()]

    def __len__(self) -> int:
        return len(self._entries)

    def add(
        self,
        alias: str,
        canonical: str,
        tbl_id: str = "",
        item_path: str = "",
        origin: str = "manual",  # 실패 유래면 fail_id 를 넣는다
    ) -> str:
        """엔트리 추가. entry_id 반환 (실패 resolve 시 derived_assets 로 사용)."""
        entry_id = f"A1-{len(self._entries) + 1:04d}"
        entry = {
            "entry_id": entry_id,
            "alias": alias,
            "canonical": canonical,
            "tbl_id": tbl_id,
            "item_path": item_path,
            "origin": origin,
            "created": time.strftime("%Y-%m-%d"),
            "verified_count": 0,
        }
        self._entries.append(entry)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry_id

    def lookup(self, text: str) -> list[dict]:
        """텍스트에 등장하는 별칭 엔트리 반환 (긴 별칭 우선)."""
        hits = [e for e in self._entries if e["alias"] in text]
        return sorted(hits, key=lambda e: -len(e["alias"]))

    def substitute(self, text: str) -> str:
        """검색 질의용: 별칭을 정식명으로 치환."""
        for e in self.lookup(text):
            text = text.replace(e["alias"], e["canonical"])
        return text

    def stats(self) -> dict:
        from_failure = sum(1 for e in self._entries if e["origin"].startswith("F"))
        return {"total": len(self._entries), "from_failure": from_failure}
