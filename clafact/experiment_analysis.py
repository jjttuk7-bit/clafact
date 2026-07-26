from typing import Final, Literal


DisagreementType = Literal["P+/H+", "P+/H-", "P-/H+", "P-/H-", "HCX_ERROR"]

P_PLUS_H_PLUS: Final[Literal["P+/H+"]] = "P+/H+"
P_PLUS_H_MINUS: Final[Literal["P+/H-"]] = "P+/H-"
P_MINUS_H_PLUS: Final[Literal["P-/H+"]] = "P-/H+"
P_MINUS_H_MINUS: Final[Literal["P-/H-"]] = "P-/H-"
HCX_ERROR: Final[Literal["HCX_ERROR"]] = "HCX_ERROR"


def classify_disagreement(
    python_candidate: bool,
    hcx_candidate: bool,
    hcx_status: str | None,
) -> DisagreementType:
    if hcx_status != "success":
        return HCX_ERROR
    if python_candidate:
        return P_PLUS_H_PLUS if hcx_candidate else P_PLUS_H_MINUS
    return P_MINUS_H_PLUS if hcx_candidate else P_MINUS_H_MINUS
