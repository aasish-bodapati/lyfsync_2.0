import os
import psycopg2
from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")

def migrate():
    print(f"Connecting to database: {DATABASE_URL}")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    print("Adding 'source' column and setting default to 'usda'...")
    cursor.execute("ALTER TABLE food_nutrition ADD COLUMN IF NOT EXISTS source VARCHAR NOT NULL DEFAULT 'usda';")
    conn.commit()
    
    print("Migration completed successfully!")
    conn.close()

if __name__ == "__main__":
    migrate()
