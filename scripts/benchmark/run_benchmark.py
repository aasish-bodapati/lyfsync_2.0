import os
import sys
import json
from datetime import datetime

# Ensure backend directory is in path for import resolution
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def run_benchmark():
    cases_path = os.path.join(os.path.dirname(__file__), "cases.json")
    results_path = os.path.join(os.path.dirname(__file__), "benchmark_results.json")
    
    if not os.path.exists(cases_path):
        print(f"Error: Could not find {cases_path}")
        sys.exit(1)
        
    with open(cases_path, "r", encoding="utf-8") as f:
        cases = json.load(f)
        
    print(f"Loaded {len(cases)} benchmark cases.")
    
    results = []
    
    for case in cases:
        print(f"Running [{case['id']}] Level {case['level']}: {case['input']}")
        
        try:
            response = client.post("/api/v1/meals/parse", json={"text": case["input"]})
            
            if response.status_code == 200:
                data = response.json()
                results.append({
                    "case_id": case["id"],
                    "status": "success",
                    "predicted": {
                        "calories": data.get("calories"),
                        "protein": data.get("protein"),
                        "carbs": data.get("carbs"),
                        "fat": data.get("fat"),
                        "meal_type": data.get("meal_type")
                    }
                })
            else:
                print(f"  Error {response.status_code}: {response.text}")
                results.append({
                    "case_id": case["id"],
                    "status": "api_error",
                    "error": response.text
                })
        except Exception as e:
            print(f"  Exception: {str(e)}")
            results.append({
                "case_id": case["id"],
                "status": "exception",
                "error": str(e)
            })
            
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "results": results
        }, f, indent=2)
        
    print(f"Saved results to {results_path}")

if __name__ == "__main__":
    run_benchmark()
