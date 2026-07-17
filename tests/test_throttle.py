"""호출 예산·레이트 리미터·캐시 테스트 (문서 19 §5.2~5.3).

실 API 를 때리지 않는다 — 가짜 클라이언트로 호출 횟수를 센다.
검증의 핵심: **예산 초과 시 호출하기 *전에* 멈추는가.**
넘고 나서 아는 건 이미 늦다 (계정 한도가 타 있다).
"""
import shutil
import tempfile
from pathlib import Path

from clafact.kosis import CachedKosisClient
from clafact.throttle import BudgetExceeded, CallBudget, RateLimiter, backoff_delays


def _tmp():
    return Path(tempfile.mkdtemp(prefix="clafact_thr_"))


class FakeClient:
    """호출 횟수를 세는 가짜 KOSIS 클라이언트."""

    def __init__(self, rows=None):
        self.calls = 0
        self.rows = rows if rows is not None else [{"DT": "1", "PRD_DE": "2024"}]

    def fetch_data(self, org_id, tbl_id, **params):
        self.calls += 1
        return self.rows


# ── 예산 가드 ──────────────────────────────────────────────
def test_budget_counts_and_persists():
    d = _tmp()
    try:
        b = CallBudget(d / "b.json", limit=10)
        assert b.used() == 0 and b.remaining() == 10
        b.spend(3, "test")
        assert b.used() == 3 and b.remaining() == 7
        # 새 인스턴스(=프로세스 재시작)에서도 카운터가 살아야 한다
        assert CallBudget(d / "b.json", limit=10).used() == 3
    finally:
        shutil.rmtree(d)


def test_budget_blocks_before_exceeding():
    """초과를 '감지'하는 게 아니라 '사전 차단'해야 한다."""
    d = _tmp()
    try:
        b = CallBudget(d / "b.json", limit=5)
        b.spend(5)
        try:
            b.check(1)
            assert False, "예산 소진 후 check 가 통과하면 안 된다"
        except BudgetExceeded as e:
            assert "5/5" in str(e)
    finally:
        shutil.rmtree(d)


def test_budget_warns_near_limit():
    d = _tmp()
    try:
        b = CallBudget(d / "b.json", limit=10, warn_at=0.8)
        b.spend(7)
        assert not b.should_warn()
        b.spend(1)
        assert b.should_warn(), "80% 도달 시 경고해야 한다"
    finally:
        shutil.rmtree(d)


def test_budget_log_does_not_grow_unbounded():
    d = _tmp()
    try:
        b = CallBudget(d / "b.json", limit=10_000)
        for _ in range(250):
            b.spend(1, "x")
        import json
        assert len(json.loads((d / "b.json").read_text(encoding="utf-8"))["log"]) <= 200
    finally:
        shutil.rmtree(d)


def test_corrupt_budget_file_does_not_crash():
    d = _tmp()
    try:
        (d / "b.json").write_text("{{{ broken", encoding="utf-8")
        assert CallBudget(d / "b.json", limit=10).used() == 0
    finally:
        shutil.rmtree(d)


# ── 레이트 리미터 ──────────────────────────────────────────
def test_rate_limiter_allows_under_limit():
    slept = []
    r = RateLimiter(per_minute=5)
    for _ in range(5):
        r.acquire(sleep=slept.append)
    assert slept == [], "한도 내에서는 대기하지 않아야 한다"


def test_rate_limiter_waits_over_limit():
    slept = []
    r = RateLimiter(per_minute=3)
    for _ in range(4):
        r.acquire(sleep=slept.append)
    assert len(slept) == 1 and slept[0] > 0, f"4번째 호출은 대기해야 한다: {slept}"


def test_rate_limiter_rejects_bad_config():
    try:
        RateLimiter(per_minute=0)
        assert False, "per_minute=0 은 거부돼야 한다"
    except ValueError:
        pass


def test_backoff_grows_and_caps():
    d = backoff_delays(tries=6, base=1.0, cap=8.0)
    assert d == [1.0, 2.0, 4.0, 8.0, 8.0, 8.0], d


# ── 캐시 ──────────────────────────────────────────────────
def test_cache_prevents_second_call():
    """같은 질의 재호출 = 예산 낭비. 하네스 반복 실행의 생존 조건."""
    d = _tmp()
    try:
        fake = FakeClient()
        c = CachedKosisClient(fake, d)
        a = c.fetch_data("101", "DT_X", prd_de="2024")
        b = c.fetch_data("101", "DT_X", prd_de="2024")
        assert a == b
        assert fake.calls == 1, f"캐시 히트인데 실제 호출됨: {fake.calls}회"
        assert c.stats()["hits"] == 1 and c.stats()["misses"] == 1
    finally:
        shutil.rmtree(d)


def test_cache_distinguishes_params():
    d = _tmp()
    try:
        fake = FakeClient()
        c = CachedKosisClient(fake, d)
        c.fetch_data("101", "DT_X", prd_de="2024")
        c.fetch_data("101", "DT_X", prd_de="2023")   # 다른 시점 = 다른 질의
        c.fetch_data("101", "DT_Y", prd_de="2024")   # 다른 표
        assert fake.calls == 3, f"서로 다른 질의가 합쳐짐: {fake.calls}"
    finally:
        shutil.rmtree(d)


def test_cache_survives_new_instance():
    """프로세스가 죽어도 캐시는 남아야 한다 — 하네스는 매번 새로 뜬다."""
    d = _tmp()
    try:
        fake = FakeClient()
        CachedKosisClient(fake, d).fetch_data("101", "DT_X", prd_de="2024")
        CachedKosisClient(fake, d).fetch_data("101", "DT_X", prd_de="2024")
        assert fake.calls == 1, f"새 인스턴스가 캐시를 못 읽음: {fake.calls}회"
    finally:
        shutil.rmtree(d)


