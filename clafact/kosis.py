"""KOSIS Open API 클라이언트 — 실 HTTP 와 오프라인 픽스처의 공통 인터페이스.

응답 형식은 KOSIS 개발가이드(공개)의 통계자료 API(statisticsParameterData) 기준.
키가 없는 지금은 FixtureKosisClient 로 파서·정렬·판정 로직을 개발·테스트하고,
키 도착 시 HttpKosisClient 로 교체한다 (인터페이스 동일 — 스위치 켜기).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Protocol

from clafact.throttle import CallBudget, RateLimiter, backoff_delays


BASE_URL = "https://kosis.kr/openapi/Param/statisticsParameterData.do"
SEARCH_URL = "https://kosis.kr/openapi/statisticsSearch.do"  # KOSIS 통합검색 (경로 C)


def parse_json_tolerant(text: str):
    """KOSIS 응답 파싱. 표준 JSON 우선.

    ⚠️ 2026-07-15 통합검색 응답을 브라우저 innerText 로 봤을 때 키에 따옴표가 없는
       형태로 관찰됐다(원인 미확정 — innerText 렌더링 문제일 수도). 방어적으로,
       표준 파싱 실패 시 '키만 따옴표 없는' 경우에 한해 1회 보정을 시도한다.
       실 API 클라우드 검증 시 실제 포맷을 확인하고 이 폴백의 요부를 판단할 것.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        fixed = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*:)', r'\1"\2"\3', text)
        return json.loads(fixed)   # 여기서도 실패하면 그대로 예외 (진짜 깨진 응답)

# 인증키 자리표시자 — 재현 URL 에는 절대 실 키를 넣지 않는다.
# 데모는 공개 배포(Streamlit Cloud)이므로 화면에 찍히는 순간 키가 유출된다.
KEY_PLACEHOLDER = "{KOSIS_API_KEY}"


def build_query(org_id: str, tbl_id: str, api_key: str = KEY_PLACEHOLDER, **params) -> dict:
    """통계자료 API 쿼리 파라미터 — 실 호출과 재현 URL 이 **같은 함수**를 쓴다.

    둘을 따로 만들면 언젠가 어긋나고, 그러면 "재현 URL"이 거짓말이 된다.
    형식은 2026-07-14 실 API 스모크 테스트로 검증됨 (문서 16):
      objL1~objL8 을 빈 값이라도 전부 포함 + newEstPrdCnt 지정 (누락 시 err 21)
    """
    return {
        "method": "getList", "apiKey": api_key,
        "itmId": params.get("itm_id", "ALL"),
        "objL1": params.get("obj_l1", "ALL"),
        "objL2": params.get("obj_l2", ""), "objL3": "", "objL4": "",
        "objL5": "", "objL6": "", "objL7": "", "objL8": "",
        "format": "json", "jsonVD": "Y",
        "prdSe": params.get("prd_se", "Y"),
        "newEstPrdCnt": str(params.get("recent_n", 5)),
        "orgId": org_id, "tblId": tbl_id,
    }


def build_url(org_id: str, tbl_id: str, api_key: str = KEY_PLACEHOLDER, **params) -> str:
    """호출 URL. api_key 를 넘기지 않으면 자리표시자가 들어간 안전한 재현용 URL."""
    q = build_query(org_id, tbl_id, api_key, **params)
    url = f"{BASE_URL}?{urllib.parse.urlencode(q, safe='{}')}"
    return url


def build_search_url(search_nm: str, api_key: str = KEY_PLACEHOLDER, *,
                     sort: str = "RANK", result_count: int = 10,
                     start_count: int = 1, org_id: str = "") -> str:
    """KOSIS 통합검색(경로 C) URL. 엔드포인트·파라미터는 개발가이드 2026-07-15 확인.

    fetch 재현 URL 과 마찬가지로 키 미지정 시 자리표시자 → 화면 노출 안전.
    """
    q = {"method": "getList", "apiKey": api_key, "format": "json",
         "searchNm": search_nm, "sort": sort,
         "resultCount": str(result_count), "startCount": str(start_count)}
    if org_id:
        q["orgId"] = org_id
    return f"{SEARCH_URL}?{urllib.parse.urlencode(q, safe='{}')}"


