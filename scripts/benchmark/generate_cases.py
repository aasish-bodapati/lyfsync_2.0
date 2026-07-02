import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
from sqlmodel import Session, select, create_engine
from main import USDARaw, ICMRRaw, Staple
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "backend", ".env"))
engine = create_engine(os.getenv("DATABASE_URL"))

def get_macros(fdc_id):
    with Session(engine) as session:
        item = session.exec(select(USDARaw).where(USDARaw.fdc_id == fdc_id)).first()
        if not item:
            return {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
        return {"calories": item.calories, "protein": item.protein, "carbs": item.carbs, "fat": item.fat, "name": item.description}

def scale(macros, weight_g):
    factor = weight_g / 100.0
    return {
        "calories": macros["calories"] * factor,
        "protein": macros["protein"] * factor,
        "carbs": macros["carbs"] * factor,
        "fat": macros["fat"] * factor
    }

def add_macros(m1, m2):
    return {
        "calories": round(m1["calories"] + m2["calories"], 2),
        "protein": round(m1["protein"] + m2["protein"], 2),
        "carbs": round(m1["carbs"] + m2["carbs"], 2),
        "fat": round(m1["fat"] + m2["fat"], 2)
    }

# FDC IDs
EGG_ID = 323604
OATS_ID = 2346396
MILK_ID = 746782
CHICKEN_BREAST_ID = 331960
RICE_ID = 2512381

egg = get_macros(EGG_ID)
oats = get_macros(OATS_ID)
milk = get_macros(MILK_ID)
chicken = get_macros(CHICKEN_BREAST_ID)
rice = get_macros(RICE_ID)

cases = [
    {
        "id": "L1_001",
        "level": 1,
        "level_name": "Basic",
        "input": "100g raw oats",
        "gold_standard": scale(oats, 100),
        "tolerance": {"calorie_pct": 5, "protein_pct": 5, "carbs_pct": 5, "fat_pct": 5}
    },
    {
        "id": "L1_002",
        "level": 1,
        "level_name": "Basic",
        "input": "200g chicken breast",
        "gold_standard": scale(chicken, 200),
        "tolerance": {"calorie_pct": 5, "protein_pct": 5, "carbs_pct": 5, "fat_pct": 5}
    },
    {
        "id": "L2_001",
        "level": 2,
        "level_name": "Natural Language",
        "input": "A bowl of oats with 100ml milk.",
        "gold_standard": add_macros(scale(oats, 50), scale(milk, 100)), # 1 bowl oats = 50g
        "tolerance": {"calorie_pct": 10, "protein_pct": 10, "carbs_pct": 10, "fat_pct": 10}
    },
    {
        "id": "L2_002",
        "level": 2,
        "level_name": "Natural Language",
        "input": "Two eggs.",
        "gold_standard": scale(egg, 100), # 1 large egg = 50g
        "tolerance": {"calorie_pct": 10, "protein_pct": 10, "carbs_pct": 10, "fat_pct": 10}
    },
    {
        "id": "L3_001",
        "level": 3,
        "level_name": "Cooking Methods",
        "input": "Chicken breast cooked in a tablespoon of olive oil. 200g chicken.",
        # 1 tbsp oil = 14g fat. Oil macros: 884 kcal/100g -> 123.76 kcal, 14g fat.
        "gold_standard": add_macros(scale(chicken, 200), {"calories": 123.76, "protein": 0, "carbs": 0, "fat": 14.0}),
        "tolerance": {"calorie_pct": 10, "protein_pct": 10, "carbs_pct": 10, "fat_pct": 10}
    },
    {
        "id": "L5_001",
        "level": 5,
        "level_name": "Ambiguous Human Language",
        "input": "A little oil on my 200g chicken breast.",
        # A little oil = 1 tsp = ~4.5g fat -> 39.7 kcal
        "gold_standard": add_macros(scale(chicken, 200), {"calories": 39.78, "protein": 0, "carbs": 0, "fat": 4.5}),
        "tolerance": {"calorie_pct": 15, "protein_pct": 15, "carbs_pct": 15, "fat_pct": 20}
    },
    {
        "id": "L11_001",
        "level": 11,
        "level_name": "Implicit Quantities",
        "input": "Finished about two thirds of my 300g chicken breast.",
        "gold_standard": scale(chicken, 200),
        "tolerance": {"calorie_pct": 10, "protein_pct": 10, "carbs_pct": 10, "fat_pct": 10}
    }
]

with open(os.path.join(os.path.dirname(__file__), "cases.json"), "w") as f:
    json.dump(cases, f, indent=2)

print("Generated cases.json with precise DB macros.")
