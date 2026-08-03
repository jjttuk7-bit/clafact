"""골든셋 기간 표현을 재현 가능한 KOSIS 조회 단위로 바꾼다."""

from __future__ import annotations

import re


_MONTH = re.compile(r"\b(\d{4}-\d{2})\b")
_YEAR = re.compile(r"\b(\d{4})\b")


def period_requests(period: str) -> list[tuple[str, str]]:
    """기간 메모에서 월(M) 또는 연(Y) KOSIS 조회 기간을 순서대로 반환한다."""
    months = list(dict.fromkeys(_MONTH.findall(period)))
    if "~" in period and len(months) >= 2:
        start, end = months[0], months[1]
        start_year, start_month = start.split("-")
        end_year, end_month = end.split("-")
        if start_month == end_month and int(start_year) <= int(end_year):
            return [(f"{year}-{start_month}", "M") for year in range(int(start_year), int(end_year) + 1)]
    if months:
        return [(month, "M") for month in months]
    years = list(dict.fromkeys(_YEAR.findall(period)))
    return [(year, "Y") for year in years]


def coordinate_query_params(plan: dict) -> list[dict[str, str]]:
    """선택 계획을 KOSIS의 itmId·objL 좌표 요청으로 전개한다."""
    shared = dict(plan.get("shared", {}))
    base: dict[str, str] = {}
    if shared.get("indicator_code"):
        base["itm_id"] = str(shared["indicator_code"])
    for dimension, code in dict(shared.get("selection_codes", {})).items():
        if dimension.startswith("C") and dimension[1:].isdigit():
            base[f"obj_l{dimension[1:]}"] = str(code)

    components = list(plan.get("components", [])) or [{}]
    queries: list[dict[str, str]] = []
    for component in components:
        query = dict(base)
        for dimension, code in dict(component.get("selection_codes", {})).items():
            if dimension.startswith("C") and dimension[1:].isdigit():
                query[f"obj_l{dimension[1:]}"] = str(code)
        queries.append(query)
    return queries


def limit_requests(requests: Sequence[tuple[str, str]], maximum: int) -> list[tuple[str, str]]:
    """한 실행에서 요청할 개수를 제한해 외부 API 장애 시 안전하게 중단한다."""
    if maximum < 1:
        raise ValueError("maximum must be at least 1")
    return list(requests[:maximum])


def exclude_completed_requests(
    requests: Sequence[tuple[str, str, str]],
    completed: set[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    """이미 동일 표·기간·주기로 저장된 스냅샷 요청은 다음 배치에서 제외한다."""
    return [request for request in requests if request not in completed]


def exclude_completed_coordinate_requests(
    requests: list[tuple[str, str, str, dict[str, str]]],
    completed_params: list[dict[str, object]],
) -> list[tuple[str, str, str, dict[str, str]]]:
    """동일 표·기간·좌표의 불변 스냅샷이 있으면 재호출하지 않는다."""
    def covered(request: tuple[str, str, str, dict[str, str]]) -> bool:
        query = {"prd_de": request[1], "prd_se": request[2], **request[3]}
        return any(
            all(str(query.get(key, "")) == str(value) for key, value in params.items())
            for params in completed_params
        )

    return [request for request in requests if not covered(request)]
