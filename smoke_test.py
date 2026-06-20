import sys
import os

# Add parent directory to system path to resolve imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import get_db_connection
from routes.classify import rule_based_fallback

def run_tests():
    print("Running backend smoke tests...")
    
    # 1. Test database connection and count
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM complaints")
    count = cursor.fetchone()["count"]
    conn.close()
    print(f"Verified Database: Found {count} complaints in SQLite database.")
    assert count >= 200, f"Expected at least 200 complaints, got {count}"
    
    # 2. Test rule-based fallback classifier
    result_water = rule_based_fallback("There is a water pipeline leakage near Chetak Circle")
    print(f"Verified Fallback (Water): {result_water['category']} - {result_water['department']}")
    assert result_water["category"] == "Water"
    assert result_water["department"] == "Jal Board"
    
    result_road = rule_based_fallback("Huge pothole or gaddha in the middle of the street")
    print(f"Verified Fallback (Road): {result_road['category']} - {result_road['department']}")
    assert result_road["category"] == "Road"
    assert result_road["department"] == "Public Works Department"
    
    print("All backend smoke tests passed successfully!")

if __name__ == "__main__":
    run_tests()
