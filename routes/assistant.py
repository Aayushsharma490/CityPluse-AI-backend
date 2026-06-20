import os
import re
import json
import logging
from typing import Optional, Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from groq import Groq
from db import get_db_connection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class AssistantChatRequest(BaseModel):
    text: str
    language: Literal["en", "hi", "rajasthani"] = "en"

class AssistantChatResponse(BaseModel):
    reply: str
    action: Optional[str] = None
    action_data: Optional[dict] = None

# Udaipur wards list for LLM context
WARDS = [
    "Chetak Circle", "Hiran Magri", "Bhupalpura", "Sukhadia Circle", "Fateh Sagar", 
    "Ambamata", "Hathi Pol", "Surajpole", "City Station", "Sector 4", "Sector 11", 
    "Sector 14", "Mallatalai", "Shobhagpura", "Sajjan Nagar", "Goverdhan Vilas", "Panchwati"
]

def fallback_rule_based_assistant(text: str, language: str) -> dict:
    text_lower = text.lower()
    
    # 1. Check if checking status
    ticket_match = re.search(r'(udai-)?([a-z0-9]{8})', text_lower)
    if ticket_match:
        ticket_id = ticket_match.group(2)
        # Search DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM complaints WHERE LOWER(id) = ?", (ticket_id.lower(),))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            status = row["status"]
            category = row["category"]
            ward = row["ward"]
            dept = row["department"]
            if language == "hi":
                reply = f"आपकी शिकायत टिकट UDAI-{ticket_id.upper()} की स्थिति: '{status}' है। यह {ward} वार्ड में {category} श्रेणी की है और {dept} विभाग को आवंटित है।"
            elif language == "rajasthani":
                reply = f"खम्मा घणी सा! थारी शिकायत UDAI-{ticket_id.upper()} की स्थिति: '{status}' है। ओ काम {ward} वार्ड रो है और {dept} विभाग वालो काम है सा।"
            else:
                reply = f"Your complaint ticket UDAI-{ticket_id.upper()} is currently '{status}'. It is a {category} issue in {ward} ward, assigned to {dept}."
            return {"reply": reply, "action": "check_status", "action_data": {"id": ticket_id}}
            
    # 2. Check if submitting a complaint
    category = None
    if any(kw in text_lower for kw in ["pani", "water", "leak", "pipe", "drinking", "sewer", "nal", "jal"]):
        category = "Water"
    elif any(kw in text_lower for kw in ["gaddha", "road", "pothole", "divider", "pavement", "street"]):
        category = "Road"
    elif any(kw in text_lower for kw in ["bijli", "light", "electricity", "power", "transformer", "wire", "current", "pole"]):
        category = "Electricity"
    elif any(kw in text_lower for kw in ["kachra", "garbage", "safai", "drain", "clean", "waste", "toilet"]):
        category = "Sanitation"
        
    matched_ward = None
    for w in WARDS:
        if w.lower() in text_lower:
            matched_ward = w
            break
            
    if category and matched_ward:
        if language == "hi":
            reply = f"ठीक है, मैंने {matched_ward} में {category} की समस्या समझ ली है। क्या मैं आपकी शिकायत दर्ज करूँ?"
        elif language == "rajasthani":
            reply = f"खम्मा घणी! म्हे {matched_ward} में {category} री समस्या लिख लीदी है सा। शिकायत दर्ज कर दूँ का?"
        else:
            reply = f"Understood. A {category} issue in {matched_ward}. Shall I file this complaint for you?"
            
        return {
            "reply": reply,
            "action": "create_complaint",
            "action_data": {
                "category": category,
                "ward": matched_ward,
                "text": text
            }
        }
        
    # 3. General chat fallback
    if language == "hi":
        reply = "नमस्ते! मैं उदयपुर स्मार्ट सिटी का वॉइस असिस्टेंट हूँ। आप मुझसे नई शिकायत दर्ज करा सकते हैं या अपनी शिकायत की स्थिति जान सकते हैं।"
    elif language == "rajasthani":
        reply = "खम्मा घणी सा! मैं उदयपुर नगर निगम रो वॉइस असिस्टेंट हूँ। आप नयी शिकायत दर्ज करा सको हो या शिकायत रो स्टेटस पूछ सको हो सा।"
    else:
        reply = "Hello! I am the CityPulse AI voice assistant for Udaipur Municipal Corporation. You can report a new civic issue or check the status of an existing ticket."
        
    return {"reply": reply}

