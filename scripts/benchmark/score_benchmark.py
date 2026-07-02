import os
import sys
import json
from collections import defaultdict

def calculate_error(predicted, gold):
    if gold == 0:
        return 0 if predicted == 0 else 100
    return abs(predicted - gold) / gold * 100

def score_benchmark():
    cases_path = os.path.join(os.path.dirname(__file__), "cases.json")
    results_path = os.path.join(os.path.dirname(__file__), "benchmark_results.json")
    report_path = os.path.join(os.path.dirname(__file__), "benchmark_report.md")
    
    if not os.path.exists(cases_path) or not os.path.exists(results_path):
        print("Error: cases.json or benchmark_results.json not found.")
        sys.exit(1)
        
    with open(cases_path, "r", encoding="utf-8") as f:
        cases = {c["id"]: c for c in json.load(f)}
        
    with open(results_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        results = data["results"]
        
    level_stats = defaultdict(lambda: {"total": 0, "pass": 0, "cal_errors": []})
    
    for res in results:
        case_id = res["case_id"]
        case = cases.get(case_id)
        if not case:
            continue
            
        level = case["level"]
        level_name = case["level_name"]
        key = f"Level {level}: {level_name}"
        
        level_stats[key]["total"] += 1
        
        if res["status"] != "success":
            continue
            
        pred = res["predicted"]
        gold = case["gold_standard"]
        tol = case["tolerance"]
        
        cal_err = calculate_error(pred["calories"], gold["calories"])
        pro_err = calculate_error(pred["protein"], gold["protein"])
        carb_err = calculate_error(pred["carbs"], gold["carbs"])
        fat_err = calculate_error(pred["fat"], gold["fat"])
        
        level_stats[key]["cal_errors"].append(cal_err)
        
        if (cal_err <= tol["calorie_pct"] and 
            pro_err <= tol["protein_pct"] and 
            carb_err <= tol["carbs_pct"] and 
            fat_err <= tol["fat_pct"]):
            level_stats[key]["pass"] += 1

    # Generate Report
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# LyfSync SOTA Benchmark Report\n\n")
        f.write(f"Generated at: {data.get('timestamp')}\n\n")
        
        f.write("| Level | Total Cases | Pass Rate | Median Calorie Error |\n")
        f.write("| :--- | :---: | :---: | :---: |\n")
        
        all_cal_errors = []
        total_pass = 0
        total_cases = 0
        
        for key in sorted(level_stats.keys()):
            stats = level_stats[key]
            total = stats["total"]
            total_cases += total
            passed = stats["pass"]
            total_pass += passed
            
            pass_rate = (passed / total * 100) if total > 0 else 0
            
            errors = sorted(stats["cal_errors"])
            all_cal_errors.extend(errors)
            
            if errors:
                median_err = errors[len(errors)//2] if len(errors) % 2 != 0 else (errors[len(errors)//2 - 1] + errors[len(errors)//2]) / 2
                median_str = f"{median_err:.1f}%"
            else:
                median_str = "N/A"
                
            f.write(f"| {key} | {total} | {pass_rate:.1f}% | {median_str} |\n")
            
        f.write("\n### Global Metrics\n")
        global_pass_rate = (total_pass / total_cases * 100) if total_cases > 0 else 0
        
        if all_cal_errors:
            all_cal_errors.sort()
            global_median = all_cal_errors[len(all_cal_errors)//2] if len(all_cal_errors) % 2 != 0 else (all_cal_errors[len(all_cal_errors)//2 - 1] + all_cal_errors[len(all_cal_errors)//2]) / 2
        else:
            global_median = 0
            
        f.write(f"- **Overall Pass Rate:** {global_pass_rate:.1f}%\n")
        f.write(f"- **Global Median Calorie Error:** {global_median:.1f}%\n")
        
    print(f"Scoring complete. Report saved to {report_path}")

if __name__ == "__main__":
    score_benchmark()
