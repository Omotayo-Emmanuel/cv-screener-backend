
import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.matcher import compute_match
from app.services.matcher import extract_skills

test_dir = Path(__file__).parent

jd = "We need a software engineer with Python, FastAPI, and Docker. Experience with AWS is a plus."
cv = "I have 5 years of Python development, built REST APIs with FastAPI, and used Docker for containerization."

result = compute_match(jd, cv)
print(result)
# Expected output:
# {
#   'match_score': ~85-95,
#   'matched_skills': ['python', 'fastapi', 'docker'],
#   'missing_skills': ['aws'],
#   'semantic_score': ~90,
#   'keyword_overlap': 75.0
# }

jd = "We need a software engineer with Python, FastAPI, and Docker. Experience with AWS is a plus."
print(extract_skills(jd))