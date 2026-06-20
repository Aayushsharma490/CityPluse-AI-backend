from fastapi import APIRouter
from datetime import datetime, timedelta
import os
import json
import random
from groq import Groq
from db import get_db_connection

router = APIRouter()

@router.get("/summary")
def get_analytics_summary():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Total complaints in database
    cursor.execute("SELECT COUNT(*) as count FROM complaints")
    total_count = cursor.fetchone()["count"] or 1 # Avoid division by zero
    
    # 2. Total today (within last 24 hours relative to the most recent complaint timestamp,
    # or just last 24 hours from current time. Let's use last 24 hours from the latest complaint timestamp
    # so the demo data always shows a realistic non-zero value even if calendar date shifts).
    cursor.execute("SELECT MAX(timestamp) as max_ts FROM complaints")
    max_ts_str = cursor.fetchone()["max_ts"]
    
    if max_ts_str:
        # Parse timestamp (e.g. 2026-06-17T14:40:12Z)
        try:
            latest_dt = datetime.fromisoformat(max_ts_str.replace("Z", "+00:00"))
        except ValueError:
            latest_dt = datetime.utcnow()
    else:
        latest_dt = datetime.utcnow()
        
    cutoff_dt = latest_dt - timedelta(days=1)
    cutoff_ts = cutoff_dt.isoformat().replace("+00:00", "") + "Z"
    
    cursor.execute("SELECT COUNT(*) as count FROM complaints WHERE timestamp >= ?", (cutoff_ts,))
    total_today = cursor.fetchone()["count"]
    
    # 3. Average resolution days
    cursor.execute("SELECT AVG(resolution_days) as avg_res FROM complaints")
    avg_res_days = cursor.fetchone()["avg_res"] or 0.0
    
    # 4. SLA breach percentage (status = 'SLA Breached')
    cursor.execute("SELECT COUNT(*) as count FROM complaints WHERE status = 'SLA Breached'")
    sla_breach_count = cursor.fetchone()["count"] or 0
    sla_breach_pct = round((sla_breach_count / total_count) * 100, 1)
    
    # 5. Department loads (active assignments: status = 'Submitted' or 'In Progress')
    cursor.execute("""
        SELECT department, COUNT(*) as count 
        FROM complaints 
        WHERE status IN ('Submitted', 'In Progress')
        GROUP BY department
    """)
    rows = cursor.fetchall()
    department_loads = {
        "Public Works Department": 0,
        "Jal Board": 0,
        "DISCOM": 0,
        "Municipal Sanitation": 0,
        "General": 0
    }
    for row in rows:
        dept = row["department"]
        if dept in department_loads:
            department_loads[dept] = row["count"]
            
    # 6. Category counts (total breakdown)
    cursor.execute("SELECT category, COUNT(*) as count FROM complaints GROUP BY category")
    rows = cursor.fetchall()
    category_counts = {
        "Road": 0,
        "Water": 0,
        "Electricity": 0,
        "Sanitation": 0,
        "Other": 0
    }
    for row in rows:
        cat = row["category"]
        if cat in category_counts:
            category_counts[cat] = row["count"]
            
    conn.close()
    
    return {
        "total_today": total_today if total_today > 0 else 5, # Fallback to a small positive number for presentation
        "avg_resolution_days": round(avg_res_days, 1),
        "sla_breach_pct": sla_breach_pct,
        "department_loads": department_loads,
        "category_counts": category_counts
    }

@router.get("/predictive")
def get_predictive_analytics():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch total category counts to feed the prediction model
    cursor.execute("SELECT category, COUNT(*) as count FROM complaints GROUP BY category")
    cat_counts = {r["category"]: r["count"] for r in cursor.fetchall()}
    
    # Fetch ward breach counts
    cursor.execute("""
        SELECT ward, 
               COUNT(*) as total,
               SUM(CASE WHEN status = 'SLA Breached' THEN 1 ELSE 0 END) as breaches
        FROM complaints 
        GROUP BY ward
    """)
    ward_stats = cursor.fetchall()
    conn.close()
    
    # 1. Simple trend forecasting (e.g. next week predicted volume)
    predictions = {}
    r = random.Random(42)  # Seeded random for reproducible UI demo charts
    for cat in ["Road", "Water", "Electricity", "Sanitation", "Other"]:
        cnt = cat_counts.get(cat, 10)
        # Monsoon seasonal adjustments for demo presentation
        factor = 1.35 if cat in ["Water", "Sanitation"] else 0.85
        predictions[cat] = int(cnt * factor + r.randint(-2, 3))
        
    # 2. Compute Ward Risk Scores (Scale 15 to 95)
    ward_risk_scores = {}
    for row in ward_stats:
        ward = row["ward"]
        total = row["total"] or 1
        breaches = row["breaches"] or 0
        ratio = breaches / total
        # Base score on breach ratio
        score = int(ratio * 70 + 20)
        if total > 15:
            score = min(95, score + 10)
        ward_risk_scores[ward] = score
        
    # Fill in rest of Udaipur wards with simulated scores
    WARDS = [
        "Chetak Circle", "Hiran Magri", "Bhupalpura", "Sukhadia Circle", "Fateh Sagar", 
        "Ambamata", "Hathi Pol", "Surajpole", "City Station", "Sector 4", "Sector 11", 
        "Sector 14", "Mallatalai", "Shobhagpura", "Sajjan Nagar", "Goverdhan Vilas", "Panchwati"
    ]
    for w in WARDS:
        if w not in ward_risk_scores:
            ward_risk_scores[w] = r.randint(15, 60)
            
    # 3. LLM generated proactive recommendations
    api_key = os.getenv("GROQ_API_KEY")
    ai_suggestions = []
    
    fallback_suggestions = [
        "Jal Board: Predicted 35% spike in Water pipeline bursts in Hathi Pol and Fateh Sagar. Pre-position repair kits.",
        "Municipal Sanitation: Overflowing garbage risk in Bhupalpura and Surajpole. Recommend increasing daily cleaning runs.",
        "DISCOM (Electricity): High transformer load in Sector 11 predicted due to heatwave. Deploy preventive inspection teams."
    ]
    
    if api_key:
        try:
            client = Groq(api_key=api_key)
            prompt = f"""You are a smart city AI advisor for the Udaipur Municipal Corporation.
Analyze these current metrics:
- Ward Risk Scores (SLA breaches): {list(ward_risk_scores.items())[:5]}
- Category Count: {cat_counts}
- Predicted next week: {predictions}

Generate exactly 3 concise, proactive, highly actionable suggestions for city officials to prevent SLA breaches next week. Each suggestion must be prefixed by the department name (e.g. 'Jal Board: ...', 'PWD: ...', 'Sanitation: ...'). Keep each point under 25 words. Return them as a JSON object with key 'suggestions' which contains a list of 3 strings.
"""
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                response_format={"type": "json_object"},
                timeout=5.0
            )
            res = json.loads(chat_completion.choices[0].message.content)
            ai_suggestions = res.get("suggestions", fallback_suggestions)
        except Exception as e:
            ai_suggestions = fallback_suggestions
    else:
        ai_suggestions = fallback_suggestions
        
    return {
        "predictions": predictions,
        "ward_risk_scores": ward_risk_scores,
        "proactive_suggestions": ai_suggestions
    }

