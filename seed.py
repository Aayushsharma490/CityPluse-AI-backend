import os
import json
import random
import uuid
from datetime import datetime, timedelta
from db import init_db, get_db_connection

# Define Udaipur wards and their coordinates
WARDS = [
    {"name": "Chetak Circle", "lat": 24.5937, "lng": 73.6934},
    {"name": "Hiran Magri", "lat": 24.5684, "lng": 73.7144},
    {"name": "Bhupalpura", "lat": 24.5945, "lng": 73.7088},
    {"name": "Sukhadia Circle", "lat": 24.6033, "lng": 73.6922},
    {"name": "Fateh Sagar", "lat": 24.5982, "lng": 73.6828},
    {"name": "Ambamata", "lat": 24.5919, "lng": 73.6745},
    {"name": "Hathi Pol", "lat": 24.5878, "lng": 73.6875},
    {"name": "Surajpole", "lat": 24.5815, "lng": 73.7001},
    {"name": "City Station", "lat": 24.5712, "lng": 73.6985},
    {"name": "Sector 4", "lat": 24.5631, "lng": 73.7224},
    {"name": "Sector 11", "lat": 24.5550, "lng": 73.7202},
    {"name": "Sector 14", "lat": 24.5450, "lng": 73.7180},
    {"name": "Mallatalai", "lat": 24.5902, "lng": 73.6655},
    {"name": "Shobhagpura", "lat": 24.6135, "lng": 73.7092},
    {"name": "Sajjan Nagar", "lat": 24.5824, "lng": 73.6601},
    {"name": "Goverdhan Vilas", "lat": 24.5501, "lng": 73.6902},
    {"name": "Panchwati", "lat": 24.6012, "lng": 73.6995}
]

TEMPLATES = {
    "Road": [
        "Huge pothole near {} main intersection causing severe traffic delay and vehicle damage.",
        "Water logging on the road in {} has completely ruined the asphalt surface.",
        "Deep crater in middle of the road near {}, dangerous for two-wheelers at night.",
        "Broken road divider at {} is causing accidents during peak hours.",
        "Pedestrian pavement collapsed near {}, blocking the walking pathway.",
        "Unmarked and excessively high speed breaker near {} is causing vehicles to scrape.",
        "Caved-in road surface due to recent construction near {} is blocked by stones.",
        "Road gravel has come loose on the main lane in {}, causing skidding hazards."
    ],
    "Water": [
        "No water supply for the past three consecutive days in {}.",
        "Muddy and foul-smelling drinking water flowing out of municipal pipes in {}.",
        "Major pipeline leak near {} is wasting thousands of liters of drinking water.",
        "Extremely low pressure water supply in {}, unable to fill ground level tanks.",
        "Water leakage from municipal main control valve near {}.",
        "Contaminated water mixing with municipal supply line near {}.",
        "Water supply timings are extremely irregular in {} without prior warning.",
        "Municipal water tanker failed to arrive in {} despite advance booking."
    ],
    "Electricity": [
        "Frequent power cuts and high voltage fluctuations in {}.",
        "Streetlight out of order near {}, making the street completely pitch black.",
        "Loose overhead electric cables hanging dangerously low near {} market.",
        "Transformer burst near {} has disrupted electrical supply for over 6 hours.",
        "Electric utility pole hit by a vehicle near {} is leaning over the road.",
        "Voltage spikes in {} are damaging household electronics regularly.",
        "Sparking from power lines near {} during strong winds, risk of fire.",
        "Municipal park lights are not functional in {}, unsafe for evening walkers."
    ],
    "Sanitation": [
        "Large garbage dump left uncollected for five days near {} commercial block.",
        "Open drainage line overflowing and flooding the walkway in {}.",
        "Public toilet facility near {} has no running water and is highly unhygienic.",
        "Construction waste illegally dumped on the roadside in {}.",
        "Carcass of a stray dog lying on the street in {}, spreading terrible stench.",
        "Sewage backflow in residential lanes of {} due to clogged main lines.",
        "Municipal sweeping workers have not cleaned the roads in {} for a week.",
        "Dustbins provided by corporation are overflowing near {} without clearing."
    ],
    "Other": [
        "Stray cattle blockading traffic on the main road of {} daily.",
        "Illegal commercial hoarding blocking traffic signals near {}.",
        "Severe noise pollution from public speakers playing past midnight in {}.",
        "Encroachment of pedestrian footpaths by street vendors in {}.",
        "Stray dog menace near {} park, attacking children and elderly residents.",
        "Illegal parking of heavy transport vehicles in residential sector of {}.",
        "Damaged public park bench and playground equipment in {} requires repair.",
        "Unauthorized digging of road for internet cable installation in {}."
    ]
}

