"""KOSIS 통계목록 트리를 안전하게 나눠 수집하는 도구."""
from __future__ import annotations

import json
import time
from pathlib import Path
from collections import deque
from collections.abc import Iterable

from clafact.assets.alias_dict import AliasDict
from clafact.kosis import KosisConnectionError
from clafact.pipeline.retrieve import TableHit, _tokens


def crawl_catalog(client, view_code: str, parent_ids: Iterable[str], *, max_list_calls: int,
                  seen_parent_ids: Iterable[str] = ()) -> dict:
    """제한된 목록 호출로 표 메타를 모으고, 남은 목록 ID를 반환한다.

    반환된 ``pending_parent_ids``를 다음 실행에 넘기면 중단 지점부터 재개한다.
    """
    if max_list_calls < 1:
        raise ValueError("max_list_calls must be at least 1")
    seen = {str(parent_id) for parent_id in seen_parent_ids}
    queue = deque(parent_id for parent_id in dict.fromkeys(str(parent_id) for parent_id in parent_ids)
                  if parent_id not in seen)
    tables, visited = [], []
    seen_tables = set()
    calls = 0
    while queue and calls < max_list_calls:
        parent_id = queue.popleft()
        try:
            rows = client.fetch_statistics_list(view_code, parent_id)
        except KosisConnectionError as error:
            queue.appendleft(parent_id)
            return {
                "tables": tables,
                "pending_parent_ids": list(queue),
                "visited_parent_ids": visited,
                "list_calls": calls,
                "connection_error": str(error),
            }
        calls += 1
        visited.append(parent_id)
        for row in rows:
            table_id = str(row.get("TBL_ID", "")).strip()
            if table_id:
                if table_id not in seen_tables:
                    tables.append(row)
                    seen_tables.add(table_id)
                continue
            child_id = str(row.get("LIST_ID", "")).strip()
            if child_id and child_id not in seen and child_id not in visited and child_id not in queue:
                queue.append(child_id)
    return {
        "tables": tables,
        "pending_parent_ids": list(queue),
        "visited_parent_ids": visited,
        "list_calls": calls,
        "connection_error": "",
    }


def save_catalog_snapshot(path: str | Path, view_code: str, crawl: dict) -> dict:
    """수집 결과를 병합 저장하고 다음 재개에 필요한 큐를 반환한다."""
    target = Path(path)
    previous = {}
    if target.exists():
        try:
            previous = json.loads(target.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            previous = {}
    merged = {str(row.get("TBL_ID")): row for row in previous.get("tables", []) if row.get("TBL_ID")}
    for row in crawl.get("tables", []):
        if row.get("TBL_ID"):
            merged[str(row["TBL_ID"])] = row
    snapshot = {
        "view_code": view_code,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "tables": list(merged.values()),
        "pending_parent_ids": list(crawl.get("pending_parent_ids", [])),
        "seen_parent_ids": list(dict.fromkeys([
            *previous.get("seen_parent_ids", []), *crawl.get("visited_parent_ids", []),
        ])),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"table_count": len(snapshot["tables"]), "pending_parent_ids": snapshot["pending_parent_ids"]}


class CatalogIndex:
    """수집된 KOSIS 표 메타 스냅샷을 검색하는 로컬 후보 인덱스."""

    def __init__(self, snapshot_path: str | Path, aliases: AliasDict | None = None):
        snapshot = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
        self.aliases = aliases if aliases is not None else AliasDict()
        self.tables = list(snapshot.get("tables", []))
        for table in self.tables:
            searchable = " ".join(str(table.get(field, "")) for field in (
                "TBL_NM", "STAT_NM", "MT_ATITLE", "CONTENTS", "ITEM03",
            ))
            table["_tokens"] = _tokens(searchable)

    def search(self, query: str, top_k: int = 5) -> list[TableHit]:
        query_tokens = _tokens(self.aliases.substitute(query))
        hits = []
        for table in self.tables:
            table_tokens = table["_tokens"]
            overlap = len(query_tokens & table_tokens)
            if not overlap:
                continue
            score = overlap / (len(query_tokens | table_tokens) ** 0.5)
            hits.append(TableHit(
                tbl_id=str(table.get("TBL_ID", "")),
                org_id=str(table.get("ORG_ID", "")),
                tbl_name=str(table.get("TBL_NM", "")),
                survey=str(table.get("STAT_NM", "")),
                score=round(score, 4),
            ))
        return sorted(hits, key=lambda hit: -hit.score)[:top_k]
