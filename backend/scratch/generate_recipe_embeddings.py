import os
import json
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")

def generate_recipe_embeddings():
    print(f"Connecting to database: {DATABASE_URL}")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, description, ingredients
        FROM recipes 
        WHERE vector_embedding IS NULL
    """)
    recipes = cursor.fetchall()
    
    total_recipes = len(recipes)
    if total_recipes == 0:
        print("All recipes already have vector embeddings.")
        conn.close()
        return

    print(f"Found {total_recipes} recipes needing vector embeddings.")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("CRITICAL ERROR: 'OPENAI_API_KEY' is not set in your .env file.")
        conn.close()
        return
        
    client = OpenAI(api_key=api_key)

    batch_size = 100
    print("Generating embeddings via OpenAI...")
    
    for i in range(0, total_recipes, batch_size):
        batch = recipes[i:i+batch_size]
        # Create a rich text representation for the embedding
        descriptions = [f"{row[1]} - {row[2]}. Ingredients: {row[3]}" for row in batch]
        ids = [row[0] for row in batch]
        
        try:
            response = client.embeddings.create(
                input=descriptions,
                model="text-embedding-3-small"
            )
            
            cursor.execute("BEGIN TRANSACTION;")
            for recipe_id, embedding_data in zip(ids, response.data):
                vector_json = json.dumps(embedding_data.embedding)
                cursor.execute(
                    "UPDATE recipes SET vector_embedding = %s WHERE id = %s;",
                    (vector_json, recipe_id)
                )
            conn.commit()
            print(f"  * Generated and saved embeddings for recipes {i+1} to {i+len(batch)} of {total_recipes}")
        except Exception as e:
            print(f"Error generating embeddings for batch starting at index {i}: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            conn.close()
            return

    print("\nVector Embeddings Generation Completed Successfully!")
    conn.close()

if __name__ == "__main__":
    generate_recipe_embeddings()