DEPARTMENTS = {
    "Road": "Public Works Department",
    "Water": "Jal Board",
    "Electricity": "DISCOM",
    "Sanitation": "Municipal Sanitation",
    "Other": "General"
}

SLA_DAYS = {
    "Road": 5,
    "Water": 3,
    "Electricity": 2,
    "Sanitation": 4,
    "Other": 5
}

def generate_mock_complaints(total=200):
    # Category target counts: 60 Road, 55 Water, 35 Electricity, 35 Sanitation, 15 Other
    counts = {"Road": 60, "Water": 55, "Electricity": 35, "Sanitation": 35, "Other": 15}
    complaints = []
    
    # Generate for each category
    now = datetime.utcnow()
    
    for category, count in counts.items():
        for _ in range(count):
            ward_info = random.choice(WARDS)
            ward_name = ward_info["name"]
            
            # Slightly randomize lat/lng around the ward center (within ~500m)
            lat = ward_info["lat"] + random.uniform(-0.003, 0.003)
            lng = ward_info["lng"] + random.uniform(-0.003, 0.003)
            
            text_template = random.choice(TEMPLATES[category])
            text = text_template.format(ward_name)
            
            priority_score = random.randint(1, 10)
            # Higher priority for water/electricity issues or critical descriptions
            if category in ["Water", "Electricity"] and priority_score < 4:
                priority_score += 3
            
            dept = DEPARTMENTS[category]
            sla = SLA_DAYS[category]
            
            # Estimate resolution days around SLA
            res_days = max(1, sla + random.randint(-2, 2))
            
            # Timestamp spread over last 30 days
            days_ago = random.uniform(0.1, 30.0)
            timestamp_dt = now - timedelta(days=days_ago)
            timestamp = timestamp_dt.isoformat() + "Z"
            
            # Status assignments
            # Younger complaints are Submitted or In Progress
            # Older complaints are Resolved or SLA Breached
            if days_ago < 3:
                status = random.choice(["Submitted", "In Progress"])
            elif days_ago < 7:
                status = random.choice(["In Progress", "Resolved"])
            else:
                # If resolved, did it exceed SLA?
                exceeded_sla = res_days > sla
                if exceeded_sla:
                    status = random.choice(["Resolved", "SLA Breached"])
                else:
                    status = "Resolved"
                    
            complaints.append({
                "id": str(uuid.uuid4())[:8],
                "text": text,
                "category": category,
                "priority_score": priority_score,
                "department": dept,
                "resolution_days": res_days,
                "ward": ward_name,
                "lat": round(lat, 6),
                "lng": round(lng, 6),
                "timestamp": timestamp,
                "status": status
            })
            
    # Sort by timestamp descending
    complaints.sort(key=lambda x: x["timestamp"], reverse=True)
    return complaints

def seed_data():
    print("Generating mock data...")
    complaints = generate_mock_complaints(200)
    
    # Save to seed.json
    os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)
    json_path = os.path.join(os.path.dirname(__file__), "data", "seed.json")
    with open(json_path, "w") as f:
        json.dump(complaints, f, indent=2)
    print(f"Mock data written to {json_path}")
    
    # Save to SQLite
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Clear existing data to make it idempotent
    cursor.execute("DELETE FROM complaints")
    
    # Insert new data
    for c in complaints:
        cursor.execute("""
            INSERT INTO complaints (id, text, category, priority_score, department, resolution_days, ward, lat, lng, timestamp, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            c["id"],
            c["text"],
            c["category"],
            c["priority_score"],
            c["department"],
            c["resolution_days"],
            c["ward"],
            c["lat"],
            c["lng"],
            c["timestamp"],
            c["status"]
        ))
        
    conn.commit()
    conn.close()
    print("Database seeded successfully with 200 complaints!")

if __name__ == "__main__":
    seed_data()
