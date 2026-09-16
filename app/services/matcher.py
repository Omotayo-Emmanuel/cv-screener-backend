"""
 Matcher Service for the CV scoring

Uses:
- spaCy for skill extraction (noun phrases + named entities + custom keyword list)
- sentence-transformers for semantic similarity scoring (embedding-based)
- Combines both into a final match score 0-100

Dependencies:
- spaCy (with en_core_web_sm model)
- sentence-transformers
- scikit-learn (for cosine similarity)

"""

import logging
import functools
import json
from pathlib import Path
from typing import List, Tuple, Dict, Any, Set, Optional
from collections import defaultdict

import spacy
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# Load spaCy model and sentence-transformers model
try:
    nlp = spacy.load("en_core_web_sm")
    logger.info("spaCy model 'en_core_web_sm' loaded successfully.")
except OSError:
    raise RuntimeError(
        """
        spaCy model 'en_core_web_sm' not found.
        Please install it using the following command:
            python -m spacy download en_core_web_sm
        """
    )
    
try:
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    logger.info("SentenceTransformer model 'all-MiniLM-L6-v2' loaded successfully.")
except Exception as e:
    raise RuntimeError(f"Failed to load SentenceTransformer model: {e}")


# Load Skill List from File
def _load_skill_set(file_path: Optional[str] = None) -> Set[str]:
    """
    Load skills from a JSON file.
    If file_path is None, looks for "app/data/skills.json".
    Falls back to a minimal defual set if file is missing.
    
    """
    if file_path is None:
        # Defualt path
        current_dir = Path(__file__).parent # app/services
        project_root = current_dir.parent # app/
        file_path = project_root / "data" / "skills.json"
    
    try:
        with open(file_path, "r", encoding = "utf-8") as f:
            data = json.load(f)
            skills = set(data.get("skills", []))
            if not skills:
                logger.warning(f"Skill file {file_path} exists but 'skills' key is empty. Using default skill set.")
                
                return _get_fallback_skills()
            
            #Convert to lowercase set for case insensitive matching
            skill_set = {skill.lower().strip() for skill in skills if skill.strip()}
            logger.info(f"Loaded {len(skill_set)} skills from {file_path}.")
            return skill_set
    except FileNotFoundError:
        logger.warning(f"Skill file {file_path} not found. Using default skill set.")
        return _get_fallback_skills()
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in skill file {file_path}: {e}. Using default skill set.")
        return _get_fallback_skills()

def _get_fallback_skills() -> Set[str]:
    """
    Returns a minimal default set of skills if the skill file is missing or invalid.
    """
    fallback_skills = {
        "python", "java", "c++", "javascript", "sql", "html", "css",
        "machine learning", "data analysis", "project management",
        "communication", "teamwork"
    }
    logger.info(f"Using fallback skill set with {len(fallback_skills)} skills.")
    return fallback_skills

# Load the skill set at module load time
DEFAULT_SKILL_SET = _load_skill_set()

# Caching for performance optimization
@functools.lru_cache(maxsize=128)
def _get_embedding(text: str) -> np.ndarray:
    """
    Get the embedding for a given text using the sentence-transformers model.
    Caches results to improve performance on repeated calls.
    """
    return embedding_model.encode(text, normalize_embeddings=True) # L2 more for cosine

