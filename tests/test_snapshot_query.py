from clafact.eval.snapshot_query import period_requests


def test_expands_same_month_year_range_for_historical_comparison():
    assert period_requests("1990-04~2025-04 (4월 전년동월비 비교)") == [
        (f"{year}-04", "M") for year in range(1990, 2026)
    ]


def test_keeps_explicit_months_and_identifies_year_periods():
    assert period_requests("2024-10, 2025-10") == [("2024-10", "M"), ("2025-10", "M")]
    assert period_requests("2024") == [("2024", "Y")]


def test_limits_queue_to_a_reproducible_batch_size():
    from clafact.eval.snapshot_query import limit_requests

    requests = [(f"2025-{month:02d}", "M") for month in range(1, 6)]
    assert limit_requests(requests, 2) == requests[:2]


def test_excludes_requests_already_saved_as_snapshots():
    from clafact.eval.snapshot_query import exclude_completed_requests

    requests = [("DT_X", "2024-10", "M"), ("DT_X", "2025-10", "M")]
    assert exclude_completed_requests(requests, {("DT_X", "2024-10", "M")}) == [("DT_X", "2025-10", "M")]


def test_expands_component_selection_codes_into_small_kosis_queries():
    from clafact.eval.snapshot_query import coordinate_query_params

    plan = {
        "shared": {"indicator_code": "T", "selection_codes": {"C1": "T10"}},
        "components": [
            {"name": "배추", "selection_codes": {"C2": "A02A01701"}},
            {"name": "무", "selection_codes": {"C2": "A02A01708"}},
        ],
    }

    assert coordinate_query_params(plan) == [
        {"itm_id": "T", "obj_l1": "T10", "obj_l2": "A02A01701"},
        {"itm_id": "T", "obj_l1": "T10", "obj_l2": "A02A01708"},
    ]


def test_excludes_coordinate_request_when_exact_snapshot_exists():
    from clafact.eval.snapshot_query import exclude_completed_coordinate_requests

    requests = [
        ("DT_X", "2025-10", "M", {"itm_id": "T", "obj_l1": "T10", "obj_l2": "rice"}),
        ("DT_X", "2025-10", "M", {"itm_id": "T", "obj_l1": "T10", "obj_l2": "apple"}),
    ]
    completed = [{"prd_de": "2025-10", "prd_se": "M", "itm_id": "T", "obj_l1": "T10", "obj_l2": "rice"}]

    assert exclude_completed_coordinate_requests(requests, completed) == [requests[1]]


def test_excludes_coordinate_request_when_broad_period_snapshot_exists():
    from clafact.eval.snapshot_query import exclude_completed_coordinate_requests

    request = ("DT_X", "2024-10", "M", {"itm_id": "T", "obj_l1": "T10", "obj_l2": "rice"})
    assert exclude_completed_coordinate_requests([request], [{"prd_de": "2024-10", "prd_se": "M"}]) == []
