import os
from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel, Field
from backend.app.ingest_service import import_article_file
from clafact.kosis import CachedKosisClient, FixtureKosisClient, HttpKosisClient
from clafact.llm import HcxClient
from clafact.pipeline.detect_llm import judge
from clafact.pipeline.retrieve import StatIndex
from clafact.service.batch import process_pending
from clafact.service.store import Store
app = FastAPI(title="ClaFact API", version="0.1.0")
@app.get("/health")
def health(): return {"service":"clafact-api","status":"ok"}
def hcx_detection_signal(sentence: str) -> dict:
    ok, reason = judge(sentence, HcxClient())
    return {"verifiable": ok, "reason": reason, "mode": "live"}
def build_kosis_engine():
    root=Path(__file__).resolve().parents[2]; index=StatIndex(root/"data/samples/kosis/tables_meta.json")
    if os.environ.get("CLAFACT_KOSIS_MODE","fixture").lower()=="live" and os.environ.get("KOSIS_API_KEY"):
        return index, CachedKosisClient(HttpKosisClient(), Path(os.environ.get("CLAFACT_KOSIS_CACHE_DIR", root/"data/cache/kosis")))
    return index, FixtureKosisClient(root/"data/samples/kosis")
class ProcessPendingRequest(BaseModel): limit:int|None=Field(default=None,ge=1)
class ArticleImportRequest(BaseModel): path:str
@app.post("/internal/batches/process-pending")
def process_pending_batch(request:ProcessPendingRequest)->dict:
    root=Path(__file__).resolve().parents[2]; store=Store(Path(os.environ.get("CLAFACT_SERVICE_DB",root/"data/service/clafact.db")))
    try:
        index,client=build_kosis_engine(); return process_pending(store,index,client,limit=request.limit)
    finally: store.close()
@app.post("/internal/articles/import")
def import_article(request:ArticleImportRequest)->dict[str,int]:
    root=Path(__file__).resolve().parents[2]; store=Store(Path(os.environ.get("CLAFACT_SERVICE_DB",root/"data/service/clafact.db")))
    try:
        signal=hcx_detection_signal if os.environ.get("CLAFACT_HCX_MODE","fixture").lower()=="live" else None
        return import_article_file(request.path,store,hcx_signal=signal)
    finally: store.close()