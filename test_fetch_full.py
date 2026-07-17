import psycopg2
from dotenv import load_dotenv
import os

load_dotenv("backend/.env")
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS food_nutrition;")
cursor.execute("""
CREATE TABLE food_nutrition (
    fdc_id INTEGER PRIMARY KEY,
    description TEXT NOT NULL,
    calories REAL NOT NULL DEFAULT 0.0,
    protein REAL NOT NULL DEFAULT 0.0,
    carbs REAL NOT NULL DEFAULT 0.0,
    fat REAL NOT NULL DEFAULT 0.0,
    vector_embedding VECTOR(1536)
);
""")
conn.commit()

cursor.execute("DROP TABLE IF EXISTS food;")
cursor.execute("DROP TABLE IF EXISTS nutrient;")
cursor.execute("DROP TABLE IF EXISTS food_nutrient;")
conn.commit()

cursor.execute("SELECT COUNT(*) FROM food_nutrition")
print("COUNT:", cursor.fetchone())
