import os
import sys
import json
import time
from datetime import datetime

# Ensure backend directory is in path for import resolution
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "backend", ".env"))

from sqlmodel import Session, create_engine
from fastapi import BackgroundTasks
from main import DATABASE_URL, MealPipeline

class MockBackgroundTasks(BackgroundTasks):
    def add_task(self, func, *args, **kwargs):
        pass  # Ignore background tasks during benchmarking

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
    engine = create_engine(DATABASE_URL)
    
    with Session(engine) as db:
        for case in cases:
            print(f"Running [{case['id']}] Level {case['level']}: {case['input']}")
            
            result = {
                "case_id": case["id"],
                "status": "success",
                "extracted_items": [],
                "scaled_ingredients": [],
                "predicted": {},
                "latency_ms": {}
            }
            
            try:
                t0 = time.perf_counter()
                
                pipeline = MealPipeline(case["input"], db, MockBackgroundTasks())
                
                # 1. Extraction
                t_step = time.perf_counter()
                pipeline.extract()
                result["latency_ms"]["extraction"] = (time.perf_counter() - t_step) * 1000
                
                result["extracted_items"] = [
                    {
                        "food_name": node.original_name, 
                        "logged_portion": node.logged_portion,
                        "is_cooked_dish": node.is_cooked_dish
                    } for node in pipeline.nodes
                ]
                
                # 2. Retrieve Templates (Grounding)
                t_step = time.perf_counter()
                pipeline.ground()
                result["latency_ms"]["templates"] = (time.perf_counter() - t_step) * 1000
                
                # 3. Parse Portions
                t_step = time.perf_counter()
                pipeline.parse_portions()
                result["latency_ms"]["parse_portions"] = (time.perf_counter() - t_step) * 1000
                
                # 4. Convert and Lookup
                t_step = time.perf_counter()
                pipeline.convert()
                result["latency_ms"]["conversion"] = (time.perf_counter() - t_step) * 1000
                
                t_step = time.perf_counter()
                pipeline.nutrition()
                result["latency_ms"]["db_lookup"] = (time.perf_counter() - t_step) * 1000
                
                result["latency_ms"]["total"] = (time.perf_counter() - t0) * 1000
                
                # Format scaled ingredients from nodes
                resolved = []
                total_cal = 0.0
                for node in pipeline.nodes:
                    resolved.append({
                        "food_name": node.original_name,
                        "quantity": node.quantity,
                        "unit": node.unit,
                        "state": node.state,
                        "weight_g": node.weight_g,
                        "food_id": node.food_id
                    })
                    if node.calories:
                        total_cal += node.calories
                        
                result["scaled_ingredients"] = resolved
                
                # Simulate the cap from persist
                SINGLE_MEAL_CAL_CAP = 3500.0
                if total_cal > SINGLE_MEAL_CAL_CAP:
                    total_cal = SINGLE_MEAL_CAL_CAP
                    
                result["predicted"]["calories"] = total_cal
                
                # Rollback transaction so benchmark doesn't insert meals into DB
                db.rollback()
                
                results.append(result)
                
            except Exception as e:
                import traceback
                print(f"  Exception: {str(e)}")
                traceback.print_exc()
                print("  Nodes state:")
                for idx, node in enumerate(pipeline.nodes):
                    print(f"    Node {idx}: original_name={node.original_name}, is_cooked_dish={node.is_cooked_dish}, db_type={node.db_type}, food_id={node.food_id}, weight_g={node.weight_g}")
                results.append({
                    "case_id": case["id"],
                    "status": "exception",
                    "error": str(e)
                })
                db.rollback()
            
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "results": results
        }, f, indent=2)
        
    print(f"Saved results to {results_path}")

if __name__ == "__main__":
    run_benchmark()
