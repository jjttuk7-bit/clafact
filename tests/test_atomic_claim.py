from clafact.atomic_claim import extract_atomic_claims


def test_extracts_named_parenthesized_quantities_as_ordered_atomic_claims():
    claims = extract_atomic_claims("배추(-34.5%), 무(-40.5%), 쌀(21.3%)")

    assert [(claim.claim_index, claim.subject, claim.value_raw, claim.unit) for claim in claims] == [
        (1, "배추", "-34.5%", "%"),
        (2, "무", "-40.5%", "%"),
        (3, "쌀", "21.3%", "%"),
    ]


def test_does_not_split_a_single_named_quantity_into_atomic_claims():
    assert extract_atomic_claims("배추는 -34.5% 하락했다.") == ()


def test_requires_explicit_quantity_units_to_avoid_splitting_labels():
    assert extract_atomic_claims("배추(1), 무(2), 쌀(3)이다.") == ()