# SKILL EXTRACTION FUNCTIONS
def  extract_skills(text: str, skill_set: Set[str] = None) -> List[str]:
    """
    Extract skills from the given text using spaCy and a controlled vocabulary.
    
    Strategy:
    1. Lowercase the text and process with spacy.
    2. Look at noun chunks and named entities (e.g., " machine learning", "project management").
    3. Look at individual token that match knows skills (lemmatised).
    4. Also include proper nouns that resemble product/technology names (e.g., "AWS", "Docker").
    
    Args:
        text (str): The input text (e.g., CV or job description).
        skill_set (Set[str]):  Optional set of known skill strings (case-insensitive).
                                If None, uses DEFAULT_SKILL_SET.
        
    Returns:
        List[str]: A list of extracted skills found in the text.
    """
    if skill_set is None:
        skill_set = DEFAULT_SKILL_SET

    # Normalize skill set to lowercase for case-insensitive matching
    skill_set_lower = {skill.lower() for skill in skill_set}
    
    doc = nlp(text)
    found_skills = set()
    
    
    # Noun chucks which often contains multi-word skills ( e.g., "machine learning", "project management")
    for chunk in doc.noun_chunks:
        chunk_text = chunk.text.lower().strip()
        # Only take chunks that are reasonably short and not generic
        if 1 <= len(chunk_text.split()) <= 4:
            # If chunk is a known skill, add it
            if chunk_text in skill_set_lower:
                found_skills.add(chunk_text)
            
            # ALso add if it's a proper noun and likely a skill (e.g., "AWS", "Docker")
            elif chunk.root.ent_type_ in {"ORG", "PRODUCT", "TECHNOLOGY"}:
                # Example: "React" -> prooduct; we might want to include it .
                # But to avoid over-inclusions, only add if the lemma is also in skill_set
                # Or just add all proper nouns? We'll add if the chunk root lemma is also in skill_set?
                # Let's check if the chunk's lemma (root)is in the skill set
                
                root_lemma = chunk.root.lemma_.lower()
                if root_lemma in skill_set_lower:
                    found_skills.add(chunk_text)
                # Also add if the chunk_text itself matches any skill (e.g., "AWS" vs "aws")
                
                if chunk_text in skill_set_lower:
                    found_skills.add(chunk_text)
                    
    # Individual tokens - catch single-word skills like "Python", "SQL", "Docker"
    for token in doc:
        if token.is_stop or token.is_punct:
            continue
        lemma = token.lemma_.lower() # Lemmatize to match skill set
        if lemma in skill_set_lower or token.text.lower() in skill_set_lower:
            found_skills.add(token.text.lower())    # keep original casing for output, but store in lowercase for consistency
            
    
    # Return sorted list for consistency
    return sorted(found_skills)


#   SEMANTIC SIMILARITY
def compute_semantic_similarity(text1: str, text2: str) -> float:
    """
    Compute the semantic similarity between two texts using sentence-transformers embeddings.
    
    Args:
        text1 (str): First text (e.g., CV).
        text2 (str): Second text (e.g., job description).
        
    Returns:
        float: Cosine similarity score between 0 and 1.
    """
    emb1 = _get_embedding(text1)
    emb2 = _get_embedding(text2)
    
    # Both are L2-normalized, so dot product = cosine similarity
    # Compute cosine similarity
    similarity = np.dot(emb1, emb2)
    # Clamp similarity to [0, 1] range in case of numerical issues
    return float(np.clip(similarity, 0.0, 1.0))



# Combined Scoring
def compute_match(
    cv_text: str,
    job_description: str,
    skill_set: Set[str] = None,
    keyword_weight: float = 0.3, # Weight for the skill match score (0-1).
    semantic_weight: float = 0.7 # Higher weight for semantic similarity
) -> Dict[str, Any]:
    """
    Compute a combined match score between a CV and a job description.
    
    Args:
        cv_text (str): The text of the CV.
        job_description (str): The text of the job description.
        skill_set (Set[str]): Optional set of known skills for extraction.
        keyword_weight (float): Weight for the keyword match score (0-1).
        semantic_weight (float): Weight for the semantic similarity score (0-1).
    
    Returns:
        Dict[str, Any]: A dictionary containing:
            - match_score: Final combined score (0-100).
            - matched_skills: List of skills found in both CV and job description.
            - missing_skills: List of skills in job description but not in CV.
            - Semantic similarity score (0-100) for debugging purposes.
            - keyword match score (0-100) for debugging purposes.
            
    """
    
    # Extract skills from both CV and job description
    cv_skills = set(extract_skills(cv_text, skill_set))
    jd_skills = set(extract_skills(job_description, skill_set))
    
    matched = list(jd_skills.intersection(cv_skills))
    missing = list(jd_skills.difference(cv_skills))
    
    # Compute keyword semantic similarity score (0-1)
    semantic_score = compute_semantic_similarity(job_description, cv_text)
    
    # Compute keyword overlap (0-1) - ratio of JD skills found in CV
    if jd_skills:
        keyword_overlap = len(matched) / len(jd_skills)
    else:keyword_overlap = 0.0
    
    # Combine Scores
    # Weighted average: semantic_weight * semanic_score + keyword_weight * keyword_overlap
    combined = (semantic_weight * semantic_score) + (keyword_weight * keyword_overlap)
    match_score = round(combined * 100, 2) # Scale to 0-100 and round to 2 decimal places
    
    return {
        "match_score": match_score,
        "matched_skills": matched,
        "missing_skills": missing,
        "semantic_similarity_score": round(semantic_score * 100, 2), # for transparency/debugging
        "keyword_match_score": round(keyword_overlap * 100, 2) # for transparency/debugging
    }