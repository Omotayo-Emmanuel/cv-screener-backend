"""
API routes for the CV Screener application.

Endpoints:
- POST /api/v1/score_cv: Accepts a job description and a CV file, processes them.
- GET /api/v1/health: Health check endpoint to verify the service is running.
"""

import email
import logging
import re
from datetime import date
from turtle import title
from turtle import title

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from sentence_transformers.util import fullname
from sentence_transformers.util import fullname

from app.services.parser import extract_text_from_bytes
from app.services.matcher import compute_match
from app.models.schemas import ScoreCVResponse, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["CV Screening"])

# 5 MB hard cap -  matches the frontend's "max 5MB" label
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = (".pdf", ".docx")

# Helpers
def _guess_seniority(cv_text:str) -> tuple[str, str]:
    """
    Very light heuristic: look for "X years" in the CV text
    Return (label, detail).

    Args:
        cv_text (str): The text extracted from the CV.

    Returns:
        tuple[str, str]: A tuple containing the seniority label and additional detail.
    """
    
    match = re.search(r"(\d+)\+?\s*(?:years|yrs)", cv_text, re.IGNORECASE)
    years = int(match.group(1)) if match else 0
    
    if years >= 8:
        return "Senior", f"{years} years of experience"
    elif years >= 4:
        return "Mid-level", f"{years} years of experience"
    elif years >= 1:
        return "Junior", f"{years} years of experience"
    return "Entry-level", f"{years} years of experience" if years > 0 else "No experience mentioned"

def _validate_upload(cv_file: UploadFile, file_bytes: bytes) -> None:
    """
    Validates the uploaded CV file for size and allowed extensions.

    Args:
        cv_file (UploadFile): The uploaded CV file.
        file_bytes (bytes): The content of the uploaded CV file.
    Raises:
        HTTPException: If the file size exceeds the limit or if the file extension is not allowed
        
    """
    name = (cv_file.filename or "").lower()
    
    if not name.endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
        
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty."
        )
    
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds the maximum limit of {MAX_FILE_SIZE / (1024 * 1024)} MB."
        )
        
# ENDPOINT
@router.post("/score-cv", response_model=ScoreCVResponse, responses={400: {"model": ErrorResponse}, 413: {"model": ErrorResponse}})
async def score_cv(
    # Required 
    job_description: str = Form(..., description="The job description text to match against the CV."),
    cv_file: UploadFile = File(..., description="The CV file to be scored."),
    
    # Optional candidates metadata from the apply form
    fullname: str = Form("", description="Full name of the candidate."),
    email: str = Form("", description="Email address of the candidate."),
    phone: str = Form("", description="Phone number of the candidate."),
    title: str = Form("", description="Current/previous job title of the candidate."),
    linkedin: str = Form("", description="LinkedIn profile URL of the candidate."),
    portfolio: str = Form("", description="Portfolio URL of the candidate."),
    info: str = Form("", description="Additional information about the candidate."),
):
    # Read and validate the uploaded CV file
    try:
        file_bytes = await cv_file.read()
    except Exception as e:
        logger.exception("Failed to read uploaded CV file")
        raise HTTPException(status_code=400, detail=f"Failed to read uploaded CV file: {e}")
    
    _validate_upload(cv_file, file_bytes)
    
    
    # Parse the CV file to extract text
    try:
        cv_text = extract_text_from_bytes(file_bytes, cv_file.filename or "")
    except ValueError as e:
        logger.exception("Failed to parse CV file")
        raise HTTPException(status_code=400, detail=f"Failed to parse CV file: {e}")
    
    # SCORE the CV against the job description
    try:
        seniority_label, seniority_detail = _guess_seniority(cv_text)

        candidate_meta = {
            "name":      fullname.strip(),
            "role":      title.strip(),      # "current/previous job title" → role
            "jobTitle":  "",                 # MVP: not available on apply form
            "appliedOn": date.today().strftime("%B %d, %Y"),
        }

        result = compute_match(
            cv_text=cv_text,
            job_description=job_description,
            candidate_meta=candidate_meta,
        )

        # Fill in seniority — compute_match leaves it blank by design
        result["candidate"]["seniority"] = seniority_label
        result["candidate"]["seniorityDetail"] = seniority_detail

        return result

    except Exception as e:
        logger.exception("Scoring failed")
        raise HTTPException(status_code=500, detail=f"Scoring failed: {e}")


@router.get("/health")
async def health():
    return {"status": "ok"}
