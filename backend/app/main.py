import os
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, Field

from clafact.kosis import CachedKosisClient, FixtureKosisClient, HttpKosisClient
from clafact.pipeline.retrieve import StatIndex
from clafact.service.batch import process_pending
from clafact.service.store import Store


app = FastAPI(title="ClaFact API", version="0.1.0", description="Evidence-backed Korean news claim verification service.")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"service": "clafact-api", "status": "ok"}


def build_kosis_engine():
    root = Path(__file__).resolve().parents[2]
    index = StatIndex(root / "data/samples/kosis/tables_meta.json")
    if os.environ.get("CLAFACT_KOSIS_MODE", "fixture").lower() == "live" and os.environ.get("KOSIS_API_KEY"):
        cache_dir = Path(os.environ.get("CLAFACT_KOSIS_CACHE_DIR", root / "data/cache/kosis"))
        return index, CachedKosisClient(HttpKosisClient(), cache_dir)
    return index, FixtureKosisClient(root / "data/samples/kosis")


class ProcessPendingRequest(BaseModel):
    limit: int | None = Field(default=None, ge=1)


@app.post("/internal/batches/process-pending", tags=["internal"])
def process_pending_batch(request: ProcessPendingRequest) -> dict:
    root = Path(__file__).resolve().parents[2]
    db_path = Path(os.environ.get("CLAFACT_SERVICE_DB", root / "data/service/clafact.db"))
    store = Store(db_path)
    try:
        index, client = build_kosis_engine()
        return process_pending(store, index, client, limit=request.limit)
    finally:
        store.close()