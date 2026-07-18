import json
import os
import sys
import math
import statistics

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from main import safe_parse_text, resolve_nutrition, llm_client, get_db

def run_macro_eval():
    dataset_path = os.path.join(os.path.dirname(__file__), "macro_eval_dataset.json")
    with open(dataset_path, "r") as f:
        dataset = json.load(f)
        
    db = next(get_db())
    
    # Store errors by source category
    # categories: "food_match", "recipe_match", "generated_recipe", "mixed_sources", "unresolved"
    cal_errors_by_source = {"food_match": [], "recipe_match": [], "generated_recipe": [], "mixed_sources": [], "unresolved": []}
    prot_errors_by_source = {"food_match": [], "recipe_match": [], "generated_recipe": [], "mixed_sources": [], "unresolved": []}
    
    total_meals = 0
    resolved_count = 0
    
    print("="*60)
    print("MACRO EVALUATION REPORT")
    print("="*60)
    
    for idx, item in enumerate(dataset):
        input_text = item["input"]
        expected_cal = item["expected_calories"]
        expected_prot = item["expected_protein"]
        
        try:
            parsed_meal = safe_parse_text(input_text)
            actual_cal, actual_prot, _, _, resolved_items = resolve_nutrition(parsed_meal, db, llm_client, persist=False)
            
            cal_err = actual_cal - expected_cal
            prot_err = actual_prot - expected_prot
            
            total_meals += 1
            
            # Determine the primary source for the meal
            sources = [i.source for i in resolved_items]
            
            # Group into the exact source prefixes
            source_prefixes = []
            for s in sources:
                if s.startswith("food_match"): source_prefixes.append("food_match")
                elif s.startswith("recipe_match"): source_prefixes.append("recipe_match")
                elif s.startswith("generated_recipe"): source_prefixes.append("generated_recipe")
                else: source_prefixes.append("unresolved")
            
            unique_sources = set(source_prefixes)
            if len(unique_sources) == 1:
                primary_source = list(unique_sources)[0]
            elif "unresolved" in unique_sources and len(unique_sources) == 2:
                # If it's a mix of unresolved and one other, still count it as unresolved to highlight failure
                primary_source = "unresolved"
            else:
                primary_source = "mixed_sources"
                
            if primary_source != "unresolved":
                resolved_count += 1
                
            cal_errors_by_source[primary_source].append(cal_err)
            prot_errors_by_source[primary_source].append(prot_err)
            
            print(f"[{idx+1}/25] {input_text}")
            print(f"  Source: {primary_source} (Items: {len(resolved_items)})")
            print(f"  Cal: {actual_cal:.1f} (Exp: {expected_cal}) | Err: {cal_err:+.1f}")
            print(f"  Pro: {actual_prot:.1f} (Exp: {expected_prot}) | Err: {prot_err:+.1f}")
            
        except Exception as e:
            db.rollback()
            print(f"[{idx+1}/25] ERROR on '{input_text}': {e}")
            total_meals += 1
            cal_errors_by_source["unresolved"].append(0.0 - expected_cal)
            prot_errors_by_source["unresolved"].append(0.0 - expected_prot)
            
    print("\n" + "="*60)
    print("OVERALL METRICS")
    print("="*60)
    
    coverage = (resolved_count / total_meals) * 100 if total_meals else 0.0
    print(f"Coverage: {coverage:.1f}% ({resolved_count}/{total_meals} meals resolved)")
    
    for source in ["food_match", "recipe_match", "generated_recipe", "mixed_sources", "unresolved"]:
        c_errs = cal_errors_by_source[source]
        p_errs = prot_errors_by_source[source]
        if not c_errs:
            continue
            
        count = len(c_errs)
        
        c_mae = sum(abs(e) for e in c_errs) / count
        p_mae = sum(abs(e) for e in p_errs) / count
        
        c_med = statistics.median([abs(e) for e in c_errs])
        p_med = statistics.median([abs(e) for e in p_errs])
        
        c_rmse = math.sqrt(sum(e**2 for e in c_errs) / count)
        p_rmse = math.sqrt(sum(e**2 for e in p_errs) / count)
        
        print(f"\n--- {source.upper()} ({count} meals) ---")
        print(f"  Calories -> MAE: {c_mae:.1f} | Median: {c_med:.1f} | RMSE: {c_rmse:.1f}")
        print(f"  Protein  -> MAE: {p_mae:.1f} | Median: {p_med:.1f} | RMSE: {p_rmse:.1f}")
        
    print("="*60)

if __name__ == "__main__":
    run_macro_eval()
