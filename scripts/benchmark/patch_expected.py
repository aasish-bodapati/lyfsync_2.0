import json

with open("scripts/benchmark/cases.json", "r") as f:
    cases = json.load(f)

patches = {
    "L1_001": [{"food_name": "raw oats", "weight_g": 100, "is_cooked_dish": False}],
    "L1_002": [{"food_name": "chicken breast", "weight_g": 200, "is_cooked_dish": False}],
    "L2_001": [{"food_name": "oats", "weight_g": 40, "is_cooked_dish": False}, {"food_name": "milk", "weight_g": 100, "is_cooked_dish": False}],
    "L2_002": [{"food_name": "eggs", "weight_g": 106, "is_cooked_dish": False}],
    "L2_003": [{"food_name": "banana", "weight_g": 118, "is_cooked_dish": False}],
    "L2_004": [{"food_name": "cooked white rice", "weight_g": 150, "is_cooked_dish": True}],
    "L3_001": [{"food_name": "chicken breast", "weight_g": 200, "is_cooked_dish": False}, {"food_name": "olive oil", "weight_g": 14, "is_cooked_dish": False}],
    "L3_002": [{"food_name": "eggs", "weight_g": 106, "is_cooked_dish": False}, {"food_name": "butter", "weight_g": 10, "is_cooked_dish": False}]
}

for case in cases:
    if case["id"] in patches:
        case["expected_parse"] = patches[case["id"]]

with open("scripts/benchmark/cases.json", "w") as f:
    json.dump(cases, f, indent=2)

print("Patched expected_parse successfully.")
