import os
import tempfile
from pathlib import Path
from fastapi import Body, FastAPI, Header, HTTPException
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
def import_article(request:ArticleImportRequest)->dict[str, object]:
    root=Path(__file__).resolve().parents[2]; store=Store(Path(os.environ.get("CLAFACT_SERVICE_DB",root/"data/service/clafact.db")))
    try:
        signal=hcx_detection_signal if os.environ.get("CLAFACT_HCX_MODE","fixture").lower()=="live" else None
        return import_article_file(request.path,store,hcx_signal=signal)
    finally: store.close()

@app.post("/internal/articles/upload")
def upload_article_csv(
    content: bytes = Body(...),
    x_filename: str = Header(default="articles.csv"),
) -> dict[str, object]:
    """Register an uploaded CSV through the existing article ingest boundary."""
    if not x_filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV 파일만 업로드할 수 있습니다.")
    if not content:
        raise HTTPException(status_code=400, detail="빈 CSV 파일은 등록할 수 없습니다.")

    root = Path(__file__).resolve().parents[2]
    store = Store(Path(os.environ.get("CLAFACT_SERVICE_DB", root / "data/service/clafact.db")))
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as temporary_file:
            temporary_file.write(content)
            temporary_path = Path(temporary_file.name)
        signal = hcx_detection_signal if os.environ.get("CLAFACT_HCX_MODE", "fixture").lower() == "live" else None
        return import_article_file(temporary_path, store, hcx_signal=signal)
    except (UnicodeDecodeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=f"CSV 파일을 읽을 수 없습니다: {error}") from error
    finally:
        store.close()
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
class OfficialNoticeRequest(BaseModel):
    organization: str = Field(min_length=1, max_length=120)
    url: str
    effective_date: str

@app.post("/internal/claims/{claim_id}/official-notice")
def register_official_notice(claim_id: str, request: OfficialNoticeRequest) -> dict:
    if not request.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="url must use http or https")
    root = Path(__file__).resolve().parents[2]
    store = Store(Path(os.environ.get("CLAFACT_SERVICE_DB", root / "data/service/clafact.db")))
    try:
        try:
            row = store.register_official_notice(claim_id, request.organization, request.url, request.effective_date)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="claim not found") from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {"claim_id": row["claim_id"], "label": row["label"], "reason": row["reason"], "evidence": __import__("json").loads(row["evidence_json"])}
    finally:
        store.close()
@app.get("/internal/claims/{claim_id}/official-notice")
def get_official_notice(claim_id: str) -> dict:
    root = Path(__file__).resolve().parents[2]
    store = Store(Path(os.environ.get("CLAFACT_SERVICE_DB", root / "data/service/clafact.db")))
    try:
        row = store.conn.execute("SELECT claim_id, source_type, label, reason, evidence_json FROM claims WHERE claim_id=?", (claim_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="claim not found")
        if row["source_type"] != "OFFICIAL_ANNOUNCEMENT":
            raise HTTPException(status_code=422, detail="claim is not an official announcement")
        return {"claim_id": row["claim_id"], "label": row["label"], "reason": row["reason"], "evidence": __import__("json").loads(row["evidence_json"])}
    finally:
        store.close()