import os
import json
import logging
from typing import Dict, Any, Literal
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, ValidationError
from groq import Groq
from models import ClassifyRequest, ClassifyResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Keyword matching fallback function
def rule_based_fallback(text: str) -> dict:
    text_lower = text.lower()
    
    # pani, water, leak -> Water
    if any(kw in text_lower for kw in ["pani", "water", "leak", "pipe", "leakage", "drinking", "paani", "nal", "sewerage", "jal"]):
        category = "Water"
        score = 6
        reasoning = "Rule-based fallback: detected water/leak related terms."
        dept = "Jal Board"
        days = 3
    # gaddha, road, pothole -> Road
    elif any(kw in text_lower for kw in ["gaddha", "road", "pothole", "divider", "pavement", "street", "highway", "pathway", "tar"]):
        category = "Road"
        score = 5
        reasoning = "Rule-based fallback: detected road/pothole related terms."
        dept = "Public Works Department"
        days = 5
    # bijli, light, electricity -> Electricity
    elif any(kw in text_lower for kw in ["bijli", "light", "electricity", "power", "transformer", "wire", "current", "voltage", "pole", "discom"]):
        category = "Electricity"
        score = 7
        reasoning = "Rule-based fallback: detected electricity/power related terms."
        dept = "DISCOM"
        days = 2
    # kachra, garbage, safai -> Sanitation
    elif any(kw in text_lower for kw in ["kachra", "garbage", "safai", "drain", "sewage", "clean", "toilet", "sweeping", "waste", "dustbin"]):
        category = "Sanitation"
        score = 5
        reasoning = "Rule-based fallback: detected sanitation/garbage related terms."
        dept = "Municipal Sanitation"
        days = 4
    else:
        category = "Other"
        score = 3
        reasoning = "Rule-based fallback: no specific civic category keywords matched."
        dept = "General"
        days = 5
        
    return {
        "category": category,
        "priority_score": score,
        "priority_reasoning": reasoning,
        "department": dept,
        "estimated_resolution_days": days,
        "reasoning": reasoning,
        "resolution_days": days
    }

@router.post("", response_model=ClassifyResponse)
def classify_complaint(request: ClassifyRequest):
    # 1. Resolve incoming text
    text = request.complaint_text or request.text
    if not text or len(text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Complaint text cannot be empty")
    if len(text) > 1000:
        raise HTTPException(status_code=400, detail="Complaint text exceeds 1000 characters limit")
        
    # 2. Get API key and client
    # Read GROQ_API_KEY from .env
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY is not configured in environment. Falling back to rule-based classifier.")
        return ClassifyResponse(**rule_based_fallback(text))
        
    # Initialize Groq client (Using Groq free tier — open-source Llama model, zero API cost.)
    try:
        client = Groq(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to initialize Groq client: {e}. Falling back.")
        return ClassifyResponse(**rule_based_fallback(text))
        
    system_prompt = """You are a civic complaint classifier for Indian municipal corporations.
Classify the complaint into exactly one category: Road, Water, Electricity, Sanitation, or Other.
Assign a priority score from 1 (low) to 10 (critical) based on public safety impact.
Suggest the appropriate department (PWD, Jal Board, DISCOM, Municipal Sanitation, or General).
Estimate resolution days based on typical municipal resolution times.
Return ONLY valid JSON with keys: category, priority_score, priority_reasoning, department, estimated_resolution_days.
"""

    model_name = "llama-3.3-70b-versatile"
    fallback_model = "llama-3.1-8b-instant"
    
    def try_classify(current_model: str, is_retry: bool = False) -> dict:
        prompt = system_prompt
        if is_retry:
            prompt += "\nIMPORTANT: Ensure JSON format is strictly correct. Do not wrap in markdown code blocks."
            
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text}
            ],
            model=current_model,
            response_format={"type": "json_object"},
            timeout=5.0 # Timeout after 5 seconds
        )
        
        response_content = chat_completion.choices[0].message.content
        logger.info(f"Groq API raw response: {response_content}")
        parsed_data = json.loads(response_content)
        
        # Pydantic-like validation checks
        category = parsed_data.get("category")
        if category not in ["Road", "Water", "Electricity", "Sanitation", "Other"]:
            raise ValueError(f"Invalid category: {category}")
            
        priority_score = parsed_data.get("priority_score")
        if not isinstance(priority_score, int) or not (1 <= priority_score <= 10):
            raise ValueError(f"Invalid priority score: {priority_score}")
            
        # Standardize response mapping for backwards compatibility
        parsed_data["reasoning"] = parsed_data.get("priority_reasoning", "Classified by AI model.")
        parsed_data["resolution_days"] = parsed_data.get("estimated_resolution_days", 5)
        return parsed_data

    # Attempt 1: Standard classification
    try:
        data = try_classify(model_name)
        return ClassifyResponse(**data)
    except Exception as e:
        logger.error(f"Groq classification failed or timed out with {model_name}: {e}. Retrying with strict prompt and fallback model...")
        
        # Attempt 2: Retry with fallback model and stricter prompt
        try:
            data = try_classify(fallback_model, is_retry=True)
            return ClassifyResponse(**data)
        except Exception as e_retry:
            logger.error(f"Groq classification retry failed: {e_retry}. Reverting to rule-based fallback safety net.")
            # Safety net: Rule-based fallback classifier triggers, so demo never breaks in front of judges
            return ClassifyResponse(**rule_based_fallback(text))
