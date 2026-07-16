import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from sqlmodel import Session, select, SQLModel, Field
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
    Computes query embedding, compares it to all foods in the DB, 
    and returns the best match if its similarity score exceeds the threshold.
    """
    try:
        query_vector = get_embedding(query)
    except Exception as e:
        print(f"Error generating query embedding: {e}")
        return None

    # Fetch all foods with their embeddings
    result = db.exec(select(FoodNutrition)).all()

    best_match = None
    best_score = -1.0

    for food in result:
        fdc_id = food.fdc_id
        description = food.description
        calories = food.calories
        protein = food.protein
        carbs = food.carbs
        fat = food.fat
        vector_embedding_json = food.vector_embedding
        
        if not vector_embedding_json:
            continue
            
        try:
            food_vector = json.loads(vector_embedding_json)
        except Exception:
            continue  # Skip corrupt records
            
        score = cosine_similarity(query_vector, food_vector)
        
        if score > best_score:
            best_score = score
            best_match = {
                "fdc_id": fdc_id,
                "description": description,
                "calories": calories,
                "protein": protein,
                "carbs": carbs,
                "fat": fat,
                "similarity_score": score
            }

    if best_match and best_score >= threshold:
        print(f"FOUND LOCAL MATCH: '{best_match['description']}' with score {best_score:.4f}")
        return best_match

    print(f"NO LOCAL MATCH ABOVE THRESHOLD. Best score was: {best_score:.4f}")
    return None