class KosisClient(Protocol):
    def fetch_data(self, org_id: str, tbl_id: str, **params) -> list[dict]:
        """통계자료 조회 → 표준 행 리스트.

        각 행 (공식 개발가이드 2026-07-15 확인):
          ORG_ID, TBL_ID, TBL_NM, C1~C8(분류값 ID), C1_OBJ_NM~(분류명),
          C1_NM~C8_NM(분류값명), ITM_ID, ITM_NM(항목), UNIT_ID, UNIT_NM(단위),
          PRD_SE(주기), PRD_DE(수록시점), DT(수치, 문자열),
          LST_CHN_DE(최종수정일)  ← 규칙 A2-0012 의 근거

        ⚠️ 시점 파라미터(startPrdDe/endPrdDe/newEstPrdCnt)는 **수록시점**만 가리킨다.
           **공표 시점(vintage)을 지정하는 파라미터는 존재하지 않는다** — 즉 항상
           현재 확정값만 받는다. 기사가 인용한 당시 잠정치는 원리적으로 알 수 없으므로,
           LST_CHN_DE 가 기사 작성일보다 나중이면 판단불가로 회피한다 (문서 19 §7.1).
        """
        ...

    def integrated_search(self, searchNm: str, sort: str = "RANK",
                          resultCount: int = 10) -> list[dict]:
        """통합검색(경로 C) → 통계표 후보 행 리스트.

        각 행 (개발가이드 2026-07-15): ORG_ID, TBL_ID, TBL_NM, STAT_NM,
        STRT_PRD_DE, END_PRD_DE, REC_TBL_SE(추천표), STAT_DB_CNT(총건수) 등.
        """
        ...


_TOKEN = re.compile(r"[가-힣A-Za-z0-9]+")


class FixtureKosisClient:
    """오프라인 픽스처 — data/samples/kosis/{TBL_ID}.json 을 읽는다."""

    def __init__(self, fixture_dir: str | Path = "data/samples/kosis"):
        self.dir = Path(fixture_dir)

    def fetch_data(self, org_id: str, tbl_id: str, **params) -> list[dict]:
        path = self.dir / f"{tbl_id}.json"
        if not path.exists():
            return []  # 대응 통계 부재 → 상위에서 판단불가 분기
        rows = json.loads(path.read_text(encoding="utf-8"))
        # 실 API 의 startPrdDe/endPrdDe 를 흉내: PRD_DE 필터
        prd = params.get("prd_de")
        if prd:
            rows = [r for r in rows if r.get("PRD_DE") == str(prd).replace("-", "")[:4]]
        return rows

    def integrated_search(self, searchNm: str, sort: str = "RANK",
                          resultCount: int = 10) -> list[dict]:
        """오프라인 스탠드인 — tables_meta 를 토큰 겹침으로 랭킹해 통합검색을 흉내낸다.

        실 API 는 28만 표 전체를 RANK 검색하지만, 오프라인에선 픽스처의 5개 표로
        **클라이언트·파싱·시점필터 배선을 검증**한다. 클라우드에서 HttpKosisClient 로
        스위치하면 진짜 검색이 된다 (인터페이스 동일).
        """
        meta = self.dir / "tables_meta.json"
        if not meta.exists():
            return []
        tables = json.loads(meta.read_text(encoding="utf-8"))
        qtok = set(_TOKEN.findall(searchNm))
        scored = []
        for t in tables:
            doc = f"{t['TBL_NM']} {t.get('SURVEY', '')} {t.get('KEYWORDS', '')}"
            dtok = set(_TOKEN.findall(doc))
            # 부분 문자열 겹침 포함 (형태 유사 — 실 RANK 의 대역)
            overlap = sum(1 for a in qtok for b in dtok if a in b or b in a)
            if overlap:
                scored.append((overlap, t))
        scored.sort(key=lambda x: -x[0])
        out = []
        for _, t in scored[:resultCount]:
            out.append({
                "ORG_ID": t["ORG_ID"], "TBL_ID": t["TBL_ID"], "TBL_NM": t["TBL_NM"],
                "STAT_NM": t.get("SURVEY", ""),
                "STRT_PRD_DE": t.get("STRT_PRD_DE", ""), "END_PRD_DE": t.get("END_PRD_DE", ""),
                "REC_TBL_SE": "Y",
            })
        return out


