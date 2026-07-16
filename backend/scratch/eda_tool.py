import os
import csv
import sys

# Define path to the CSV directory relative to this script
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
    "data", 
    "FoodData_Central_foundation_food_csv_2026-04-30"
)

def load_nutrients():
    """Loads nutrient list: {nutrient_id: (name, unit_name)}"""
    path = os.path.join(DATA_DIR, "nutrient.csv")
    nutrients = {}
    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            nutrients[row["id"]] = (row["name"], row["unit_name"])
    return nutrients

def load_measure_units():
    """Loads measure units: {unit_id: name}"""
    path = os.path.join(DATA_DIR, "measure_unit.csv")
    units = {}
    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            units[row["id"]] = row["name"]
    return units

def search_food(query: str):
    """Searches food.csv for a description match."""
    path = os.path.join(DATA_DIR, "food.csv")
    results = []
    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if query.lower() in row["description"].lower():
                results.append({
                    "fdc_id": row["fdc_id"],
                    "description": row["description"],
                    "data_type": row["data_type"]
                })
    # Sort results so foundation_food comes first
    results.sort(key=lambda x: 0 if x["data_type"] == "foundation_food" else 1)
    return results

def get_food_nutrients(fdc_id: str, nutrients_map: dict):
    """Gets all nutrient values for a specific fdc_id."""
    path = os.path.join(DATA_DIR, "food_nutrient.csv")
    food_nutrients = []
    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["fdc_id"] == fdc_id:
                nut_id = row["nutrient_id"]
                if nut_id in nutrients_map:
                    name, unit = nutrients_map[nut_id]
                    food_nutrients.append({
                        "name": name,
                        "amount": float(row["amount"]),
                        "unit": unit
                    })
    return food_nutrients

def get_food_portions(fdc_id: str, units_map: dict):
    """Gets portion size conversions to grams for a specific fdc_id."""
    path = os.path.join(DATA_DIR, "food_portion.csv")
    portions = []
    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["fdc_id"] == fdc_id:
                unit_id = row["measure_unit_id"]
                unit_name = units_map.get(unit_id, f"Unit-{unit_id}")
                portions.append({
                    "amount": float(row["amount"]) if row["amount"] else 1.0,
                    "unit": unit_name,
                    "description": row["portion_description"],
                    "gram_weight": float(row["gram_weight"]) if row["gram_weight"] else 0.0
                })
    return portions

def run_eda(query: str):
    print("=" * 60)
    print(f"LOADING DATASETS FROM {DATA_DIR}...")
    nutrients_map = load_nutrients()
    units_map = load_measure_units()
    
    print(f"SEARCHING FOR '{query}'...")
    foods = search_food(query)
    print(f"Found {len(foods)} matches.")
    print("=" * 60)
    
    # Show the first 5 matches in detail
    for food in foods[:5]:
        print(f"\nFood ID: {food['fdc_id']}")
        print(f"Description: {food['description']}")
        print(f"Data Source: {food['data_type']}")
        
        print("\n--- Portions (Weight Mapping) ---")
        portions = get_food_portions(food['fdc_id'], units_map)
        if not portions:
            print("  No portion data found (measured in standard 100g increments).")
        for p in portions:
            desc = f" ({p['description']})" if p['description'] else ""
            print(f"  * {p['amount']} {p['unit']}{desc} = {p['gram_weight']}g")
            
        print("\n--- Core Nutrients (per 100g) ---")
        nutrients = get_food_nutrients(food['fdc_id'], nutrients_map)
        
        # Display key macronutrients
        core_ids = ["Protein", "Total lipid (fat)", "Carbohydrate, by difference", "Energy"]
        for nut in nutrients:
            if any(core in nut["name"] for core in core_ids):
                print(f"  * {nut['name']}: {nut['amount']} {nut['unit']}")
        print("-" * 60)

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "hummus"
    run_eda(query)
