import os
import csv
import psycopg2
import json
from openai import OpenAI
from dotenv import load_dotenv

# Define absolute paths
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv(os.path.join(BACKEND_DIR, ".env"))
DATABASE_URL = os.getenv("DATABASE_URL")

def generate_embeddings():
    print(f"Connecting to database: {DATABASE_URL}")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # 1. Add vector_embedding column if it doesn't exist
    print("Checking if 'vector_embedding' column exists...")
    try:
        cursor.execute("ALTER TABLE food_nutrition ADD COLUMN IF NOT EXISTS vector_embedding VECTOR(1536);")
        conn.commit()
        print("  * Ensured 'vector_embedding' column exists in 'food_nutrition' table.")
    except Exception as e:
        print(f"  * Warning: {e}")
        conn.rollback()

    # 2. Fetch foods that need embeddings
    print("Fetching foods that need vector embeddings...")
    cursor.execute(
        "SELECT fdc_id, description FROM food_nutrition WHERE vector_embedding IS NULL"
    )
    foods = cursor.fetchall()
    
    total_foods = len(foods)
    if total_foods == 0:
        print("All foods already have embeddings. Nothing to do!")
        conn.close()
        return

    print(f"Found {total_foods} foods needing vector embeddings.")

    # 3. Initialize OpenAI Client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("CRITICAL ERROR: 'OPENAI_API_KEY' is not set in your .env file.")
        conn.close()
        return
        
    client = OpenAI(api_key=api_key)

    # 4. Generate and update in batches
    batch_size = 100
    print("Generating embeddings via OpenAI...")
    
    for i in range(0, total_foods, batch_size):
        batch = foods[i:i+batch_size]
        descriptions = [row[1] for row in batch]
        ids = [row[0] for row in batch]
        
        try:
            response = client.embeddings.create(
                input=descriptions,
                model="text-embedding-3-small"
            )
            
            cursor.execute("BEGIN TRANSACTION;")
            for food_id, embedding_data in zip(ids, response.data):
                vector_json = json.dumps(embedding_data.embedding)
                cursor.execute(
                    "UPDATE food_nutrition SET vector_embedding = %s WHERE fdc_id = %s;",
                    (vector_json, food_id)
                )
            conn.commit()
            print(f"  * Generated and saved embeddings for foods {i+1} to {i+len(batch)} of {total_foods}")
        except Exception as e:
            print(f"Error generating embeddings for batch starting at index {i}: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            # Stop execution on failure
            conn.close()
            return

    print("\nVector Embeddings Generation Completed Successfully!")
    conn.close()

if __name__ == "__main__":
    generate_embeddings()
