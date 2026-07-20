"""공유 픽스처·스킵 규칙 — 테스트 구조 고도화 (2026-07-20).

핵심: 외부 자원(실물 데이터셋·실 API·카세트)이 없으면 **조용히 통과가 아니라 skip**.
skip 사유가 콘솔에 남아, '왜 안 돌았는지'가 항상 보이게 한다.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
# 데이터셋은 리포 밖(커밋 금지) — 상대 경로로 탐색
DATASET = REPO.parent / "news_data" / "[AI 기반 뉴스 사실검증 시스템] 프로젝트 데이터.csv"
CASSETTE_DIR = REPO / "tests" / "cassettes" / "hcx"


@pytest.fixture(scope="session")
def dataset_path() -> Path:
    if not DATASET.exists():
        pytest.skip(f"실물 데이터셋 없음: {DATASET} (news_data/ 배치 필요)")
    return DATASET


@pytest.fixture(scope="session")
def hcx_cassette():
    """녹화된 HCX 카세트를 재생 클라이언트로 제공. 없으면 skip."""
    from clafact.llm import Cassette, ReplayLLMClient
    path = CASSETTE_DIR / "smoke.json"
    if not path.exists():
        pytest.skip(f"HCX 카세트 없음: {path} (scripts/record_hcx.py 로 녹화 필요)")
    return ReplayLLMClient(Cassette(path))
