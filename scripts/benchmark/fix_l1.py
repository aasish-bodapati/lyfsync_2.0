import json

with open("scripts/benchmark/cases.json", "r") as f:
    cases = json.load(f)

for case in cases:
    if case["id"] == "L1_002":
        case["input"] = "200g raw chicken breast"
        case["expected_macros"]["calories"] = 215.02
        case["expected_parse"][0]["food_name"] = "raw chicken breast"

with open("scripts/benchmark/cases.json", "w") as f:
    json.dump(cases, f, indent=2)

print("Fixed L1_002 successfully.")
