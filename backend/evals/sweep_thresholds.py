import json
import os
import sys
import statistics
from unittest.mock import patch

sys.path.append(os.path.join(os.path.dirname(__file__)))

from main import safe_parse_text, resolve_nutrition, llm_client, get_db
import embeddings

def sweep():
    dataset_path = os.path.join(os.path.dirname(__file__), "macro_eval_heldout.json")
    with open(dataset_path, "r") as f:
        dataset = json.load(f)
        
    thresholds = [0.65, 0.70, 0.75]
    
    print("="*60)
    print("THRESHOLD SWEEP ON HELD-OUT SET")
    print("="*60)
    
    for thresh in thresholds:
        print(f"\n--- Running evaluation with threshold = {thresh} ---")
        
        # Patch the functions in main.py to pass the custom threshold
        def mock_find_food(q, db, c):
            return embeddings.find_closest_food(q, db, c, threshold=thresh)
            
        def mock_find_recipe(q, db, c):
            return embeddings.find_closest_recipe(q, db, c, threshold=thresh)
            
        db = next(get_db())
        resolved_count = 0
        cal_errors = []
        prot_errors = []
        
        with patch('main.find_closest_food', side_effect=mock_find_food), \
             patch('main.find_closest_recipe', side_effect=mock_find_recipe):
             
            for idx, item in enumerate(dataset):
                parsed_meal = safe_parse_text(item["input"])
                actual_cal, actual_prot, _, _, resolved_items = resolve_nutrition(parsed_meal, db, llm_client, persist=False)
                
                cal_err = actual_cal - item["expected_calories"]
                prot_err = actual_prot - item["expected_protein"]
                
                sources = [i.source for i in resolved_items]
                if "unresolved" not in sources:
                    resolved_count += 1
                
                cal_errors.append(abs(cal_err))
                prot_errors.append(abs(prot_err))
                
        coverage = (resolved_count / len(dataset)) * 100
        mae_cal = statistics.mean(cal_errors) if cal_errors else 0
        mae_prot = statistics.mean(prot_errors) if prot_errors else 0
        
        print(f"Coverage: {coverage:.1f}% ({resolved_count}/{len(dataset)} meals)")
        print(f"Overall Calorie MAE: {mae_cal:.1f}")
        print(f"Overall Protein MAE: {mae_prot:.1f}")

if __name__ == "__main__":
    sweep()
