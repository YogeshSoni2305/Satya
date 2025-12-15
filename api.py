from fastapi import FastAPI, UploadFile, File, Form
from typing import Optional
from fighter import run_pipeline
import tempfile
import os
from fastapi.middleware.cors import CORSMiddleware



app = FastAPI(
    title="Fact Fighter API",
    description="Multimodal fact-checking API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # or "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
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

        # ---- FILTER RELEVANT SOURCES ONLY ----
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






