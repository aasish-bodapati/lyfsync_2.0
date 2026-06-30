import os
import csv
import sys
from sqlmodel import create_engine, Session, SQLModel
from dotenv import load_dotenv

# Load env variables explicitly
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

# Import models to ensure they are registered
from main import Recipe

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL not found in environment variables.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)

CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "IndianFoodDatasetCSV.csv")

def clean_text(text: str) -> str:
    if not text:
        return ""
    # Clean non-breaking spaces (\xa0)
    return text.replace("\xa0", " ").strip()

def seed():
    print("Ensuring database tables exist...")
    SQLModel.metadata.create_all(engine)
    
    print(f"Reading and cleaning recipes from {CSV_PATH}...")
    if not os.path.exists(CSV_PATH):
        print(f"Error: CSV file not found at {CSV_PATH}")
        sys.exit(1)
        
    recipes_to_insert = []
    
    with open(CSV_PATH, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 1. Skip rows with missing ingredients
            ingredients = row.get("Ingredients")
            if not ingredients or ingredients.strip() == "":
                continue
                
            # 2. Extract values and clean text/whitespace
            try:
                recipe = Recipe(
                    srno=int(row["Srno"]),
                    recipe_name=clean_text(row["RecipeName"]),
                    translated_recipe_name=clean_text(row["TranslatedRecipeName"]),
                    ingredients=clean_text(row["Ingredients"]),
                    translated_ingredients=clean_text(row["TranslatedIngredients"]),
                    prep_time_in_mins=int(row["PrepTimeInMins"]) if row["PrepTimeInMins"] else 0,
                    cook_time_in_mins=int(row["CookTimeInMins"]) if row["CookTimeInMins"] else 0,
                    total_time_in_mins=int(row["TotalTimeInMins"]) if row["TotalTimeInMins"] else 0,
                    servings=int(row["Servings"]) if row["Servings"] else 1,
                    cuisine=clean_text(row["Cuisine"]),
                    course=clean_text(row["Course"]),
                    diet=clean_text(row["Diet"]),
                    instructions=clean_text(row["Instructions"]),
                    translated_instructions=clean_text(row["TranslatedInstructions"]),
                    url=clean_text(row["URL"])
                )
                recipes_to_insert.append(recipe)
            except Exception as ex:
                print(f"Skipping row Srno {row.get('Srno')} due to parsing error: {ex}")
                
    total_recipes = len(recipes_to_insert)
    print(f"Cleaned {total_recipes} recipes. Starting batch database inserts...")
    
    # 3. Batch inserts to prevent Supabase connection timeouts
    batch_size = 200
    inserted_count = 0
    
    with Session(engine) as session:
        for i in range(0, total_recipes, batch_size):
            batch = recipes_to_insert[i : i + batch_size]
            try:
                session.add_all(batch)
                session.commit()
                inserted_count += len(batch)
                print(f"  Inserted {inserted_count}/{total_recipes} recipes...")
            except Exception as e:
                session.rollback()
                print(f"Error inserting batch starting at index {i}: {e}")
                
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    seed()
