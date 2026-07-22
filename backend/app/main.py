from fastapi import FastAPI


app = FastAPI(
    title="ClaFact API",
    version="0.1.0",
    description="Evidence-backed Korean news claim verification service.",
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"service": "clafact-api", "status": "ok"}
