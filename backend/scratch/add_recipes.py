import os
import psycopg2
from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")

def add_recipe_table():
    print(f"Connecting to database: {DATABASE_URL}")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    print("Adding recipes table...")
    cursor.execute("DROP TABLE IF EXISTS recipes;")
    
    cursor.execute("""
    CREATE TABLE recipes (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL UNIQUE,
        cuisine VARCHAR(100) NOT NULL,
        category VARCHAR(100) NOT NULL,
        description TEXT,
        ingredients TEXT NOT NULL,
        cooking_instructions TEXT NOT NULL,
        prep_time_mins INTEGER,
        cook_time_mins INTEGER,
        calories FLOAT NOT NULL DEFAULT 0.0,
        protein FLOAT NOT NULL DEFAULT 0.0,
        carbs FLOAT NOT NULL DEFAULT 0.0,
        fat FLOAT NOT NULL DEFAULT 0.0,
        typical_serving_grams FLOAT NOT NULL DEFAULT 0.0,
        servings_per_recipe INTEGER NOT NULL DEFAULT 4,
        source VARCHAR NOT NULL DEFAULT 'openai',
        vector_embedding VECTOR(1536),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    
    print("Table created successfully!")
    conn.close()

if __name__ == "__main__":
    add_recipe_table()
