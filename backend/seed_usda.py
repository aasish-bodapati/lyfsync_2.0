import os
import sys
import pandas as pd
from sqlmodel import create_engine, Session, SQLModel, delete
from dotenv import load_dotenv

# Load env variables explicitly
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

# Import models
from main import USDARaw

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL not found.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "FoodData_Central_foundation_food_csv_2026-04-30")

# Verified standard macro baselines (per 100g) for known zero-macro FDC items
standard_macros = {
    # 1. Pure Oils (884 kcal, 100g fat)
    748278: {"calories": 884.0, "protein": 0.0, "carbs": 0.0, "fat": 100.0},     # Canola Oil
    748323: {"calories": 884.0, "protein": 0.0, "carbs": 0.0, "fat": 100.0},     # Corn Oil
    748366: {"calories": 884.0, "protein": 0.0, "carbs": 0.0, "fat": 100.0},     # Soybean Oil
    748608: {"calories": 884.0, "protein": 0.0, "carbs": 0.0, "fat": 100.0},     # Extra Virgin Olive Oil
    1750348: {"calories": 884.0, "protein": 0.0, "carbs": 0.0, "fat": 100.0},    # Peanut Oil
    1750349: {"calories": 884.0, "protein": 0.0, "carbs": 0.0, "fat": 100.0},    # Sunflower Oil
    1750350: {"calories": 884.0, "protein": 0.0, "carbs": 0.0, "fat": 100.0},    # Safflower Oil
    1750351: {"calories": 884.0, "protein": 0.0, "carbs": 0.0, "fat": 100.0},    # Extra Light Olive Oil
    
    # 2. Pasta / Macaroni (Dry)
    2758998: {"calories": 371.0, "protein": 13.0, "carbs": 75.0, "fat": 1.5},    # Dry Spaghetti
    2758999: {"calories": 348.0, "protein": 14.6, "carbs": 75.0, "fat": 1.5},    # Whole Grain Spaghetti
    2759000: {"calories": 348.0, "protein": 14.6, "carbs": 75.0, "fat": 1.5},    # Whole Grain Spaghetti 2
    
    # 3. Breads & Tortillas
    2758993: {"calories": 265.0, "protein": 9.0, "carbs": 49.0, "fat": 3.2},     # White Bread
    2758994: {"calories": 247.0, "protein": 13.0, "carbs": 41.0, "fat": 3.4},    # Whole Wheat Bread
    2758995: {"calories": 265.0, "protein": 10.2, "carbs": 43.0, "fat": 4.2},    # Multigrain Bread
    2758996: {"calories": 312.0, "protein": 8.0, "carbs": 50.0, "fat": 8.0},     # Wheat Tortilla
    2758997: {"calories": 218.0, "protein": 6.0, "carbs": 45.0, "fat": 3.0},     # Corn Tortilla
    
    # 4. Spreads & Dressings
    2758989: {"calories": 588.0, "protein": 25.0, "carbs": 20.0, "fat": 50.0},    # Peanut Butter
    2758990: {"calories": 321.0, "protein": 8.0, "carbs": 54.0, "fat": 9.0},     # Sweetened Condensed Milk
    2758986: {"calories": 680.0, "protein": 1.0, "carbs": 1.0, "fat": 75.0},     # Mayonnaise
    2758987: {"calories": 290.0, "protein": 0.0, "carbs": 8.0, "fat": 29.0},     # Italian Dressing
    2758988: {"calories": 430.0, "protein": 1.0, "carbs": 7.0, "fat": 44.0},     # Ranch Dressing
    
    # 5. Lunchmeats & Charcuterie
    2759001: {"calories": 100.0, "protein": 15.0, "carbs": 3.0, "fat": 2.0},     # Turkey Breast Slices
    2759002: {"calories": 110.0, "protein": 16.0, "carbs": 2.0, "fat": 4.0},     # Ham Slices
    2759003: {"calories": 120.0, "protein": 18.0, "carbs": 1.0, "fat": 4.0},     # Roast Beef Slices
    2759004: {"calories": 100.0, "protein": 16.0, "carbs": 3.0, "fat": 2.0},     # Chicken Breast Slices
    2759005: {"calories": 380.0, "protein": 20.0, "carbs": 1.0, "fat": 32.0},    # Salami Slices
    2759006: {"calories": 490.0, "protein": 20.0, "carbs": 1.0, "fat": 44.0},    # Pepperoni Slices
    2758991: {"calories": 300.0, "protein": 12.0, "carbs": 3.0, "fat": 26.0},    # Beef Bologna
    2758992: {"calories": 300.0, "protein": 12.0, "carbs": 3.0, "fat": 26.0},    # Classic Bologna
    
    # 6. Beans & Edamame
    2758982: {"calories": 155.0, "protein": 6.0, "carbs": 29.0, "fat": 1.0},     # Baked beans with pork
    2758983: {"calories": 155.0, "protein": 6.0, "carbs": 29.0, "fat": 1.0},     # Baked beans vegetarian
    2758984: {"calories": 90.0, "protein": 6.0, "carbs": 16.0, "fat": 1.0},      # Refried beans
    2758985: {"calories": 90.0, "protein": 6.0, "carbs": 16.0, "fat": 1.0},      # Refried beans vegetarian
    2758981: {"calories": 121.0, "protein": 12.0, "carbs": 9.0, "fat": 5.0},     # Prepared Edamame
    
    # 7. Fruits & Juices
    2758975: {"calories": 21.0, "protein": 0.9, "carbs": 4.5, "fat": 0.2},       # Rhubarb
    2758976: {"calories": 308.0, "protein": 0.1, "carbs": 82.0, "fat": 1.4},     # Dried Cranberries
    2758977: {"calories": 32.0, "protein": 0.6, "carbs": 8.0, "fat": 0.1},       # Grapefruit
    2758978: {"calories": 240.0, "protein": 2.2, "carbs": 64.0, "fat": 0.4},     # Prunes
    2758979: {"calories": 299.0, "protein": 3.0, "carbs": 79.0, "fat": 0.5},     # Golden Raisins
    2758980: {"calories": 299.0, "protein": 3.0, "carbs": 79.0, "fat": 0.5},     # Dark Raisins
    2727588: {"calories": 54.0, "protein": 0.1, "carbs": 13.0, "fat": 0.3}       # Pomegranate Juice
}

