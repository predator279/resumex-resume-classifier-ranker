"""
main.py — FastAPI application entry point.

Endpoints:
  GET  /health      — liveness check
  POST /classify    — BERT top-5 category classification
  POST /parse-jd    — Auto-extract requirements from free-form JD text
  POST /rank        — 5-dimension ATS ranking
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from .models_loader import load_all_models, models_are_loaded
from .classifier import classify_resume
from .jd_parser import parse_jd
from .ranker import rank_resumes

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== ResumeX startup: loading models ===")
    load_all_models()
    logger.info("=== ResumeX ready ===")
    yield
    logger.info("=== ResumeX shutdown ===")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="ResumeX API",
    description="Resume classifier and ATS ranker powered by BERT + MiniLM",
    version="2.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Static files (frontend SPA)
# ---------------------------------------------------------------------------
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def serve_frontend():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse({"message": "ResumeX API — frontend not found."})


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "models_loaded": models_are_loaded()}


# ---------------------------------------------------------------------------
# /classify
# ---------------------------------------------------------------------------
@app.post("/classify")
async def classify(file: UploadFile = File(...)):
    """Classify a single resume. Returns top-5 job categories."""
    allowed = {"pdf", "docx", "doc", "txt"}
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in allowed:
        raise HTTPException(400, f"Unsupported file type '{ext}'. Allowed: {allowed}")

    data = await file.read()
    if not data:
        raise HTTPException(400, "Uploaded file is empty.")

    try:
        return classify_resume(file.filename, data)
    except Exception as e:
        logger.exception("Classify error for '%s'", file.filename)
        raise HTTPException(500, str(e))


# ---------------------------------------------------------------------------
# /parse-jd
# ---------------------------------------------------------------------------
class ParseJDRequest(BaseModel):
    jd_text: str


@app.post("/parse-jd")
async def parse_jd_endpoint(req: ParseJDRequest):
    """
    Auto-extract structured requirements from a free-form job description.

    Returns:
        skills            : list of tech skill strings
        experience_years  : integer or null
        education         : degree label string or null
        seniority         : seniority level string or null
    """
    if not req.jd_text.strip():
        raise HTTPException(400, "jd_text cannot be empty.")

    try:
        result = parse_jd(req.jd_text)
        return result
    except Exception as e:
        logger.exception("JD parse error")
        raise HTTPException(500, str(e))


# ---------------------------------------------------------------------------
# /rank
# ---------------------------------------------------------------------------
@app.post("/rank")
async def rank(
    resumes: list[UploadFile] = File(...),
    jd_text: str = Form(default=""),

    # Optional user overrides (pre-filled from /parse-jd, editable on frontend)
    skills_override: str = Form(default=""),       # comma-separated
    experience_override: str = Form(default=""),   # numeric string e.g. "5"
    education_override: str = Form(default=""),    # e.g. "Bachelors"
    seniority_override: str = Form(default=""),    # e.g. "Senior"
):
    """
    Rank multiple resumes against a job description.

    Mode C flow:
    1. Frontend sends jd_text (full JD) for semantic embedding.
    2. Frontend also sends the auto-extracted/user-edited structured fields
       as *_override params.
    3. Backend uses overrides for structured scoring, jd_text for semantic.
    """
    if not resumes:
        raise HTTPException(400, "No resumes uploaded.")

    if not jd_text.strip() and not skills_override.strip():
        raise HTTPException(400, "Provide either a job description or at least required skills.")

    # Parse structured fields from overrides
    required_skills: list[str] = [
        s.strip() for s in skills_override.split(",") if s.strip()
    ]

    required_years: Optional[int] = None
    if experience_override.strip():
        try:
            required_years = int(float(experience_override.strip()))
        except ValueError:
            pass

    required_education: Optional[str] = education_override.strip() or None
    required_seniority: Optional[str] = seniority_override.strip() or None

    # If no overrides yet (user skipped parse step), auto-parse from jd_text
    if jd_text.strip() and not required_skills:
        parsed = parse_jd(jd_text)
        required_skills   = parsed["skills"]
        if required_years is None:
            required_years = parsed["experience_years"]
        if required_education is None:
            required_education = parsed["education"]
        if required_seniority is None:
            required_seniority = parsed["seniority"]

    # Read uploaded files
    allowed = {"pdf", "docx", "doc", "txt"}
    files = []
    for upload in resumes:
        ext = (upload.filename or "").rsplit(".", 1)[-1].lower()
        if ext not in allowed:
            raise HTTPException(400, f"Unsupported type '{ext}' for '{upload.filename}'.")
        raw = await upload.read()
        if raw:
            files.append((upload.filename, raw))

    if not files:
        raise HTTPException(400, "All uploaded files are empty.")

    try:
        result = rank_resumes(
            files=files,
            jd_text=jd_text,
            required_skills=required_skills,
            required_years=required_years,
            required_education=required_education,
            required_seniority=required_seniority,
        )
        # Surface the effective requirements back to the client
        result["effective_requirements"] = {
            "skills":      required_skills,
            "experience":  required_years,
            "education":   required_education,
            "seniority":   required_seniority,
        }
        return result
    except Exception as e:
        logger.exception("Rank error")
        raise HTTPException(500, str(e))