def test_corrupt_cache_falls_back_to_fetch():
    d = _tmp()
    try:
        fake = FakeClient()
        c = CachedKosisClient(fake, d)
        c.fetch_data("101", "DT_X", prd_de="2024")
        for f in d.glob("*.json"):
            f.write_text("{{{ broken", encoding="utf-8")
        rows = c.fetch_data("101", "DT_X", prd_de="2024")
        assert rows == fake.rows and fake.calls == 2, "캐시가 깨지면 다시 받아야 한다"
    finally:
        shutil.rmtree(d)


def test_cache_ttl_expires():
    d = _tmp()
    try:
        fake = FakeClient()
        c = CachedKosisClient(fake, d, ttl_sec=-1)  # 즉시 만료
        c.fetch_data("101", "DT_X", prd_de="2024")
        c.fetch_data("101", "DT_X", prd_de="2024")
        assert fake.calls == 2, "TTL 만료 시 재호출해야 한다"
    finally:
        shutil.rmtree(d)


# ── HttpKosisClient 배선 (네트워크 없이) ──────────────────
def test_http_client_blocks_on_exhausted_budget_without_network():
    """예산이 없으면 **네트워크를 건드리기 전에** 멈춰야 한다.

    urlopen 을 폭탄으로 바꿔놓고 호출한다 — 네트워크에 닿으면 테스트가 터진다.
    """
    import urllib.request
    from clafact.kosis import HttpKosisClient

    d = _tmp()
    orig = urllib.request.urlopen
    try:
        b = CallBudget(d / "b.json", limit=2)
        b.spend(2)
        c = HttpKosisClient(api_key="DUMMY", budget=b, rate_limiter=RateLimiter(60))

        def boom(*a, **k):
            raise AssertionError("예산이 소진됐는데 네트워크 호출이 나갔다")
        urllib.request.urlopen = boom
        try:
            c.fetch_data("101", "DT_X", prd_de="2024")
            assert False, "BudgetExceeded 가 나야 한다"
        except BudgetExceeded:
            pass
    finally:
        urllib.request.urlopen = orig
        shutil.rmtree(d)


def test_http_client_spends_budget_on_success():
    """성공 호출은 예산을 1 차감해야 한다 — 안 세면 가드가 무의미하다."""
    import io
    import urllib.request
    from clafact.kosis import HttpKosisClient

    d = _tmp()
    orig = urllib.request.urlopen
    try:
        b = CallBudget(d / "b.json", limit=10)
        c = HttpKosisClient(api_key="DUMMY", budget=b, rate_limiter=RateLimiter(60))

        class Resp(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *a): return False

        urllib.request.urlopen = lambda *a, **k: Resp(
            b'[{"DT":"1","PRD_DE":"2024","TBL_NM":"t"}]')
        rows = c.fetch_data("101", "DT_X", prd_de="2024")
        assert len(rows) == 1
        assert b.used() == 1, f"예산이 차감되지 않음: {b.used()}"
    finally:
        urllib.request.urlopen = orig
        shutil.rmtree(d)


def test_connection_failure_does_not_spend_budget():
    """연결 실패는 예산을 차감하면 안 된다 — KOSIS 가 받은 적 없는 호출이다.

    우리 개발망은 정부망 443 을 차단한다(문서 19 §5.5). 여기서 차감하면
    KOSIS 는 구경도 못한 호출로 로컬 카운터만 1,000까지 태운다.
    """
    import urllib.error
    import urllib.request
    from clafact.kosis import HttpKosisClient

    d = _tmp()
    orig = urllib.request.urlopen
    try:
        b = CallBudget(d / "b.json", limit=10)
        c = HttpKosisClient(api_key="DUMMY", budget=b, rate_limiter=RateLimiter(600))
        c.timeout = 0.01

        def blocked(*a, **k):
            raise urllib.error.URLError("handshake timed out")
        urllib.request.urlopen = blocked

        import clafact.kosis as K
        orig_sleep = K.time.sleep
        K.time.sleep = lambda s: None      # 백오프 대기 건너뛰기
        try:
            c.fetch_data("101", "DT_X", prd_de="2024")
            assert False, "실패해야 한다"
        except RuntimeError as e:
            assert "예산은 차감하지 않았습니다" in str(e)
        finally:
            K.time.sleep = orig_sleep
        assert b.used() == 0, f"연결 실패인데 예산이 차감됨: {b.used()}"
    finally:
        urllib.request.urlopen = orig
        shutil.rmtree(d)


def test_http_error_does_spend_budget():
    """서버가 응답했으면(4xx/5xx 포함) 한도를 쓴 것이므로 차감해야 한다."""
    import urllib.error
    import urllib.request
    from clafact.kosis import HttpKosisClient

    d = _tmp()
    orig = urllib.request.urlopen
    try:
        b = CallBudget(d / "b.json", limit=10)
        c = HttpKosisClient(api_key="DUMMY", budget=b, rate_limiter=RateLimiter(600))

        def too_many(*a, **k):
            raise urllib.error.HTTPError("u", 429, "Too Many Requests", {}, None)
        urllib.request.urlopen = too_many
        try:
            c.fetch_data("101", "DT_X", prd_de="2024")
            assert False, "실패해야 한다"
        except RuntimeError as e:
            assert "429" in str(e)
        assert b.used() == 1, f"서버 응답인데 예산이 차감되지 않음: {b.used()}"
    finally:
        urllib.request.urlopen = orig
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
