

from fastapi import FastAPI, UploadFile, File, Form
from typing import Optional
from fighter import run_pipeline
import tempfile
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Header, HTTPException
import os
from datetime import datetime



app = FastAPI(
    title="Fact Fighter API",
    description="Multimodal fact-checking API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/cron/ping")
async def cron_ping(x_cron_secret: str = Header(None)):
    if x_cron_secret != os.getenv("CRON_SECRET"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    print("🕒 Cron hit at:", datetime.utcnow())



    return {
        "status": "ok",
        "message": "cron alive",
        "time": datetime.utcnow().isoformat()
    }


@app.post("/fact-check")
async def fact_check(
    text: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
):
    input_data = {
        "text": text or "",
        "url": url or "",
        "image": "",
        "video": "",
        "audio": ""
    }

    # ---- Save uploaded files ----
    if image:
        with tempfile.NamedTemporaryFile(delete=False, suffix=image.filename) as tmp:
            tmp.write(await image.read())
            input_data["image"] = tmp.name

    if video:
        with tempfile.NamedTemporaryFile(delete=False, suffix=video.filename) as tmp:
            tmp.write(await video.read())
            input_data["video"] = tmp.name

    if audio:
        with tempfile.NamedTemporaryFile(delete=False, suffix=audio.filename) as tmp:
            tmp.write(await audio.read())
            input_data["audio"] = tmp.name

    # ---- Run pipeline ----
    pipeline_output = run_pipeline(input_data)

    results = []

    for _, claim_block in pipeline_output.items():
        if not isinstance(claim_block, dict):
            continue

        claim = claim_block.get("claim", "")
        gemini = claim_block.get("gemini_response", {})
        tavily_sources = claim_block.get("tavily_sources", [])

        filtered_sources = []
        for src in tavily_sources:
            text_blob = (
                (src.get("title", "") + " " + src.get("snippet", "")).lower()
            )
            if any(k in text_blob for k in claim.lower().split()[:3]):
                filtered_sources.append({
                    "title": src.get("title"),
                    "url": src.get("url")
                })

        results.append({
            "claim": claim,
            "verdict": gemini.get("verdict", "Unverifiable"),
            "confidence": gemini.get("confidence", 0.5),
            "conclusion": gemini.get("conclusion", ""),
            "sources": filtered_sources[:3]
        })

    return {
        "status": "success",
        "results": results
    }
    print(results)


