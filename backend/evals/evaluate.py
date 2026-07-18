import json
import os
import sys
from collections import defaultdict
from typing import Any

# Add backend to path so we can import from main
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from main import safe_parse_text

EVAL_ALIASES = {
    "doodh": "milk",
    "chawal": "rice",
    "ande": "egg",
    "bhindi ki sabzi": "bhindi sabzi"
}

def normalize_name(name: str) -> str:
    """Normalizes string for comparison (lowercasing, plural stripping, aliases)."""
    n = name.lower().strip()
    
    if n.endswith('s') and not n.endswith('ss'):
        n = n[:-1]
        
    for k, v in EVAL_ALIASES.items():
        if k in n:
            n = n.replace(k, v)
            
    return n.strip()

UNIT_ALIASES = {
    "grams": "g", "gram": "g",
    "milliliters": "ml", "milliliter": "ml",
    "tablespoon": "tbsp",
    "teaspoon": "tsp",
    "pieces": "piece",
    "slices": "slice",
    "rotis": "roti",
    "chapatis": "chapati",
    "bowls": "bowl",
    "cups": "cup",
    "glasses": "glass"
}

def normalize_unit(unit: str) -> str:
    if not unit:
        return ""
    u = unit.lower().strip()
    return UNIT_ALIASES.get(u, u)

def match_items(expected_names: list[str], predicted_items: list[Any]) -> list[tuple[int, Any]]:
    matches = []
    used_predicted_indices = set()
    
    normalized_expected = [normalize_name(n) for n in expected_names]
    normalized_predicted = [normalize_name(p.name) for p in predicted_items]
    
    for e_idx, e_name in enumerate(normalized_expected):
        for p_idx, p_name in enumerate(normalized_predicted):
            if p_idx in used_predicted_indices:
                continue
            if e_name == p_name:
                matches.append((e_idx, predicted_items[p_idx]))
                used_predicted_indices.add(p_idx)
                break
                
    matched_e_indices = {m[0] for m in matches}
    
    for e_idx, e_name in enumerate(normalized_expected):
        if e_idx in matched_e_indices:
            continue
        for p_idx, p_name in enumerate(normalized_predicted):
            if p_idx in used_predicted_indices:
                continue
            if e_name in p_name or p_name in e_name:
                matches.append((e_idx, predicted_items[p_idx]))
                used_predicted_indices.add(p_idx)
                break
                
    return matches

def safe_float_equal(a, b, tolerance=0.1):
    if a is None or b is None:
        return a == b
    return abs(float(a) - float(b)) <= tolerance

def run_evals():
    dataset_path = os.path.join(os.path.dirname(__file__), "eval_dataset.json")
    failures_path = os.path.join(os.path.dirname(__file__), "eval_failures.json")
    
    with open(dataset_path, "r") as f:
        dataset = json.load(f)
        
    num_runs = 3
    run_f1s = []
    run_exact_matches = []
    
    print(f"Starting Robust Evaluation on {len(dataset)} examples ({num_runs} runs)...\n")
    
    for run in range(num_runs):
        print(f"\n--- RUN {run+1}/{num_runs} ---")
        totals = {
            "expected_items_total": 0, "extracted_items_correct": 0,
            "extra_predicted_total": 0, "exact_meal_matches": 0,
            "total_meals": 0
        }
        
        all_failures = []
        
        for i, example in enumerate(dataset):
            input_text = example["input"]
            slice_name = example.get("slice", "unknown")
            
            expected_items = example.get("expected_items", [])
            expected_quantities = example.get("expected_quantities", [])
            expected_units = [u.lower() for u in example.get("expected_units", [])]
            expected_raw_or_cooked = [rc.lower() for rc in example.get("expected_raw_or_cooked", [])]
            expected_needs_clarification = example.get("expected_needs_clarification", False)
            
            totals["total_meals"] += 1
            totals["expected_items_total"] += len(expected_items)
            
            meal_failed = False
            
            try:
                parsed = safe_parse_text(input_text)
                
                any_clarification = any(item.needs_clarification for item in parsed.items)
                if any_clarification != expected_needs_clarification:
                    meal_failed = True
                    
                matches = match_items(expected_items, parsed.items)
                matched_map = {m[0]: m[1] for m in matches}
                
                totals["extracted_items_correct"] += len(matches)
                
                for e_idx, e_name in enumerate(expected_items):
                    if e_idx not in matched_map:
                        meal_failed = True
                        continue
                        
                    pred_item = matched_map[e_idx]
                    if not safe_float_equal(expected_quantities[e_idx], pred_item.quantity):
                        meal_failed = True
                    if normalize_unit(expected_units[e_idx]) != normalize_unit(pred_item.unit):
                        meal_failed = True
                    if expected_raw_or_cooked[e_idx] != pred_item.raw_or_cooked.lower():
                        meal_failed = True
                        
                # Count extra predicted items
                matched_p_items = list(matched_map.values())
                extras = 0
                for p in parsed.items:
                    if p not in matched_p_items:
                        extras += 1
                        
                totals["extra_predicted_total"] += extras
                if extras > 0:
                    meal_failed = True
                    
                if not meal_failed:
                    totals["exact_meal_matches"] += 1
                    
            except Exception as e:
                meal_failed = True
                print(f"[{i+1}/{len(dataset)}] ERROR on '{input_text}': {e}")
                
        # Calculate PRF1 for this run
        tp = totals["extracted_items_correct"]
        fp = totals["extra_predicted_total"]
        fn = totals["expected_items_total"] - tp
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        exact_match = totals["exact_meal_matches"] / totals["total_meals"] if totals["total_meals"] > 0 else 0.0
        
        run_f1s.append(f1)
        run_exact_matches.append(exact_match)
        print(f"Run {run+1} Complete -> F1: {f1*100:.1f}%, Exact Match: {exact_match*100:.1f}%")
        
    # Aggregate over 3 runs
    mean_f1 = sum(run_f1s) / num_runs
    min_f1 = min(run_f1s)
    max_f1 = max(run_f1s)
    
    mean_exact = sum(run_exact_matches) / num_runs
    min_exact = min(run_exact_matches)
    max_exact = max(run_exact_matches)
    
    print("\n" + "="*50)
    print("ROBUST METRICS (OVER 3 RUNS)")
    print("="*50)
    print(f"F1 Score (Extraction):")
    print(f"  Mean: {mean_f1*100:.1f}%")
    print(f"  Min:  {min_f1*100:.1f}%")
    print(f"  Max:  {max_f1*100:.1f}%")
    print("-" * 50)
    print(f"Exact Meal Match:")
    print(f"  Mean: {mean_exact*100:.1f}%")
    print(f"  Min:  {min_exact*100:.1f}%")
    print(f"  Max:  {max_exact*100:.1f}%")
    print("=" * 50)

if __name__ == "__main__":
    run_evals()
