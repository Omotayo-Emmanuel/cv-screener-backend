from pydantic import BaseModel, ConfigDict, Field
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

class CandidateInfo(BaseModel):
    """
    Data model representing information about a job candidate.

    This class is built on Pydantic's BaseModel to provide validation,
    serialization, and alias support for candidate-related fields. It
    captures key details about a candidate's application, evaluation,
    and professional background.

    Attributes:
        name (str): Candidate's full name. Defaults to an empty string.
        role (str): The role or position the candidate is applying for.
        jobTitle (str): Candidate's current or most recent job title.
            Uses an alias "jobTitle" for external data mapping.
        appliedOn (str): Date when the candidate applied for the role,
            typically in ISO 8601 format (YYYY-MM-DD).
        overallScore (float): Numerical score representing the candidate's
            overall evaluation or assessment. Defaults to 0.0.
        skillsFound (int): Number of relevant skills identified in the
            candidate's profile or resume.
        skillsTotal (int): Total number of skills expected or required
            for the role.
        seniority (str): General seniority level of the candidate
            (e.g., "Junior", "Mid-level", "Senior").
        seniorityDetail (str): Additional descriptive detail about the
            candidate's seniority (e.g., "5 years of experience in
            software engineering").
    """
    model_config = ConfigDict(populate_by_name=True)
    
    name: str = ""
    role: str = ""
    jobTitle: str = Field(default="", alias="jobTitle")
    appliedOn: str = ""
    overallScore: float = 0.0
    skillsFound: int = 0
    skillsTotal: int = 0
    seniority: str = ""
    seniorityDetail: str = ""

class SkillCoverageItem(BaseModel):
    """_summary_

    Args:
        BaseModel (_type_): _description_
    """
    name: str
    value: float
    color: str

class CategoryScore(BaseModel):
    """
    Data model representing a score for a specific category.

    This class is built on Pydantic's BaseModel to provide validation,
    serialization, and alias support for category score-related fields.
    It captures the name of the category and its associated score.

    Attributes:
        category (str): The name of the category being scored.
        score (float): The numerical score associated with the category.
    """
    category: str
    score: float
    
class KeywordDensityItem(BaseModel):
    """
    Data model representing the density of a specific keyword.

    This class is built on Pydantic's BaseModel to provide validation,
    serialization, and alias support for keyword density-related fields.
    It captures the keyword and its associated density value.

    Attributes:
        keyword (str): The specific keyword being analyzed.
        jobDescription (int): The number of times the keyword appears in the job description.
        cv (int): The number of times the keyword appears in the CV.
    """
    keyword: str
    jobDescription: int
    cv: int

# Response Models
class ScoreCVResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    candidate: CandidateInfo
    skillCoverage: List[SkillCoverageItem] = []
    categoryBreakdown: List[CategoryScore] = []
    keywordDensity: List[KeywordDensityItem] = []
    matchedSkills: List[str] = []
    missingSkills: List[str] = []
    strengths: List[str] = []
    gaps: List[str] = []
    jobDescriptionKeywords: List[str] = []
    parsedResume: str = ""
    error: Optional[str] = None

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
    