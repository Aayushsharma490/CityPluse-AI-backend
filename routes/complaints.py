from fastapi import APIRouter, HTTPException
from typing import List
from models import Complaint, UpdateComplaintRequest
from db import get_db_connection

router = APIRouter()

@router.get("", response_model=List[Complaint])
def get_complaints():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM complaints ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()
    
    complaints = []
    for row in rows:
        complaints.append(Complaint(
            id=row["id"],
            text=row["text"],
            category=row["category"],
            priority_score=row["priority_score"],
            department=row["department"],
            resolution_days=row["resolution_days"],
            ward=row["ward"],
            lat=row["lat"],
            lng=row["lng"],
            timestamp=row["timestamp"],
            status=row["status"]
        ))
    return complaints

@router.post("", response_model=Complaint)
def create_complaint(complaint: Complaint):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO complaints (id, text, category, priority_score, department, resolution_days, ward, lat, lng, timestamp, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            complaint.id,
            complaint.text,
            complaint.category,
            complaint.priority_score,
            complaint.department,
            complaint.resolution_days,
            complaint.ward,
            complaint.lat,
            complaint.lng,
            complaint.timestamp,
            complaint.status
        ))
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Failed to create complaint: {e}")
    conn.close()
    return complaint

@router.get("/{complaint_id}", response_model=Complaint)
def get_complaint(complaint_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    return Complaint(
        id=row["id"],
        text=row["text"],
        category=row["category"],
        priority_score=row["priority_score"],
        department=row["department"],
        resolution_days=row["resolution_days"],
        ward=row["ward"],
        lat=row["lat"],
        lng=row["lng"],
        timestamp=row["timestamp"],
        status=row["status"]
    )

@router.patch("/{complaint_id}", response_model=Complaint)
def update_complaint(complaint_id: str, request: UpdateComplaintRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    updates = []
    params = []
    if request.status is not None:
        updates.append("status = ?")
        params.append(request.status)
        
    if request.department is not None:
        updates.append("department = ?")
        params.append(request.department)
        
    if not updates:
        conn.close()
        return get_complaint(complaint_id)
        
    params.append(complaint_id)
    try:
        cursor.execute(f"""
            UPDATE complaints
            SET {', '.join(updates)}
            WHERE id = ?
        """, tuple(params))
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Failed to update complaint: {e}")
    conn.close()
    
    return get_complaint(complaint_id)

