from clafact.pipeline import detect_llm


class FalseClient:
    def complete(self, *args, **kwargs):
        return '{"verifiable": false, "reason": "식별용 숫자"}'


def test_assist_keeps_rule_candidate_when_hcx_rejects() -> None:
    sentence = "올해 실업률은 7.2%로 상승했다."

    candidate, signal = detect_llm.assist(sentence, FalseClient())

    assert candidate is True
    assert signal is False
