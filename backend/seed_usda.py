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
    foundation_foods = food_df[food_df["data_type"] == "foundation_food"]
    print(f"Found {len(foundation_foods)} foundation foods.")

    foundation_ids = set(foundation_foods["fdc_id"])

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
