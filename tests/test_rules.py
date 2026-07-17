"""A2 규칙 레지스트리 · A3 골든셋 append · 플라이휠 배선 테스트.

핵심 검증: **규칙 카드를 추가하면 탐지 동작이 실제로 바뀌는가** (문서 20 §3.1).
카드가 문서일 뿐이면 플라이휠은 연출이고, 실행되면 진짜다.
"""
import json
import shutil
import tempfile
from pathlib import Path

from clafact.assets.rules import RuleRegistry
from clafact.assets import goldenset
from clafact.pipeline import detect


def _tmpdir():
    return Path(tempfile.mkdtemp(prefix="clafact_test_"))


# ── A2 레지스트리 ──────────────────────────────────────────
def test_next_id_from_empty():
    d = _tmpdir()
    try:
        assert RuleRegistry(d).next_id() == "A2-0001"
    finally:
        shutil.rmtree(d)


def test_next_id_increments_past_existing():
    """문서 19 초안의 채번 충돌(A2-0009 중복) 재발 방지."""
    d = _tmpdir()
    try:
        reg = RuleRegistry(d)
        (d / "A2-0009_x.json").write_text('{"rule_id":"A2-0009"}', encoding="utf-8")
        (d / "A2-0010_y.json").write_text('{"rule_id":"A2-0010"}', encoding="utf-8")
        assert reg.next_id() == "A2-0011"
    finally:
        shutil.rmtree(d)


def test_real_repo_next_id():
    """실제 저장소 기준 다음 ID.

    A2-0012(잠정치)·A2-0013(기준연도) 등록으로 이제 A2-0014.
    (A2-0011 은 이중계상용으로 예약 — UP_ITM_ID 필요, 아직 미구현이라 번호 갭.)
    """
    root = Path(__file__).resolve().parents[1]
    assert RuleRegistry(root / "data/assets/rules").next_id() == "A2-0014"


def test_create_detection_requires_pattern():
    d = _tmpdir()
    try:
        reg = RuleRegistry(d)
        try:
            reg.create(type="detection", name="x", condition="c", handling="h")
            assert False, "pattern 없이 detection 카드가 생성되면 안 된다"
        except ValueError as e:
            assert "pattern" in str(e)
    finally:
        shutil.rmtree(d)


def test_create_rejects_bad_regex():
    d = _tmpdir()
    try:
        try:
            RuleRegistry(d).create(type="detection", name="x", condition="c",
                                   handling="h", pattern="((((")
            assert False, "깨진 정규식이 통과하면 안 된다"
        except ValueError as e:
            assert "정규식" in str(e)
    finally:
        shutil.rmtree(d)


def test_create_accepts_none_optionals():
    """선택 필드에 None 이 와도 죽지 않아야 한다 — 시연 4막의 주 경로.

    리뷰 보정 없이 문장을 직접 입력하면 fail_id 가 None 으로 넘어온다.
    초기 구현은 origin_run.strip() 에서 AttributeError 로 죽었다 (UI 실주행에서 발견).
    """
    d = _tmpdir()
    try:
        card = RuleRegistry(d).create(type="detection", name="n", condition="c",
                                      handling="h", pattern=r"x",
                                      origin_case=None, origin_run=None, test=None)
        assert card["origin_run"] == "" and card["origin_case"] == "" and card["test"] == ""
    finally:
        shutil.rmtree(d)


def test_create_writes_card_and_bumps_id():
    d = _tmpdir()
    try:
        reg = RuleRegistry(d)
        card = reg.create(type="detection", name="테스트 규칙", condition="c",
                          handling="h", pattern=r"반토막", origin_run="F123")
        assert card["rule_id"] == "A2-0001"
        assert reg.next_id() == "A2-0002"
        saved = json.loads(next(d.glob("A2-0001*.json")).read_text(encoding="utf-8"))
        assert saved["pattern"] == r"반토막"
        assert saved["origin_run"] == "F123"
        assert reg.stats()["executable"] == 1
    finally:
        shutil.rmtree(d)


# ── 플라이휠 핵심: 카드 추가 → 탐지 동작 변화 ────────────────
def test_new_rule_card_changes_detection():
    """플라이휠이 진짜인지 판별하는 테스트.

    '매출이 반토막 났다' 는 숫자가 없어 기존 필터가 놓친다.
    규칙 카드를 추가하면 **코드 수정 없이** 탐지되어야 한다.
    """
    d = _tmpdir()
    try:
        sentence = "지역 상권 매출이 반토막 났다."
        detect.reload_rules()
        assert not detect.is_candidate(sentence), "사전 조건: 원래는 놓쳐야 한다"

        RuleRegistry(d).create(type="detection", name="반토막 표현",
                               condition="'반토막' 포함", handling="후보로 탐지",
                               pattern=r"반토막")
        pats = detect.rule_patterns(d)
        assert [rid for rid, _ in pats] == ["A2-0001"]
        assert any(rx.search(sentence) for _, rx in pats), "카드 추가 후엔 잡혀야 한다"
    finally:
        shutil.rmtree(d)
        detect.reload_rules()


