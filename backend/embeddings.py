from typing import List, Dict, Any, Optional
from openai import OpenAI
from sqlmodel import Session, select, SQLModel, Field, Column
from pgvector.sqlalchemy import Vector
import re

class FoodNutrition(SQLModel, table=True):
    __tablename__ = "food_nutrition"  # type: ignore
    fdc_id: int | None = Field(default=None, primary_key=True)
    description: str
    calories: float
    protein: float
    carbs: float
    fat: float
    vector_embedding: Any = Field(default=None, sa_column=Column(Vector(1536)))
    source: str = Field(default="usda")

def get_embedding(text_to_embed: str, client: OpenAI) -> List[float]:
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

def normalize_food_name(query: str) -> str:
    """Normalizes the query using a dictionary of common Indian food aliases."""
    ALIASES = {
        "curd": "yogurt",
        "roti": "chapati",
        "kadhai": "wok",
        "paneer": "cheese",
        "dal": "lentils",
        "chana": "chickpeas",
        "rajma": "kidney beans"
    }
    
    query_lower = query.lower().strip()
    for alias, replacement in ALIASES.items():
        query_lower = re.sub(rf'\b{alias}\b', replacement, query_lower)
        
    return query_lower

def find_closest_food(query: str, db: Session, client: OpenAI, threshold: float = 0.60) -> Optional[Dict[str, Any]]:
    """
    Computes query embedding, compares it to all foods in the DB natively using pgvector,
    and returns the best match if its similarity score exceeds the threshold.
    """
    query_normalized = normalize_food_name(query)
    
    try:
        query_vector = get_embedding(query_normalized, client)
    except Exception as e:
        print(f"Error generating query embedding: {e}")
        return None

    results = db.execute(
        select(FoodNutrition)
        .where(FoodNutrition.vector_embedding.is_not(None))
        .order_by(FoodNutrition.vector_embedding.cosine_distance(query_vector))
        .limit(3)
    ).scalars().all()
    
    if not results:
        return None
        
    result = results[0]

    if result and result.vector_embedding is not None:
        similarity_score = cosine_similarity(query_vector, result.vector_embedding)
        
        if similarity_score >= threshold:
            print(f"FOUND MATCH: '{result.description}' with score {similarity_score:.4f}")
            return {
                "fdc_id": result.fdc_id,
                "description": result.description,
                "calories": result.calories,
                "protein": result.protein,
                "carbs": result.carbs,
                "fat": result.fat,
                "similarity_score": similarity_score
            }

    print(f"NO MATCH ABOVE THRESHOLD.")
    return None
