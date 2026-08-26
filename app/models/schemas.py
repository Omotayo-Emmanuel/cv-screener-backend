from pydantic import BaseModel, Field
from typing import Optional, List

# Request Models
class ScoreCVRequest(BaseModel):
    """
    Optional JSON request body (if you ever switch from from-data to JSON).
    For now, the edpoint uses Frorm (...) so thisis just for documentation/fallback.

    Args:
        BaseModel (pydantic.BaseModel): Defines the schema for the request payload,
        including validation and type enforcement for the fields.
    """
    
    job_description: str = Field(..., description="The job description text for scoring the CV.")
    cv_text: str = Field(..., description="The CV text to be scored against the job description.")
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_description": "We are looking for a skilled software engineer with experience in Python and machine learning.",
                "cv_text": "John Doe is a software engineer with 5 years of experience in Python, data analysis, and machine learning."
            }
        }
        
# Response Models
class ScoreCVResponse(BaseModel):
    """
    Response model for the CV scoring endpoint.

    Args:
        BaseModel (pydantic.BaseModel): Defines the schema for the response payload,
        including validation and type enforcement for the fields.
    """
    match_score: float = Field(
        ..., 
        ge = 0.0,
        le = 100.0,
       description="The match score between the job description and the CV text."
       )
    
    matched_skills: Optional[List[str]] = Field(
        ...,
        description="A list of skills that were matched between the job description and the CV text."
    )
    
    missing_skills: Optional[List[str]] = Field(
        ...,
        description="A list of skills that were mentioned in the job description but not found in the CV text."
    )
    
    error: Optional[str] = Field(
        None,
        description="An optional error message if the scoring process encountered an issue."
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "match_score": 87.5,
                "matched_skills": ["Python", "Machine Learning"],
                "missing_skills": ["Data Analysis"],
                "error": None
            }
        }

# Error Response Model (For consistency in error handling)
class ErrorResponse(BaseModel):
    """
    Standardized error response model for API endpoints.

    Args:
        BaseModel (pydantic.BaseModel): Defines the schema for the error response payload,
        including validation and type enforcement for the fields.
    """
    details: str = Field(..., description="A detailed error message describing the issue.")
    status_code: int = Field(..., description="The HTTP status code associated with the error.")
    
    class Config:
        json_schema_extra = {
            "example": {
                "details": "PDF parsing failed: file is corrupted.",
                "status_code": 400
            }
        }
    