def test_broken_pattern_does_not_crash_pipeline():
    """깨진 카드 1장이 파이프라인 전체를 멈추면 안 된다."""
    d = _tmpdir()
    try:
        (d / "A2-0099_broken.json").write_text(
            json.dumps({"rule_id": "A2-0099", "type": "detection", "name": "깨짐",
                        "condition": "c", "handling": "h", "pattern": "(((("}),
            encoding="utf-8")
        assert detect.rule_patterns(d) == []
    finally:
        shutil.rmtree(d)
        detect.reload_rules()


def test_cache_invalidates_on_new_card():
    """캐시 무효화 회귀 테스트 — 시연 4막이 이 테스트에 달려 있다.

    초기 구현은 '디렉터리 mtime 변화'로 무효화했는데, Windows(NTFS)에서는
    파일을 새로 만들어도 상위 디렉터리 mtime 이 그대로인 경우가 있다(실측).
    그러면 규칙을 만들어도 낡은 캐시가 쓰여 점수가 오르지 않는 **조용한 실패**가 난다.
    성능을 이유로 파일 목록 지문(_signature)을 mtime 한 방으로 되돌리지 말 것.
    """
    d = _tmpdir()
    try:
        assert detect.rule_patterns(d) == []
        RuleRegistry(d).create(type="detection", name="신규", condition="c",
                               handling="h", pattern=r"급락")
        assert len(detect.rule_patterns(d)) == 1, "카드 추가가 즉시 반영돼야 한다"
    finally:
        shutil.rmtree(d)
        detect.reload_rules()


def test_dir_mtime_is_unreliable_documented():
    """위 버그의 근거를 코드로 남긴다 — 이 플랫폼에서 디렉터리 mtime 은 신뢰 불가.

    (이 테스트가 실패한다면 해당 플랫폼에선 mtime 이 동작한다는 뜻일 뿐,
     파일 목록 지문 방식은 어느 쪽에서도 안전하므로 그대로 두면 된다.)
    """
    d = _tmpdir()
    try:
        before = d.stat().st_mtime_ns
        (d / "A2-0001_probe.json").write_text("{}", encoding="utf-8")
        after = d.stat().st_mtime_ns
        # 콘솔 인코딩(cp949)에서 깨지지 않도록 ASCII 로만 출력한다
        if before == after:
            print("      (note: dir mtime does NOT update on this platform "
                  "-> file-list signature is required)")
        # 어느 쪽이든 지문 기반 무효화는 동작해야 한다
        assert detect.rule_patterns(d) == []  # 유효한 카드가 없으므로 패턴 0개
    finally:
        shutil.rmtree(d)
        detect.reload_rules()


# ── A3 골든셋 ─────────────────────────────────────────────
def test_goldenset_append_and_id():
    d = _tmpdir()
    try:
        p = d / "g.jsonl"
        r1 = goldenset.append_row(p, "지난해 실업률은 7.2%였다.", True, "match",
                                  claimed_value=7.2, claimed_unit="%")
        assert r1["article_id"] == "A001"
        r2 = goldenset.append_row(p, "경제가 나빠졌다.", False)
        assert r2["article_id"] == "A002"
        assert goldenset.stats(p)["total"] == 2
    finally:
        shutil.rmtree(d)


def test_goldenset_rejects_duplicate_and_missing_label():
    d = _tmpdir()
    try:
        p = d / "g.jsonl"
        goldenset.append_row(p, "같은 문장", True, "match")
        for bad, why in [
            (lambda: goldenset.append_row(p, "같은 문장", True, "match"), "중복"),
            (lambda: goldenset.append_row(p, "새 문장", True), "라벨 없는 주장"),
            (lambda: goldenset.append_row(p, "새 문장", True, "몰라"), "잘못된 라벨"),
        ]:
            try:
                bad()
                assert False, f"{why} 은 거부돼야 한다"
            except ValueError:
                pass
    finally:
        shutil.rmtree(d)


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
        except Exception:
            failed += 1
            print(f"  FAIL  {fn.__name__}")
            traceback.print_exc()
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
