"""
EDA: Filter food_portion.csv to clean, human-meaningful portion priors.
Does NOT join or write to anything. Just prints analysis.
"""
import pandas as pd
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "data", "FoodData_Central_foundation_food_csv_2026-04-30")

portions = pd.read_csv(os.path.join(DATA_DIR, "food_portion.csv"))
food = pd.read_csv(os.path.join(DATA_DIR, "food.csv"))
units = pd.read_csv(os.path.join(DATA_DIR, "measure_unit.csv"))

print(f"Total rows in food_portion.csv: {len(portions)}")

# --- Stage 1: Drop garbage gram_weights ---
before = len(portions)
portions = portions[portions["gram_weight"].notna()]
portions = portions[portions["gram_weight"] > 0]
portions = portions[portions["gram_weight"] < 2000]
print(f"\nAfter dropping null/zero/huge gram_weight: {len(portions)} (dropped {before - len(portions)})")

# --- Stage 2: Keep only natural human portion units ---
HUMAN_UNITS = {
    1000,   # cup
    1001,   # tablespoon
    1002,   # teaspoon
    1018,   # breast
    1027,   # fillet
    1028,   # fruit
    1029,   # large
    1030,   # lb
    1031,   # leaf
    1036,   # medium
    1038,   # oz
    1043,   # piece
    1044,   # pieces
    1048,   # scoop
    1050,   # slice
    1051,   # slices
    1052,   # small
    1053,   # stalk
    1054,   # steak
    1058,   # thigh
    1059,   # unit
    1071,   # each
    1072,   # filet
    1090,   # bowl
    1099,   # egg
    1104,   # head
    1107,   # pancake
    1119,   # Banana
    1120,   # Onion
}
before = len(portions)
portions = portions[portions["measure_unit_id"].isin(HUMAN_UNITS)]
print(f"After keeping only human-readable units: {len(portions)} (dropped {before - len(portions)})")

# --- Stage 3: Keep only best entry per (fdc_id, measure_unit_id) ---
portions_sorted = portions.sort_values("seq_num", na_position="last")
portions_deduped = portions_sorted.drop_duplicates(subset=["fdc_id", "measure_unit_id"], keep="first")
print(f"After deduplicating per (fdc_id, unit): {len(portions_deduped)}")

# --- Stage 4: Join food names for human reading ---
food_names = food[["fdc_id", "description"]].drop_duplicates()
merged = portions_deduped.merge(food_names, on="fdc_id", how="left")
units_named = units.rename(columns={"id": "measure_unit_id", "name": "unit_name"})
merged = merged.merge(units_named, on="measure_unit_id", how="left")

# Build human-readable label
merged["label"] = (
    merged["amount"].apply(lambda x: f"{x:g}") + " " +
    merged["unit_name"].fillna("") + " " +
    merged["description"].fillna("") + " = " +
    merged["gram_weight"].apply(lambda x: f"{x:g}") + "g"
)

print(f"\n--- Sample of {min(30, len(merged))} filtered portion priors ---")
for _, row in merged.sample(min(30, len(merged)), random_state=42).iterrows():
    print(f"  {row['label']}")

print(f"\n--- Unit distribution after filtering ---")
unit_counts = merged["unit_name"].value_counts()
print(unit_counts.to_string())

print(f"\n--- Final count: {len(merged)} clean portion priors ---")
