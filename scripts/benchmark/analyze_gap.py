import json

with open("scripts/benchmark/cases.json") as f:
    cases = {c["id"]: c for c in json.load(f)}

with open("scripts/benchmark/benchmark_results.json") as f:
    results = json.load(f)["results"]

errors = []
for r in results:
    if r["status"] != "success": continue
    case = cases[r["case_id"]]
    expected_cal = case["gold_standard"]["calories"]
    pred_cal = r["predicted"]["calories"]
    error_pct = abs(expected_cal - pred_cal) / expected_cal * 100
    errors.append({
        "id": case["id"],
        "level": case["level"],
        "input": case["input"],
        "expected": expected_cal,
        "predicted": pred_cal,
        "error_pct": error_pct
    })

errors.sort(key=lambda x: x["error_pct"], reverse=True)
print(f"{'ID':<8} | {'Expected':<10} | {'Predicted':<10} | {'Error %':<8} | Input")
print("-" * 80)
for e in errors:
    print(f"{e['id']:<8} | {e['expected']:<10.1f} | {e['predicted']:<10.1f} | {e['error_pct']:<8.1f}% | {e['input'][:40]}")
