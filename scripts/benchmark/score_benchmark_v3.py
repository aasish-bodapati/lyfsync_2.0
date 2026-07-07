import json
import os
import statistics

def categorize_error(pct):
    if pct <= 5: return "Excellent (<5%)"
    if pct <= 10: return "Good (5-10%)"
    if pct <= 20: return "Acceptable (10-20%)"
    if pct <= 30: return "Poor (20-30%)"
    return "Fail (>30%)"

def p(data, percentile):
    if not data: return 0.0
    return statistics.quantiles(data, n=100)[percentile - 1] if len(data) > 1 else data[0]

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
        "unit_recognition": {"hits": 0, "total": 0},
        "unit_grams_accuracy": {"hits": 0, "total": 0},
        "canonical_mapping": {"hits": 0, "total": 0},
        "macro_bands": {
            "Excellent (<5%)": 0,
            "Good (5-10%)": 0,
            "Acceptable (10-20%)": 0,
            "Poor (20-30%)": 0,
            "Fail (>30%)": 0
        },
        "latencies": {
            "extraction": [],
            "templates": [],
            "parse_portions": [],
            "conversion": [],
            "db_lookup": []
        },
        "total_cases": 0
    }

    for res in results:
        if res["status"] != "success": continue
        case = cases[res["case_id"]]
        metrics["total_cases"] += 1

        # Latencies
        for k, v in res.get("latency_ms", {}).items():
            metrics["latencies"][k].append(v)

        # Score Intermediate Parses
        expected_parses = case.get("expected_parse", [])
        if expected_parses:
            extracted_names = [e["food_name"].lower() for e in res.get("extracted_items", [])]
            extracted_states = {e["food_name"].lower(): e["is_cooked_dish"] for e in res.get("extracted_items", [])}
            
            scaled_weights = {s["food_name"].lower(): s["weight_g"] for s in res.get("scaled_ingredients", [])}
            scaled_units = {s["food_name"].lower(): s.get("unit") for s in res.get("scaled_ingredients", [])}
            scaled_ids = {s["food_name"].lower(): s.get("food_id") for s in res.get("scaled_ingredients", [])}
            scaled_final_states = {s["food_name"].lower(): s.get("state") for s in res.get("scaled_ingredients", [])}

            for exp in expected_parses:
                exp_name = exp["food_name"].lower()
                metrics["ingredient_extraction"]["total"] += 1
                
                # Check ingredient extraction
                matched_ext = next((n for n in extracted_names if exp_name in n or n in exp_name), None)
                if matched_ext:
                    metrics["ingredient_extraction"]["hits"] += 1

                # Check downstream scaling/converter outputs
                matched_scale = next((k for k in scaled_weights.keys() if exp_name in k or k in exp_name), None)
                
                if "state" in exp:
                    metrics["cooking_state"]["total"] += 1
                    if matched_scale and scaled_final_states.get(matched_scale) == exp["state"]:
                        metrics["cooking_state"]["hits"] += 1
                        
                if "expected_unit" in exp:
                    metrics["unit_recognition"]["total"] += 1
                    if matched_scale and scaled_units.get(matched_scale) == exp["expected_unit"]:
                        metrics["unit_recognition"]["hits"] += 1
                        
                if "expected_id" in exp:
                    metrics["canonical_mapping"]["total"] += 1
                    if matched_scale and scaled_ids.get(matched_scale) == exp["expected_id"]:
                        metrics["canonical_mapping"]["hits"] += 1
                        
                if "weight_g" in exp:
                    metrics["unit_grams_accuracy"]["total"] += 1
                    if matched_scale:
                        exp_w = exp.get("weight_g", 0)
                        pred_w = scaled_weights[matched_scale]
                        if pred_w is not None and exp_w > 0 and abs(exp_w - pred_w) / exp_w <= 0.15:
                            metrics["unit_grams_accuracy"]["hits"] += 1

        # Score Macros
        if "expected_macros" in case:
            expected_cal = case["expected_macros"]["calories"]
            pred_cal = res["predicted"]["calories"]
            error_pct = abs(expected_cal - pred_cal) / expected_cal * 100
            band = categorize_error(error_pct)
            metrics["macro_bands"][band] += 1

    # Generate Markdown Report
    with open(report_path, "w") as f:
        f.write("# LyfSync SOTA Benchmark Report v3.0\n\n")
        
        f.write("## 1. NLP & Pipeline Accuracy\n\n")
        f.write("| Metric | Score |\n")
        f.write("| --- | --- |\n")
        
        def pct(hits, total):
            return f"{(hits/total*100):.1f}%" if total > 0 else "N/A"
            
        f.write(f"| Ingredient Extraction | {pct(metrics['ingredient_extraction']['hits'], metrics['ingredient_extraction']['total'])} |\n")
        f.write(f"| Cooking State Resolution | {pct(metrics['cooking_state']['hits'], metrics['cooking_state']['total'])} |\n")
        f.write(f"| Unit Recognition | {pct(metrics['unit_recognition']['hits'], metrics['unit_recognition']['total'])} |\n")
        f.write(f"| Unit->Grams Accuracy | {pct(metrics['unit_grams_accuracy']['hits'], metrics['unit_grams_accuracy']['total'])} |\n")
        f.write(f"| Canonical ID Mapping | {pct(metrics['canonical_mapping']['hits'], metrics['canonical_mapping']['total'])} |\n\n")
        
        f.write("## 2. Latency (Percentiles)\n\n")
        f.write("| Stage | P50 (ms) | P95 (ms) | P99 (ms) |\n")
        f.write("| --- | --- | --- | --- |\n")
        for stage, data in metrics["latencies"].items():
            if data:
                p50, p95, p99 = p(data, 50), p(data, 95), p(data, 99)
                f.write(f"| {stage} | {p50:.1f} | {p95:.1f} | {p99:.1f} |\n")
        f.write("\n")
        
        f.write("## 3. Nutrition Engine Accuracy (Calorie Error Bands)\n\n")
        f.write(f"Total Cases: {metrics['total_cases']}\n\n")
        f.write("| Error Band | Count | % |\n")
        f.write("| --- | --- | --- |\n")
        
        for band, count in metrics["macro_bands"].items():
            f.write(f"| {band} | {count} | {pct(count, metrics['total_cases'])} |\n")

    print(f"Scoring complete. v3 Report saved to {report_path}")

if __name__ == "__main__":
    run_scorer()
