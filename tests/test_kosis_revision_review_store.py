from clafact.kosis_revision_impact import KosisRevisionImpact
from clafact.kosis_revision_review_store import KosisRevisionReviewStore


def impact() -> KosisRevisionImpact:
    return KosisRevisionImpact(
        shadow_run_id="shadow-001", row_index=3, table_id="DT_1B040A3",
        period="2025", indicator="총인구", value_before="50000000",
        value_after="50001000", match_score=100, note="인구 근거",
    )


def test_review_store_enqueues_impact_once_and_records_decision(tmp_path):
    with KosisRevisionReviewStore(tmp_path / "reviews.db") as store:
        review = store.enqueue(
            impact(), before_snapshot_id="before", after_snapshot_id="after",
            detected_at="2026-07-28T10:00:00+09:00",
        )
        assert store.enqueue(
            impact(), before_snapshot_id="before", after_snapshot_id="after",
            detected_at="2026-07-28T10:00:00+09:00",
        ).review_id == review.review_id
        assert store.list_for_table("DT_1B040A3")[0]["status"] == "pending"

        store.decide(
            review.review_id, action="ignored", note="값 변동이 문장 판단에 영향 없음",
            decided_at="2026-07-28T11:00:00+09:00",
        )
        saved = store.get(review.review_id)
        assert saved["status"] == "ignored"
        assert saved["note"] == "값 변동이 문장 판단에 영향 없음"
