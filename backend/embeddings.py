import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from sqlmodel import Session, select, SQLModel, Field, text
from dotenv import load_dotenv

# Ensure environment variables are loaded
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class FoodNutrition(SQLModel, table=True):
    __tablename__ = "food_nutrition"  # type: ignore
    fdc_id: int | None = Field(default=None, primary_key=True)
    description: str
    calories: float
    protein: float
    carbs: float
    fat: float
    vector_embedding: str | None = Field(default=None)


def get_embedding(text_to_embed: str) -> List[float]:
    """Generates a 1536-dimensional vector embedding using text-embedding-3-small."""
    response = client.embeddings.create(
        input=[text_to_embed],
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculates the cosine similarity score between two 1536-dimensional vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(v1, v2))
    mag1 = sum(a * a for a in v1) ** 0.5
    mag2 = sum(b * b for b in v2) ** 0.5
    
    if not mag1 or not mag2:
        return 0.0
        
    return dot_product / (mag1 * mag2)

def find_closest_food(query: str, db: Session, threshold: float = 0.80) -> Optional[Dict[str, Any]]:
    """
    Computes query embedding, compares it to all foods in the DB natively using sqlite-vec,
    and returns the best match if its similarity score exceeds the threshold.
    """
    try:
        query_vector = get_embedding(query)
    except Exception as e:
        print(f"Error generating query embedding: {e}")
        return None

    # Load sqlite-vec extension on demand
    import sqlite_vec
    raw_conn = db.connection().connection.dbapi_connection
    try:
        raw_conn.execute("SELECT vec_version()")
    except Exception:
        raw_conn.enable_load_extension(True)
        sqlite_vec.load(raw_conn)
        raw_conn.enable_load_extension(False)

    # Convert query vector to JSON string for sqlite-vec
    import json
    query_vector_json = json.dumps(query_vector)

    # Cosine distance = 1.0 - Cosine similarity
    # We want similarity >= threshold, which translates to distance <= 1.0 - threshold
    max_distance = 1.0 - threshold

    result = db.execute(
        text(
            "SELECT fdc_id, description, calories, protein, carbs, fat, "
            "vec_distance_cosine(vector_embedding, :query_vec) as distance "
            "FROM food_nutrition "
            "WHERE vector_embedding IS NOT NULL "
            "AND vec_distance_cosine(vector_embedding, :query_vec) <= :max_dist "
            "ORDER BY distance "
            "LIMIT 1"
        ),
        {"query_vec": query_vector_json, "max_dist": max_distance}
    ).fetchone()

    if result:
        fdc_id, description, calories, protein, carbs, fat, distance = result
        similarity_score = 1.0 - distance
        print(f"FOUND LOCAL MATCH: '{description}' with score {similarity_score:.4f}")
        return {
            "fdc_id": fdc_id,
            "description": description,
            "calories": calories,
            "protein": protein,
            "carbs": carbs,
            "fat": fat,
            "similarity_score": similarity_score
        }

    print(f"NO LOCAL MATCH ABOVE THRESHOLD.")
    return None
