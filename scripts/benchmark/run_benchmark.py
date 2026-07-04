import os
import sys
import json
from datetime import datetime

# Ensure backend directory is in path for import resolution
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "backend", ".env"))

from sqlmodel import Session, create_engine, select
from main import (
    DATABASE_URL, get_embedding, extract_dishes, retrieve_grounding_templates,
    scale_ingredients_with_rag, ICMRRaw, USDARaw
)

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
                "predicted": {}
            }
            
            try:
                # 1. Extraction
                logged_items = extract_dishes(case["input"])
                result["extracted_items"] = [
                    {
                        "food_name": item.food_name, 
                        "logged_portion": item.logged_portion,
                        "is_cooked_dish": item.is_cooked_dish
                    } for item in logged_items
                ]
                
                # 2. Retrieve Templates
                templates = retrieve_grounding_templates(logged_items, db)
                
                # 3. Scale Ingredients
                scaled_res = scale_ingredients_with_rag(case["input"], templates, logged_items, db)
                result["scaled_ingredients"] = [
                    {
                        "food_name": ing.raw_ingredient_name,
                        "weight_g": ing.weight_g
                    } for ing in scaled_res.ingredients
                ]
                
                # 4. DB Macro Lookup
                total_cal = 0
                for ing in scaled_res.ingredients:
                    ing_emb = get_embedding(ing.raw_ingredient_name)
                    
                    icmr_dist = ICMRRaw.embedding.cosine_distance(ing_emb)
                    best_icmr = db.exec(select(ICMRRaw, icmr_dist).order_by(icmr_dist).limit(1)).first()
                    
                    usda_dist = USDARaw.embedding.cosine_distance(ing_emb)
                    best_usda = db.exec(select(USDARaw, usda_dist).order_by(usda_dist).limit(1)).first()
                    
                    candidates = []
                    if best_icmr: candidates.append(("ICMR", best_icmr[0], best_icmr[1]))
                    if best_usda: candidates.append(("USDA", best_usda[0], best_usda[1]))
                    
                    if not candidates: continue
                    candidates.sort(key=lambda x: x[2])
                    best_db_type, best_db_model, best_db_dist = candidates[0]
                    
                    if best_db_dist > 0.75: continue
                        
                    factor = ing.weight_g / 100.0
                    total_cal += best_db_model.calories * factor
                    
                SINGLE_MEAL_CAL_CAP = 3500.0
                if total_cal > SINGLE_MEAL_CAL_CAP:
                    total_cal = SINGLE_MEAL_CAL_CAP
                    
                result["predicted"]["calories"] = total_cal
                results.append(result)
                
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
