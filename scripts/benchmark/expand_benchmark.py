import json
import os

cases_path = os.path.join(os.path.dirname(__file__), "cases.json")
with open(cases_path, "r") as f:
    cases = json.load(f)

# Base DB truths for generation
# Oats (USDA: 381.6 kcal/100g)
# Chicken, raw (USDA: 107.5 kcal/100g)
# Chicken, cooked (USDA: ~165 kcal/100g)
# Banana (USDA: 89 kcal/100g)
# White Rice, cooked (USDA: ~130 kcal/100g)

new_cases = []
start_idx = 100

def add_l1(input_text, food_name, weight_g, kcal_per_100g, is_cooked=False):
    global start_idx
    new_cases.append({
        "id": f"L1_{start_idx:03d}",
        "level": 1,
        "level_name": "Basic",
        "input": input_text,
        "expected_parse": [{
            "food_name": food_name,
            "weight_g": weight_g,
            "is_cooked_dish": is_cooked
        }],
        "expected_macros": {
            "calories": round(weight_g * (kcal_per_100g / 100.0), 1)
        }
    })
    start_idx += 1

# --- Oats Variations (USDA raw: 381.6) ---
add_l1("100g oats", "oats", 100, 381.6)
add_l1("250g oats", "oats", 250, 381.6)
add_l1("75g oats", "oats", 75, 381.6)
add_l1("40g oats", "oats", 40, 381.6)
add_l1("0.5 cup oats", "oats", 40, 381.6) # standard 0.5 cup rolled oats is ~40g
add_l1("one cup oats", "oats", 81, 381.6)
add_l1("rolled oats", "rolled oats", 40, 381.6) # fallback default serving ~40g
add_l1("raw oats", "raw oats", 40, 381.6)
add_l1("steel cut oats", "steel cut oats", 40, 381.6)

# --- Chicken Variations (USDA raw: 107.5, cooked: 165.0) ---
add_l1("100g raw chicken breast", "raw chicken breast", 100, 107.5)
add_l1("250g raw chicken breast", "raw chicken breast", 250, 107.5)
add_l1("100g cooked chicken breast", "cooked chicken breast", 100, 165.0)
add_l1("50g cooked chicken", "cooked chicken", 50, 165.0)
add_l1("one pound raw chicken breast", "raw chicken breast", 453, 107.5)
add_l1("half a pound cooked chicken", "cooked chicken", 226, 165.0)

# --- Banana Variations (USDA raw: 89) ---
add_l1("100g banana", "banana", 100, 89.0)
add_l1("1 medium banana", "banana", 118, 89.0)
add_l1("2 large bananas", "bananas", 272, 89.0) # 136g per large
add_l1("half a banana", "banana", 59, 89.0)
add_l1("sliced banana", "sliced banana", 118, 89.0)

# --- Rice Variations (USDA cooked: 130) ---
add_l1("100g cooked white rice", "cooked white rice", 100, 130.0)
add_l1("200g cooked rice", "cooked rice", 200, 130.0)
add_l1("1 cup cooked white rice", "cooked white rice", 158, 130.0)
add_l1("half cup cooked rice", "cooked rice", 79, 130.0)
add_l1("a bowl of cooked rice", "cooked rice", 200, 130.0)

# Merge
cases.extend(new_cases)

with open(cases_path, "w") as f:
    json.dump(cases, f, indent=2)

print(f"Added {len(new_cases)} new Level 1 cases.")
