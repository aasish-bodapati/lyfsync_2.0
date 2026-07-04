import json

with open("scripts/benchmark/cases.json", "r") as f:
    cases = json.load(f)

for case in cases:
    # Migrate gold_standard -> expected_macros
    if "gold_standard" in case:
        case["expected_macros"] = case.pop("gold_standard")
    
    # Add empty expected_parse structure
    if "expected_parse" not in case:
        case["expected_parse"] = [
            # {
            #     "food_name": "example",
            #     "weight_g": 100,
            #     "is_cooked_dish": False
            # }
        ]

with open("scripts/benchmark/cases.json", "w") as f:
    json.dump(cases, f, indent=2)

print("Migrated cases.json successfully.")
