from typing import Literal


P_PLUS_H_PLUS = "P+/H+"
P_PLUS_H_MINUS = "P+/H-"
P_MINUS_H_PLUS = "P-/H+"
P_MINUS_H_MINUS = "P-/H-"
HCX_ERROR = "HCX_ERROR"

DisagreementType = Literal["P+/H+", "P+/H-", "P-/H+", "P-/H-", "HCX_ERROR"]


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
