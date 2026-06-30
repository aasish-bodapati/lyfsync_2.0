import os
import sys
from sqlmodel import create_engine, Session, select
from dotenv import load_dotenv

# Load env variables explicitly
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

from main import USDARaw

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL not found.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)

# Verified standard macro baselines (per 100g) for the 42 zero-macro items
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

def correct_database():
    print(f"Connecting to database and updating {len(standard_macros)} items...")
    
    updated_count = 0
    with Session(engine) as session:
        for fdc_id, macros in standard_macros.items():
            db_row = session.exec(select(USDARaw).where(USDARaw.fdc_id == fdc_id)).first()
            if db_row:
                db_row.calories = macros["calories"]
                db_row.protein = macros["protein"]
                db_row.carbs = macros["carbs"]
                db_row.fat = macros["fat"]
                session.add(db_row)
                updated_count += 1
                
        session.commit()
        
    print(f"Successfully updated {updated_count} rows in Supabase usda_raw table!")

if __name__ == "__main__":
    correct_database()
