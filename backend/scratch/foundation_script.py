import os
import csv
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# Define absolute paths
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BACKEND_DIR, "data", "FoodData_Central_foundation_food_csv_2026-04-30")

load_dotenv(os.path.join(BACKEND_DIR, ".env"))
DATABASE_URL = os.getenv("DATABASE_URL")

def import_and_denormalize():
    print(f"Connecting to database: {DATABASE_URL}")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # 0. Enable pgvector extension
    print("Enabling pgvector extension...")
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    conn.commit()

    # 1. Drop and Recreate Raw/Flat Tables
    print("Recreating database tables...")
    cursor.execute("DROP TABLE IF EXISTS food;")
    cursor.execute("DROP TABLE IF EXISTS nutrient;")
    cursor.execute("DROP TABLE IF EXISTS food_nutrient;")
    cursor.execute("DROP TABLE IF EXISTS food_nutrition;")
    
    cursor.execute("""
    CREATE TABLE food (
        fdc_id INTEGER PRIMARY KEY,
        data_type TEXT,
        description TEXT,
        food_category_id INTEGER,
        publication_date TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE nutrient (
        id INTEGER PRIMARY KEY,
        name TEXT,
        unit_name TEXT,
        nutrient_nbr TEXT,
        rank REAL
    );
    """)

    cursor.execute("""
    CREATE TABLE food_nutrient (
        id INTEGER PRIMARY KEY,
        fdc_id INTEGER,
        nutrient_id INTEGER,
        amount REAL,
        data_points INTEGER,
        derivation_id INTEGER,
        min TEXT,
        max TEXT,
        median TEXT,
        footnote TEXT,
        min_year_acquired TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE food_nutrition (
        fdc_id INTEGER PRIMARY KEY,
        description TEXT NOT NULL,
        calories REAL NOT NULL DEFAULT 0.0,
        protein REAL NOT NULL DEFAULT 0.0,
        carbs REAL NOT NULL DEFAULT 0.0,
        fat REAL NOT NULL DEFAULT 0.0,
        source TEXT NOT NULL DEFAULT 'usda',
        vector_embedding VECTOR(1536)
    );
    """)
    conn.commit()

    # 2. Import food.csv (Filter for foundation_food only)
    food_path = os.path.join(DATA_DIR, "food.csv")
    print(f"Importing {food_path}...")
    foundation_foods = []
    foundation_fdc_ids = set()
    with open(food_path, mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if row[1] == "foundation_food":
                row = [None if val == "" else val for val in row]
                foundation_foods.append(row)
                foundation_fdc_ids.add(int(row[0]))
                
        execute_values(
            cursor,
            "INSERT INTO food (fdc_id, data_type, description, food_category_id, publication_date) VALUES %s",
            foundation_foods
        )
        conn.commit()

    # 3. Import nutrient.csv
    nutrient_path = os.path.join(DATA_DIR, "nutrient.csv")
    print(f"Importing {nutrient_path}...")
    with open(nutrient_path, mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        
        # Convert empty strings to None for proper NULL insertion
        nutrients = [[None if val == "" else val for val in row] for row in reader]
        
        execute_values(
            cursor,
            "INSERT INTO nutrient (id, name, unit_name, nutrient_nbr, rank) VALUES %s",
            nutrients
        )
        conn.commit()

    # 4. Import food_nutrient.csv (Filter for nutrients belonging to foundation foods only)
    food_nutrient_path = os.path.join(DATA_DIR, "food_nutrient.csv")
    print(f"Importing {food_nutrient_path}...")
    foundation_nutrients = []
    with open(food_nutrient_path, mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if int(row[1]) in foundation_fdc_ids:
                row = [None if val == "" else val for val in row]
                foundation_nutrients.append(row)
                
        execute_values(
            cursor,
            "INSERT INTO food_nutrient (id, fdc_id, nutrient_id, amount, data_points, derivation_id, min, max, median, footnote, min_year_acquired) VALUES %s",
            foundation_nutrients
        )
        conn.commit()

    # 5. Pivot and insert data into 'food_nutrition' (CORRECT ORDER)
    print("Pivoting data into flat 'food_nutrition' table...")
    cursor.execute("BEGIN TRANSACTION;")
    cursor.execute("""
    INSERT INTO food_nutrition (fdc_id, description, calories, protein, carbs, fat, source)
    SELECT 
        f.fdc_id,
        f.description,
        MAX(CASE WHEN fn.nutrient_id = 1008 THEN fn.amount ELSE 0.0 END) as calories,
        MAX(CASE WHEN fn.nutrient_id = 1003 THEN fn.amount ELSE 0.0 END) as protein,
        MAX(CASE WHEN fn.nutrient_id = 1005 THEN fn.amount ELSE 0.0 END) as carbs,
        MAX(CASE WHEN fn.nutrient_id = 1004 THEN fn.amount ELSE 0.0 END) as fat,
        'usda' as source
    FROM food f
    LEFT JOIN food_nutrient fn ON f.fdc_id = fn.fdc_id
    GROUP BY f.fdc_id, f.description;
    """)
    conn.commit()

    # 6. Drop the old heavy tables
    print("Cleaning up raw USDA tables...")
    cursor.execute("DROP TABLE IF EXISTS food;")
    cursor.execute("DROP TABLE IF EXISTS nutrient;")
    cursor.execute("DROP TABLE IF EXISTS food_nutrient;")
    conn.commit()

    # 7. Show the final results
    cursor.execute("SELECT COUNT(*) FROM food_nutrition")
    row = cursor.fetchone()
    count = row[0] if row else 0
    print(f"\nAll-in-one Seeding & Denormalization completed successfully!")
    print(f"  * Table 'food_nutrition' created with {count} rows.")
    
    # Print the first 5 records as a sample
    print("\nSample records:")
    cursor.execute("SELECT fdc_id, description, calories, protein, carbs, fat FROM food_nutrition LIMIT 5")
    sample = cursor.fetchall()
    for row in sample:
        print(f"  ID: {row[0]} | Name: {row[1][:40]} | Calories: {row[2]} kcal | P: {row[3]}g | C: {row[4]}g | F: {row[5]}g")

    conn.close()

if __name__ == "__main__":
    import_and_denormalize()