@router.post("/chat", response_model=AssistantChatResponse)
def assistant_chat(request: AssistantChatRequest):
    text = request.text
    language = request.language
    
    if not text or len(text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
        
    # 1. Regex check for complaint ticket ID check first to inject DB data
    ticket_match = re.search(r'(udai-)?([a-zA-Z0-9]{8})', text.lower())
    db_context = ""
    if ticket_match:
        ticket_id = ticket_match.group(2)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM complaints WHERE LOWER(id) = ?", (ticket_id.lower(),))
        row = cursor.fetchone()
        conn.close()
        if row:
            db_context = f"\n[DATABASE CONTEXT] The user is inquiring about Ticket ID 'UDAI-{ticket_id.upper()}'. Database record: status={row['status']}, category={row['category']}, ward={row['ward']}, department={row['department']}, resolution_days={row['resolution_days']}, timestamp={row['timestamp']}. Tell the user about this ticket."
            
    # 2. Call Groq if configured
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY is not configured in environment. Using fallback assistant.")
        return AssistantChatResponse(**fallback_rule_based_assistant(text, language))
        
    try:
        client = Groq(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to initialize Groq: {e}. Using fallback.")
        return AssistantChatResponse(**fallback_rule_based_assistant(text, language))
        
    system_prompt = f"""You are 'CityPulse AI Voice Assistant' for the Udaipur Municipal Corporation (smart city platform).
You listen to user voice commands and reply in the selected language: {language}.
Available languages are: 'en' (English), 'hi' (Hindi), 'rajasthani' (Rajasthani/Marwari dialect).

CRITICAL INSTRUCTIONS FOR LANGUAGES:
- If language is 'hi', reply in clean Hindi (using Devanagari script).
- If language is 'rajasthani', reply in Rajasthani (Marwari dialect using Devanagari script, starting with 'खम्मा घणी सा!' or similar polite greetings, using local vocabulary like 'म्हारे', 'थाने', 'म्हे', 'कोनी', 'सा').
- If language is 'en', reply in English.

FUNCTIONAL INSTRUCTIONS:
1. You can check ticket status. If the Database Context is provided below, explain the ticket status to the user.
2. If the user is describing a civic complaint (e.g. road pothole, leaking water pipes, streetlights out, overflowing garbage), you must return an action to create the complaint.
   - Extract the category (must be exactly: 'Road', 'Water', 'Electricity', 'Sanitation', or 'Other').
   - Extract the ward name (must match exactly one of these: {WARDS}). If the user didn't mention a ward, ask them for the ward name in a friendly voice, and do not set the action to create_complaint yet.
   - Generate a clean text description of their complaint.
   - If ward and category are found, set action='create_complaint' and fill in action_data with keys: 'category', 'ward', 'text'.
3. Keep spoken replies short and natural (1 to 3 sentences max) since they will be read by text-to-speech.

You must output ONLY valid JSON in this format:
{{
  "reply": "friendly voice response text here",
  "action": "create_complaint" or "check_status" or null,
  "action_data": {{ "category": "Water", "ward": "Fateh Sagar", "text": "water pipe leak" }} or null
}}
"""

    if db_context:
        system_prompt += db_context

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
            timeout=5.0
        )
        response_content = chat_completion.choices[0].message.content
        logger.info(f"Assistant LLM Response: {response_content}")
        parsed_data = json.loads(response_content)
        return AssistantChatResponse(
            reply=parsed_data.get("reply", ""),
            action=parsed_data.get("action"),
            action_data=parsed_data.get("action_data")
        )
    except Exception as e:
        logger.error(f"Groq assistant chat failed: {e}. Reverting to fallback.")
        return AssistantChatResponse(**fallback_rule_based_assistant(text, language))