class HttpKosisClient:
    """실 KOSIS Open API. KOSIS_API_KEY 환경변수 필요.

    ⚠️ 키 발급 후 실 응답으로 파라미터·필드명을 검증할 것 (개발가이드 기준 구현).
    """

    BASE = BASE_URL

    def __init__(self, api_key: str | None = None, timeout: int = 15,
                 rate_limiter: RateLimiter | None = None,
                 budget: CallBudget | None = None):
        self.api_key = api_key or os.environ.get("KOSIS_API_KEY", "")
        self.timeout = timeout
        # 기본값으로도 보호되게 한다 — 가드는 "켜는 걸 잊으면" 없는 것과 같다.
        self.rate = rate_limiter or RateLimiter(per_minute=30)
        self.budget = budget or CallBudget()
        if not self.api_key:
            raise RuntimeError("KOSIS_API_KEY 가 없습니다 — .env 설정 또는 FixtureKosisClient 사용")

    def _call(self, url: str, note: str):
        """공통 호출 — 예산 확인 → 레이트·백오프 → 파싱. fetch_data·integrated_search 공용.

        예산 차감 규칙 (**KOSIS 가 요청을 받은 경우에만** 센다):
          - urlopen 성공 → 차감. 서버가 응답했으므로 한도를 썼다 (파싱 실패도 응답은 받음).
          - HTTP 에러(4xx/5xx) → 차감. 서버가 처리했다.
          - 연결 실패(URLError/timeout) → **차감 안 함.** 개발망은 정부망 443 을 차단하므로
            (문서 19 §5.5) 헛되이 차감하면 KOSIS 가 받은 적 없는 호출로 로컬 카운터만 태운다.
        """
        self.budget.check(1)          # 예산 초과면 호출하기 *전에* 멈춘다
        for i, delay in enumerate(backoff_delays()):
            self.rate.acquire()
            try:
                with urllib.request.urlopen(url, timeout=self.timeout) as resp:  # noqa: S310
                    text = resp.read().decode("utf-8")
                self.budget.spend(1, note)          # urlopen 성공 = 서버 응답 = 차감
                data = parse_json_tolerant(text)     # 파싱 실패는 응답 받은 뒤 문제 → 이미 차감됨
                if isinstance(data, dict) and data.get("err"):
                    raise RuntimeError(f"KOSIS API 오류: {data}")
                return data
            except urllib.error.HTTPError as e:
                self.budget.spend(1, f"{note} HTTP{e.code}")
                raise RuntimeError(f"KOSIS HTTP 오류 {e.code}: {e.reason}") from e
            except (urllib.error.URLError, TimeoutError) as e:   # 연결 실패만 재시도·미차감
                if i == len(backoff_delays()) - 1:
                    raise RuntimeError(
                        f"KOSIS 호출 실패({type(e).__name__}): {e}\n"
                        f"  → 연결 실패이므로 호출 예산은 차감하지 않았습니다 "
                        f"(남음 {self.budget.remaining()}회). 개발망에서 정부망 443 이 "
                        f"차단될 수 있습니다 — 문서 19 §5.5 참조"
                    ) from e
                time.sleep(delay)

    def fetch_data(self, org_id: str, tbl_id: str, **params) -> list[dict]:
        """통계자료 조회. objL1~8 전부 + newEstPrdCnt (누락 시 err 21). prd_de 필터는 클라이언트."""
        url = build_url(org_id, tbl_id, self.api_key, **params)
        data = self._call(url, f"data {tbl_id} {params.get('prd_de', '')}")
        rows = data if isinstance(data, list) else []
        prd = str(params.get("prd_de", "")).replace("-", "")[:4]
        if prd:
            rows = [r for r in rows if str(r.get("PRD_DE", "")).startswith(prd)]
        return rows

    def integrated_search(self, searchNm: str, sort: str = "RANK",
                          resultCount: int = 10) -> list[dict]:
        """통합검색(경로 C) — 검색어로 28만 표 RANK 검색 → 후보 행 리스트."""
        url = build_search_url(searchNm, self.api_key, sort=sort, result_count=resultCount)
        data = self._call(url, f"search {searchNm[:20]}")
        return data if isinstance(data, list) else []


class CachedKosisClient:
    """캐시 래퍼 — 같은 (orgId, tblId, 파라미터)는 두 번 호출하지 않는다.

    문서 19 §5.2: "평가 하네스는 반복 실행이 전제이므로 캐시 없이는
    하네스를 돌릴수록 한도가 녹는다. 이는 성능 최적화가 아니라 생존 조건이다."

    KosisClient 프로토콜을 그대로 만족하므로 어느 클라이언트든 감쌀 수 있다:
        client = CachedKosisClient(HttpKosisClient())
    """

    def __init__(self, inner, cache_dir: str | Path = "data/cache/kosis",
                 ttl_sec: float | None = None):
        self.inner = inner
        self.dir = Path(cache_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl_sec          # None = 만료 없음 (통계는 자주 바뀌지 않는다)
        self.hits = 0
        self.misses = 0

    def _key(self, org_id: str, tbl_id: str, params: dict) -> Path:
        raw = json.dumps({"o": org_id, "t": tbl_id, "p": params},
                         sort_keys=True, ensure_ascii=False)
        h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        return self.dir / f"{tbl_id}_{h}.json"

    def fetch_data(self, org_id: str, tbl_id: str, **params) -> list[dict]:
        p = self._key(org_id, tbl_id, params)
        if p.exists():
            try:
                blob = json.loads(p.read_text(encoding="utf-8"))
                fresh = self.ttl is None or (time.time() - blob.get("fetched_at", 0)) < self.ttl
                if fresh:
                    self.hits += 1
                    return blob["rows"]
            except (json.JSONDecodeError, KeyError, OSError):
                pass  # 캐시가 깨졌으면 그냥 다시 받는다

        rows = self.inner.fetch_data(org_id, tbl_id, **params)
        self.misses += 1
        p.write_text(json.dumps(
            {"fetched_at": time.time(),
             "fetched_at_h": time.strftime("%Y-%m-%dT%H:%M:%S"),
             "org_id": org_id, "tbl_id": tbl_id, "params": params, "rows": rows},
            ensure_ascii=False), encoding="utf-8")
        return rows

    def stats(self) -> dict:
        total = self.hits + self.misses
        return {"hits": self.hits, "misses": self.misses,
                "hit_rate": (self.hits / total) if total else None,
                "cached_files": len(list(self.dir.glob("*.json")))}
