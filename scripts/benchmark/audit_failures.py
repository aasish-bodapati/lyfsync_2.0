"""
Knowledge Audit Tool — scripts/benchmark/audit_failures.py

After every benchmark run, classifies each macro failure into a specific cause
category and prints a roadmap of exactly which deterministic rules are missing.

Failure categories:
  - missing_density    : Volume unit parsed, but food not in food_density.json
  - missing_serving    : Non-volume, non-weight unit; not in ReferenceServing DB
  - missing_whole      : Fractional whole object not in whole_object_weights.json
  - converter_none     : Converter returned None (unknown unit or edge case)
  - retrieval_mismatch : Best DB match was too far from expected food
  - parser_error       : LLM extracted wrong food name or unit
  - macro_error        : Converter succeeded but calorie error > 30%
  - other              : Unclassified
"""

import os
import sys
import json

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "backend", ".env"))

from unit_converter import (
    FOOD_DENSITY, WHOLE_OBJECT_WEIGHTS, VOLUME_UNITS_ML, UNIVERSAL_UNITS,
    _find_density, _find_whole_weight
)

def classify_failure(case: dict, result: dict) -> tuple[str, str]:
    """
    Returns (category, description) for a failed benchmark case.
    """
    scaled = result.get("scaled_ingredients", [])
    
    # If no ingredients were resolved at all
    if not scaled:
        return ("converter_none", "No ingredients resolved — all portions failed conversion")
    
    # If extraction got nothing
    if not result.get("extracted_items"):
        return ("parser_error", "LLM failed to extract any food items")
    
    # Check for converter_none items in the scaled output
    none_items = [s for s in scaled if s.get("weight_g") is None]
    if none_items:
        item = none_items[0]
        food = item["food_name"]
        unit = item["unit"]
        
        if unit in VOLUME_UNITS_ML:
            density = _find_density(food)
            if density is None:
                return ("missing_density", f"Volume unit '{unit}' found for '{food}' but no density entry")
        
        if any(k in unit.lower() for k in ["whole", "pizza", "cake", "loaf", "burger"]):
            return ("missing_whole", f"Whole-object unit '{unit}' not in whole_object_weights.json")
        
        if unit.lower() not in UNIVERSAL_UNITS and unit.lower() not in VOLUME_UNITS_ML:
            return ("missing_serving", f"Non-standard unit '{unit}' for '{food}' — add to ReferenceServing or whole_object_weights.json")
        
        return ("converter_none", f"Converter returned None for '{food}' with unit '{unit}'")
    
    # If macros were computed but wrong, check calorie error
    expected_cal = case.get("expected_macros", {}).get("calories")
    pred_cal = result.get("predicted", {}).get("calories")
    if expected_cal and pred_cal is not None:
        error_pct = abs(expected_cal - pred_cal) / expected_cal * 100
        if error_pct > 30:
            # Check if the predicted calories are suspiciously wrong for a known unit
            return ("macro_error", f"Converter succeeded but calorie error is {error_pct:.0f}% — check density value or DB retrieval")
    
    return ("other", "Unclassified failure")


def run_audit():
    cases_path = os.path.join(os.path.dirname(__file__), "cases.json")
    results_path = os.path.join(os.path.dirname(__file__), "benchmark_results.json")
    audit_path = os.path.join(os.path.dirname(__file__), "knowledge_audit.md")
    
    with open(cases_path) as f:
        cases = {c["id"]: c for c in json.load(f)}
    with open(results_path) as f:
        results = json.load(f)["results"]
    
    category_counts = {}
    tickets = []
    
    for res in results:
        if res["status"] != "success":
            category_counts["exception"] = category_counts.get("exception", 0) + 1
            continue
        
        case = cases[res["case_id"]]
        expected_cal = case.get("expected_macros", {}).get("calories")
        pred_cal = res.get("predicted", {}).get("calories")
        
        if expected_cal is None or pred_cal is None:
            continue
        
        error_pct = abs(expected_cal - pred_cal) / expected_cal * 100
        
        if error_pct <= 30:
            continue  # Passing case, skip
        
        cat, desc = classify_failure(case, res)
        category_counts[cat] = category_counts.get(cat, 0) + 1
        
        tickets.append({
            "case_id": res["case_id"],
            "input": case["input"],
            "expected_cal": expected_cal,
            "predicted_cal": pred_cal,
            "error_pct": round(error_pct, 1),
            "category": cat,
            "description": desc
        })
    
    # Sort tickets by category then error
    tickets.sort(key=lambda t: (t["category"], -t["error_pct"]))
    
    # Write report
    with open(audit_path, "w") as f:
        f.write("# Knowledge Audit Report\n\n")
        f.write("> Generated automatically by `audit_failures.py`. Each row is an engineering task.\n\n")
        
        f.write("## Failure Summary by Category\n\n")
        f.write("| Category | Count |\n")
        f.write("| --- | --- |\n")
        total = sum(category_counts.values())
        for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
            f.write(f"| {cat} | {count} |\n")
        f.write(f"| **Total Failures** | **{total}** |\n\n")
        
        f.write("## Actionable Tickets\n\n")
        f.write("| Case | Input | Category | Description | Error % | Expected | Predicted |\n")
        f.write("| --- | --- | --- | --- | --- | --- | --- |\n")
        for t in tickets:
            f.write(
                f"| {t['case_id']} | `{t['input']}` | **{t['category']}** "
                f"| {t['description']} | {t['error_pct']}% "
                f"| {t['expected_cal']} kcal | {t['predicted_cal']:.0f} kcal |\n"
            )
        
        f.write("\n## Next Steps\n\n")
        f.write("- **missing_density**: Add the food to `backend/data/food_density.json`\n")
        f.write("- **missing_serving**: Add a row to the `reference_servings` DB table via `scripts/seed_reference_servings.py`\n")
        f.write("- **missing_whole**: Add the object to `backend/data/whole_object_weights.json`\n")
        f.write("- **macro_error**: Verify density value is correct, or check the embedding retrieval for this ingredient\n")
        f.write("- **retrieval_mismatch**: Verify the food is in the USDA/ICMR database or add it\n")
    
    print(f"Audit complete. {len(tickets)} failures classified.")
    print(f"Report saved to {audit_path}")
    
    print("\n== Failure Summary ==")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    run_audit()
