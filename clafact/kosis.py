"""KOSIS Open API 클라이언트 — 실 HTTP 와 오프라인 픽스처의 공통 인터페이스.

응답 형식은 KOSIS 개발가이드(공개)의 통계자료 API(statisticsParameterData) 기준.
키가 없는 지금은 FixtureKosisClient 로 파서·정렬·판정 로직을 개발·테스트하고,
키 도착 시 HttpKosisClient 로 교체한다 (인터페이스 동일 — 스위치 켜기).
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Protocol


class KosisClient(Protocol):
    def fetch_data(self, org_id: str, tbl_id: str, **params) -> list[dict]:
        """통계자료 조회 → 표준 행 리스트.

        각 행: TBL_ID, TBL_NM, C1_NM(분류1), C2_NM(분류2), ITM_NM(항목),
               UNIT_NM(단위), PRD_DE(수록시점), DT(수치, 문자열)
        """
        ...


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


class HttpKosisClient:
    """실 KOSIS Open API. KOSIS_API_KEY 환경변수 필요.

    ⚠️ 키 발급 후 실 응답으로 파라미터·필드명을 검증할 것 (개발가이드 기준 구현).
    """

    BASE = "https://kosis.kr/openapi/Param/statisticsParameterData.do"

    def __init__(self, api_key: str | None = None, timeout: int = 15):
        self.api_key = api_key or os.environ.get("KOSIS_API_KEY", "")
        self.timeout = timeout
        if not self.api_key:
            raise RuntimeError("KOSIS_API_KEY 가 없습니다 — .env 설정 또는 FixtureKosisClient 사용")

    def fetch_data(self, org_id: str, tbl_id: str, **params) -> list[dict]:
        query = {
            "method": "getList", "apiKey": self.api_key, "format": "json", "jsonVD": "Y",
            "orgId": org_id, "tblId": tbl_id,
            "prdSe": params.get("prd_se", "Y"),
            "startPrdDe": params.get("prd_de", ""), "endPrdDe": params.get("prd_de", ""),
            "itmId": params.get("itm_id", "ALL"), "objL1": params.get("obj_l1", "ALL"),
            "objL2": params.get("obj_l2", "ALL"),
        }
        url = f"{self.BASE}?{urllib.parse.urlencode(query)}"
        with urllib.request.urlopen(url, timeout=self.timeout) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
        if isinstance(data, dict) and data.get("err"):
            raise RuntimeError(f"KOSIS API 오류: {data}")
        return data if isinstance(data, list) else []
