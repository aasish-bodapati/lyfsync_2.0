"""
Build and export clean portion priors from USDA food_portion.csv.
Outputs: portion_priors.csv and portion_priors.json for human review.
Does NOT modify any database or backend code.
"""
import re
import json
import pandas as pd
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "data", "FoodData_Central_foundation_food_csv_2026-04-30")
OUT_DIR  = os.path.dirname(__file__)

portions = pd.read_csv(os.path.join(DATA_DIR, "food_portion.csv"))
food     = pd.read_csv(os.path.join(DATA_DIR, "food.csv"))
units    = pd.read_csv(os.path.join(DATA_DIR, "measure_unit.csv"))

# ── Step 1: Drop bad gram_weights ──────────────────────────────────────────────
portions = portions[portions["gram_weight"].notna()]
portions = portions[(portions["gram_weight"] > 0) & (portions["gram_weight"] < 2000)]

# ── Step 2: Keep only human-readable units ─────────────────────────────────────
HUMAN_UNITS = {
    1000, 1001, 1002,        # cup, tablespoon, teaspoon
    1018, 1027, 1028,        # breast, fillet, fruit
    1029, 1036, 1052,        # large, medium, small
    1030, 1038,              # lb, oz
    1031, 1053,              # leaf, stalk
    1043, 1044, 1059, 1071,  # piece, pieces, unit, each
    1048, 1090,              # scoop, bowl
    1050, 1051,              # slice, slices
    1054, 1058, 1072,        # steak, thigh, filet
    1099, 1104, 1107,        # egg, head, pancake
    1119, 1120,              # Banana, Onion
}
portions = portions[portions["measure_unit_id"].isin(HUMAN_UNITS)]

# ── Step 3: Join food names and unit names ─────────────────────────────────────
food_names  = food[["fdc_id", "description"]].drop_duplicates("fdc_id")
units_named = units.rename(columns={"id": "measure_unit_id", "name": "unit_name"})

df = portions.merge(food_names, on="fdc_id", how="left")
df = df.merge(units_named, on="measure_unit_id", how="left")

# ── Step 4: Simplify food names (strip brand codes, wave tags, parentheticals) ─
def simplify(raw: str) -> str:
    if pd.isna(raw):
        return ""
    s = raw.strip()
    # Remove anything in parentheses (sample codes, wave tags, store IDs)
    s = re.sub(r"\([^)]*\)", "", s)
    # Remove USDA sample codes like Tb31-C-8, Rs38-R-11, TL832-R-20, NFY120...
    s = re.sub(r"\b[A-Z]{1,4}\d+[-][A-Z]\d*[-]\d+\b", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\bNFY\w+\b", "", s, flags=re.IGNORECASE)
    # Remove rep / pass / region markers: "Rep 4", "Pass 2", "Region 4"
    s = re.sub(r",?\s*\b(Rep|Pass|Region)\s*\d+\b", "", s, flags=re.IGNORECASE)
    # Remove "Meaures & Comp" / "Measures & Comp" prefixes
    s = re.sub(r"^Meaures?\s*&\s*Comp\s*,?\s*", "", s, flags=re.IGNORECASE)
    # Remove trailing location tags like ", Chicago", ", Las Vegas", ", Ny/Nj1"
    s = re.sub(r",\s+[A-Z][a-zA-Z\s/\d]+$", "", s)
    # Remove trailing sample-location codes like "18C-Co-Swc-50"
    s = re.sub(r"\b\d+[A-Z]-[A-Z]+-\w+-\d+\b", "", s, flags=re.IGNORECASE)
    # Remove brand names following a comma in ALL CAPS (e.g., ", SARGENTO", ", KRAFT")
    s = re.sub(r",\s+[A-Z][A-Z\s&\'/]{2,}(?=\s*[,\-]|$)", "", s)
    # Remove stray trailing punctuation and collapse whitespace
    s = re.sub(r"[,\-]+\s*$", "", s)
    s = re.sub(r"\s{2,}", " ", s).strip(" ,")
    return s.title()


df["simplified_name"] = df["description"].apply(simplify)

# ── Step 5: Normalise amount to 1 (scale gram_weight) ─────────────────────────
# Some entries say "2 tablespoon = 35g". Normalise to "1 tablespoon = 17.5g"
df["gram_weight_per_1"] = df["gram_weight"] / df["amount"]

# ── Step 6: Deduplicate by (simplified_name, unit_name) → median weight ────────
grouped = (
    df.groupby(["simplified_name", "unit_name"], as_index=False)
    .agg(
        gram_weight=("gram_weight_per_1", "median"),
        n_samples=("gram_weight_per_1", "count"),
    )
)
grouped = grouped.sort_values(["simplified_name", "unit_name"])
grouped["gram_weight"] = grouped["gram_weight"].round(1)

print(f"Final unique (food, unit) pairs: {len(grouped)}")
print(f"\n--- Unit distribution ---")
print(grouped["unit_name"].value_counts().to_string())

print(f"\n--- Sample of 30 entries ---")
for _, row in grouped.sample(30, random_state=7).iterrows():
    label = f"1 {row['unit_name']} {row['simplified_name']} = {row['gram_weight']}g (n={row['n_samples']})"
    print(f"  {label}")

# ── Step 7: Export ─────────────────────────────────────────────────────────────
csv_path  = os.path.join(OUT_DIR, "portion_priors.csv")
json_path = os.path.join(OUT_DIR, "portion_priors.json")

grouped.to_csv(csv_path, index=False)

records = [
    {
        "food": row["simplified_name"],
        "unit": row["unit_name"],
        "gram_weight": row["gram_weight"],
        "n_samples": int(row["n_samples"])
    }
    for _, row in grouped.iterrows()
]
with open(json_path, "w") as f:
    json.dump(records, f, indent=2)

print(f"\nExported to:\n  {csv_path}\n  {json_path}")
