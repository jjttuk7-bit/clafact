import pytest

from clafact.shadow_policy import ShadowPolicy


def test_default_policy_is_review_safe():
    policy = ShadowPolicy.default()

    assert policy.domain == "population"
    assert policy.evidence_source == "KOSIS"
    assert policy.default_when_uncertain == "insufficient_evidence"
    assert "candidate_conflict" in policy.review_when


def test_policy_rejects_unknown_claim_type():
    with pytest.raises(ValueError, match="claim type"):
        ShadowPolicy(claim_types=("unknown",))


def test_policy_round_trips_through_dictionary():
    policy = ShadowPolicy.default()

    assert ShadowPolicy.from_dict(policy.as_dict()) == policy