def seed_usda():
    print("Ensuring database tables exist...")
    SQLModel.metadata.create_all(engine)

    food_csv = os.path.join(DATA_DIR, "food.csv")
    nutrient_csv = os.path.join(DATA_DIR, "food_nutrient.csv")

    if not os.path.exists(food_csv) or not os.path.exists(nutrient_csv):
        print("Error: USDA CSV files not found.")
        sys.exit(1)

    print("Loading food.csv...")
    food_df = pd.read_csv(food_csv)
    # Filter for Foundation Foods only (data_type == 'foundation_food')
    foundation_foods = food_df[food_df["data_type"] == "foundation_food"]
    foundation_ids = set(foundation_foods["fdc_id"])
    print(f"Found {len(foundation_foods)} foundation foods.")

    print("Loading food_nutrient.csv...")
    # Target nutrient IDs:
    # 1008: Energy (kcal)
    # 1003: Protein (g)
    # 1005: Carbohydrate, by difference (g)
    # 1004: Total lipid (fat) (g)
    target_nutrients = {1008, 1003, 1005, 1004}

    nut_df = pd.read_csv(nutrient_csv)
    # Filter for foundation foods and target nutrients
    filtered_nut = nut_df[
        (nut_df["fdc_id"].isin(foundation_ids)) &
        (nut_df["nutrient_id"].isin(target_nutrients))
    ]

    print("Building nutrient mappings...")
    pivot_df = filtered_nut.pivot_table(
        index="fdc_id",
        columns="nutrient_id",
        values="amount",
        aggfunc="max"
    ).fillna(0.0)

    # Rename columns to match database schema
    rename_dict = {
        1008: "calories",
        1003: "protein",
        1005: "carbs",
        1004: "fat"
    }
    pivot_df = pivot_df.rename(columns=rename_dict)

    # Ensure all target columns exist in pivot_df
    for col in rename_dict.values():
        if col not in pivot_df.columns:
            pivot_df[col] = 0.0

    print("Preparing records for insertion...")
    db_records = []
    for _, row in foundation_foods.iterrows():
        fdc_id = int(row["fdc_id"])
        description = str(row["description"])
        
        # Get nutrients from pivot table
        nutrients = pivot_df.loc[fdc_id] if fdc_id in pivot_df.index else None
        
        calories = float(nutrients["calories"]) if nutrients is not None else 0.0
        protein = float(nutrients["protein"]) if nutrients is not None else 0.0
        carbs = float(nutrients["carbs"]) if nutrients is not None else 0.0
        fat = float(nutrients["fat"]) if nutrients is not None else 0.0
        
        # Apply standard macros fallback if the FDC sample is known to have zero macros in FDC release
        if fdc_id in standard_macros:
            m = standard_macros[fdc_id]
            calories = m["calories"]
            protein = m["protein"]
            carbs = m["carbs"]
            fat = m["fat"]
        
        # Apply Atwater fallback if calories are missing/zero but macros exist
        if calories == 0.0 and (protein > 0.0 or carbs > 0.0 or fat > 0.0):
            calories = round((protein * 4.0) + (carbs * 4.0) + (fat * 9.0), 2)
            
        record = USDARaw(
            fdc_id=fdc_id,
            description=description,
            calories=calories,
            protein=protein,
            carbs=carbs,
            fat=fat
        )
        db_records.append(record)

    print(f"Seeding {len(db_records)} records into table 'usda_raw'...")
    with Session(engine) as session:
        # Clear existing entries in usda_raw first to prevent duplicates
        session.exec(delete(USDARaw))
        session.commit()
        
        # Add all and commit
        session.add_all(db_records)
        session.commit()
        
    print("Successfully seeded usda_raw table!")

if __name__ == "__main__":
    seed_usda()
