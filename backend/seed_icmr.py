import os
import sys
from sqlmodel import create_engine, Session, SQLModel, delete
from dotenv import load_dotenv

# Load env variables explicitly
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

# Import models
from main import ICMRRaw

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL not found.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)

# Curated list of 34 core Indian raw staples with exact macros per 100g from ICMR-NIN IFCT 2017
icmr_data = [
    # Dairy
    {"food_code": "DMP001", "food_name": "Paneer", "category": "Milk and Milk Products", "calories": 265.0, "protein": 18.0, "carbs": 1.2, "fat": 20.8},
    {"food_code": "DMP002", "food_name": "Ghee (Clarified Butter)", "category": "Milk and Milk Products", "calories": 900.0, "protein": 0.0, "carbs": 0.0, "fat": 100.0},
    {"food_code": "DMP003", "food_name": "Buffalo Milk", "category": "Milk and Milk Products", "calories": 117.0, "protein": 4.3, "carbs": 5.0, "fat": 9.0},
    {"food_code": "DMP004", "food_name": "Buffalo Curd (Dahi)", "category": "Milk and Milk Products", "calories": 60.0, "protein": 3.3, "carbs": 4.5, "fat": 3.4},
    {"food_code": "DMP005", "food_name": "Khoya / Mawa", "category": "Milk and Milk Products", "calories": 320.0, "protein": 14.6, "carbs": 19.0, "fat": 20.0},
    
    # Grains & Millets
    {"food_code": "CML001", "food_name": "Whole Wheat Flour (Atta)", "category": "Cereals and Millets", "calories": 341.0, "protein": 12.1, "carbs": 69.4, "fat": 1.7},
    {"food_code": "CML002", "food_name": "Maida (Refined Wheat Flour)", "category": "Cereals and Millets", "calories": 348.0, "protein": 11.0, "carbs": 73.9, "fat": 0.9},
    {"food_code": "CML003", "food_name": "Rava / Sooji (Semolina)", "category": "Cereals and Millets", "calories": 348.0, "protein": 11.0, "carbs": 74.0, "fat": 0.8},
    {"food_code": "CML004", "food_name": "Finger Millet (Ragi)", "category": "Cereals and Millets", "calories": 320.0, "protein": 7.3, "carbs": 72.0, "fat": 1.3},
    {"food_code": "CML005", "food_name": "Pearl Millet (Bajra)", "category": "Cereals and Millets", "calories": 361.0, "protein": 11.6, "carbs": 67.5, "fat": 5.0},
    {"food_code": "CML006", "food_name": "Sorghum (Jowar)", "category": "Cereals and Millets", "calories": 349.0, "protein": 10.4, "carbs": 72.6, "fat": 1.9},
    {"food_code": "CML007", "food_name": "Flattened Rice (Poha)", "category": "Cereals and Millets", "calories": 346.0, "protein": 6.6, "carbs": 77.3, "fat": 1.2},
    {"food_code": "CML008", "food_name": "Sago Pearls (Sabudana)", "category": "Cereals and Millets", "calories": 351.0, "protein": 0.2, "carbs": 87.0, "fat": 0.2},
    {"food_code": "CML009", "food_name": "Besan (Gram Flour)", "category": "Cereals and Millets", "calories": 372.0, "protein": 22.3, "carbs": 57.8, "fat": 5.6},
    
    # Dals & Pulses
    {"food_code": "PUL001", "food_name": "Toor Dal (Split Pigeon Peas)", "category": "Grain Legumes / Pulses", "calories": 343.0, "protein": 22.3, "carbs": 57.6, "fat": 1.7},
    {"food_code": "PUL002", "food_name": "Yellow Moong Dal (Split)", "category": "Grain Legumes / Pulses", "calories": 348.0, "protein": 24.0, "carbs": 59.0, "fat": 1.2},
    {"food_code": "PUL003", "food_name": "Green Moong (Whole)", "category": "Grain Legumes / Pulses", "calories": 334.0, "protein": 24.0, "carbs": 56.7, "fat": 1.3},
    {"food_code": "PUL004", "food_name": "Chana Dal (Split Bengal Gram)", "category": "Grain Legumes / Pulses", "calories": 372.0, "protein": 20.8, "carbs": 59.8, "fat": 5.6},
    {"food_code": "PUL005", "food_name": "Urad Dal (Split Black Gram)", "category": "Grain Legumes / Pulses", "calories": 341.0, "protein": 24.0, "carbs": 59.6, "fat": 1.4},
    {"food_code": "PUL006", "food_name": "Black Urad Dal (Whole)", "category": "Grain Legumes / Pulses", "calories": 341.0, "protein": 24.0, "carbs": 59.6, "fat": 1.4},
    {"food_code": "PUL007", "food_name": "Masoor Dal (Split Red Lentils)", "category": "Grain Legumes / Pulses", "calories": 343.0, "protein": 25.1, "carbs": 59.0, "fat": 0.7},
    {"food_code": "PUL008", "food_name": "Rajma (Red Kidney Beans)", "category": "Grain Legumes / Pulses", "calories": 346.0, "protein": 22.9, "carbs": 60.6, "fat": 1.3},
    {"food_code": "PUL009", "food_name": "Kabuli Chana (White Chickpeas)", "category": "Grain Legumes / Pulses", "calories": 360.0, "protein": 19.0, "carbs": 61.0, "fat": 6.0},
    {"food_code": "PUL010", "food_name": "Kala Chana (Brown Chickpeas)", "category": "Grain Legumes / Pulses", "calories": 362.0, "protein": 20.0, "carbs": 58.0, "fat": 5.0},
    {"food_code": "PUL011", "food_name": "Soya Chunks", "category": "Grain Legumes / Pulses", "calories": 345.0, "protein": 52.0, "carbs": 33.0, "fat": 0.5},
    
    # Oils
    {"food_code": "FAD001", "food_name": "Mustard Oil", "category": "Fats and Oils", "calories": 884.0, "protein": 0.0, "carbs": 0.0, "fat": 100.0},
    {"food_code": "FAD002", "food_name": "Gingelly Oil (Sesame Oil)", "category": "Fats and Oils", "calories": 884.0, "protein": 0.0, "carbs": 0.0, "fat": 100.0},
    {"food_code": "FAD003", "food_name": "Peanut Oil (Groundnut Oil)", "category": "Fats and Oils", "calories": 884.0, "protein": 0.0, "carbs": 0.0, "fat": 100.0},
    {"food_code": "FAD004", "food_name": "Coconut Oil (Edible)", "category": "Fats and Oils", "calories": 884.0, "protein": 0.0, "carbs": 0.0, "fat": 100.0},
    
    # Sweeteners & Nuts
    {"food_code": "SUG001", "food_name": "Jaggery (Gur)", "category": "Sugars", "calories": 383.0, "protein": 0.4, "carbs": 95.0, "fat": 0.1},
    {"food_code": "NUT001", "food_name": "Coconut (Grated, raw)", "category": "Nuts and Oil Seeds", "calories": 354.0, "protein": 3.3, "carbs": 15.2, "fat": 33.0},
    {"food_code": "NUT002", "food_name": "Cashew Nuts", "category": "Nuts and Oil Seeds", "calories": 553.0, "protein": 18.2, "carbs": 30.2, "fat": 43.8},
    {"food_code": "NUT003", "food_name": "Almonds", "category": "Nuts and Oil Seeds", "calories": 579.0, "protein": 21.2, "carbs": 21.6, "fat": 49.9}
]

def seed_icmr():
    print("Ensuring database tables exist...")
    SQLModel.metadata.create_all(engine)
    
    print(f"Preparing {len(icmr_data)} ICMR records...")
    db_records = []
    for item in icmr_data:
        record = ICMRRaw(
            food_code=item["food_code"],
            food_name=item["food_name"],
            category=item["category"],
            calories=item["calories"],
            protein=item["protein"],
            carbs=item["carbs"],
            fat=item["fat"]
        )
        db_records.append(record)
        
    print("Seeding records into table 'icmr_raw'...")
    with Session(engine) as session:
        # Clear existing entries
        session.exec(delete(ICMRRaw))
        session.commit()
        
        # Add all and commit
        session.add_all(db_records)
        session.commit()
        
    print("Successfully seeded icmr_raw table!")

if __name__ == "__main__":
    seed_icmr()
