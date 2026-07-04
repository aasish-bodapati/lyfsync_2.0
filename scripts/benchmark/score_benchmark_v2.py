import json
import os

def categorize_error(pct):
    if pct <= 5: return "Excellent (<5%)"
    if pct <= 10: return "Good (5-10%)"
    if pct <= 20: return "Acceptable (10-20%)"
    if pct <= 30: return "Poor (20-30%)"
    return "Fail (>30%)"

def run_scorer():
    cases_path = os.path.join(os.path.dirname(__file__), "cases.json")
    results_path = os.path.join(os.path.dirname(__file__), "benchmark_results.json")
    report_path = os.path.join(os.path.dirname(__file__), "benchmark_report.md")

    with open(cases_path, "r") as f:
        cases = {c["id"]: c for c in json.load(f)}

    with open(results_path, "r") as f:
        results = json.load(f)["results"]

    metrics = {
        "ingredient_extraction": {"hits": 0, "total": 0},
        "cooking_state": {"hits": 0, "total": 0},
        "quantity_extraction": {"hits": 0, "total": 0},
        "macro_bands": {
            "Excellent (<5%)": 0,
            "Good (5-10%)": 0,
            "Acceptable (10-20%)": 0,
            "Poor (20-30%)": 0,
            "Fail (>30%)": 0
        },
        "total_cases": 0
    }

    for res in results:
        if res["status"] != "success": continue
        case = cases[res["case_id"]]
        metrics["total_cases"] += 1

        # 1. Score Intermediate Parses
        expected_parses = case.get("expected_parse", [])
        if expected_parses:
            # We map extracted items to expected by simple substring inclusion for now
            extracted_names = [e["food_name"].lower() for e in res.get("extracted_items", [])]
            extracted_states = {e["food_name"].lower(): e["is_cooked_dish"] for e in res.get("extracted_items", [])}
            
            scaled_weights = {s["food_name"].lower(): s["weight_g"] for s in res.get("scaled_ingredients", [])}

            for exp in expected_parses:
                exp_name = exp["food_name"].lower()
                metrics["ingredient_extraction"]["total"] += 1
                metrics["cooking_state"]["total"] += 1
                metrics["quantity_extraction"]["total"] += 1

                # Find best match in extracted
                matched_ext = next((n for n in extracted_names if exp_name in n or n in exp_name), None)
                if matched_ext:
                    metrics["ingredient_extraction"]["hits"] += 1
                    
                    if extracted_states.get(matched_ext) == exp["is_cooked_dish"]:
                        metrics["cooking_state"]["hits"] += 1

                # Find best match in scaled
                matched_scale = next((k for k in scaled_weights.keys() if exp_name in k or k in exp_name), None)
                if matched_scale:
                    exp_w = exp.get("weight_g", 0)
                    pred_w = scaled_weights[matched_scale]
                    if exp_w > 0 and abs(exp_w - pred_w) / exp_w <= 0.15: # 15% tolerance on weight
                        metrics["quantity_extraction"]["hits"] += 1

        # 2. Score Macros
        if "expected_macros" in case:
            expected_cal = case["expected_macros"]["calories"]
            pred_cal = res["predicted"]["calories"]
            error_pct = abs(expected_cal - pred_cal) / expected_cal * 100
            band = categorize_error(error_pct)
            metrics["macro_bands"][band] += 1

    # Generate Markdown Report
    with open(report_path, "w") as f:
        f.write("# LyfSync SOTA Benchmark Report v2.0\n\n")
        
        f.write("## 1. NLP Parser Accuracy\n\n")
        f.write("| Metric | Score |\n")
        f.write("| --- | --- |\n")
        
        def pct(hits, total):
            return f"{(hits/total*100):.1f}%" if total > 0 else "N/A"
            
        f.write(f"| Ingredient Extraction | {pct(metrics['ingredient_extraction']['hits'], metrics['ingredient_extraction']['total'])} |\n")
        f.write(f"| Cooking State Detection | {pct(metrics['cooking_state']['hits'], metrics['cooking_state']['total'])} |\n")
        f.write(f"| Quantity & Scaling | {pct(metrics['quantity_extraction']['hits'], metrics['quantity_extraction']['total'])} |\n\n")
        
        f.write("## 2. Nutrition Engine Accuracy (Calorie Error Bands)\n\n")
        f.write(f"Total Cases: {metrics['total_cases']}\n\n")
        f.write("| Error Band | Count | % |\n")
        f.write("| --- | --- | --- |\n")
        
        for band, count in metrics["macro_bands"].items():
            f.write(f"| {band} | {count} | {pct(count, metrics['total_cases'])} |\n")

    print(f"Scoring complete. v2 Report saved to {report_path}")

if __name__ == "__main__":
    run_scorer()
