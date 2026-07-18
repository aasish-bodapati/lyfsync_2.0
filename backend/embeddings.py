"""
embeddings.py — Vector search utilities.

Responsibilities:
  - Generating embeddings (single + batch)
  - Normalizing food/recipe names (aliases loaded from data/aliases.json)
  - Cosine similarity + reranked top-k search for FoodNutrition and Recipe

DB models are in models.py. Configuration thresholds are in nutrition_service.py.
"""
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from openai import OpenAI
from sqlmodel import Session, select

from models import FoodNutrition, Recipe

logger = logging.getLogger(__name__)

_BASE = os.path.dirname(__file__)
with open(os.path.join(_BASE, "config", "aliases.json")) as _f:
    _ALIASES: dict = json.load(_f)


# ── Embedding helpers ──────────────────────────────────────────────────────────

def get_embedding(text: str, client: OpenAI) -> List[float]:
    """Single embedding call."""
    response = client.embeddings.create(
        input=[text], model="text-embedding-3-small"
    )
    return response.data[0].embedding


def get_embeddings_batch(texts: List[str], client: OpenAI) -> List[List[float]]:
    """Batch embedding call; returns results in input order."""
    if not texts:
        return []
    response = client.embeddings.create(input=texts, model="text-embedding-3-small")
    return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]


# ── Name normalisation ─────────────────────────────────────────────────────────

def normalize_food_name(query: str) -> str:
    """Applies alias substitutions to improve USDA retrieval precision."""
    q = query.lower().strip()
    for alias, replacement in _ALIASES.items():
        q = re.sub(rf"\b{alias}\b", replacement, q)
    return q


def normalize_recipe_name(query: str) -> str:
    """Normalises spacing; preserves Indian dish names (no alias substitution)."""
    return " ".join(query.lower().split())


# ── Cosine similarity ──────────────────────────────────────────────────────────

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    mag1 = sum(a * a for a in v1) ** 0.5
    mag2 = sum(b * b for b in v2) ** 0.5
    return dot / (mag1 * mag2) if mag1 and mag2 else 0.0


# ── Search ─────────────────────────────────────────────────────────────────────

def _rerank(query_norm: str, name: str, base_score: float) -> float:
    """Applies substring bonus to the cosine score."""
    if query_norm == name.lower():
        return base_score + 0.20
    if query_norm in name.lower():
        return base_score + 0.10
    return base_score


def find_closest_food_with_vector(
    query: str,
    query_vector: List[float],
    db: Session,
    threshold: float = 0.65,
) -> Optional[Dict[str, Any]]:
    """Core food search given a pre-computed vector."""
    query_norm = normalize_food_name(query)
    rows = db.execute(
        select(FoodNutrition)
        .where(FoodNutrition.vector_embedding.is_not(None))
        .order_by(FoodNutrition.vector_embedding.cosine_distance(query_vector))
        .limit(5)
    ).scalars().all()

    best, best_score = None, -1.0
    for row in rows:
        if row.vector_embedding is None:
            continue
        score = _rerank(query_norm, row.description, cosine_similarity(query_vector, row.vector_embedding))
        if score > best_score:
            best_score, best = score, row

    if best and best_score >= threshold:
        logger.info(f"FOUND MATCH: '{best.description}' with reranked score {best_score:.4f}")
        return {
            "fdc_id": best.fdc_id,
            "description": best.description,
            "calories": best.calories,
            "protein": best.protein,
            "carbs": best.carbs,
            "fat": best.fat,
            "similarity_score": best_score,
        }

    logger.info(f"NO MATCH ABOVE THRESHOLD {threshold}. Best was {best_score:.4f}")
    return None


def find_closest_food(
    query: str,
    db: Session,
    client: OpenAI,
    threshold: float = 0.70,
) -> Optional[Dict[str, Any]]:
    query_norm = normalize_food_name(query)
    try:
        vec = get_embedding(query_norm, client)
    except Exception as e:
        logger.error(f"Embedding error for food '{query}': {e}")
        return None
    return find_closest_food_with_vector(query_norm, vec, db, threshold)


def find_closest_recipe(
    query: str,
    db: Session,
    client: OpenAI,
    threshold: float = 0.70,
) -> Optional[Dict[str, Any]]:
    query_norm = normalize_recipe_name(query)
    try:
        vec = get_embedding(query_norm, client)
    except Exception as e:
        logger.error(f"Embedding error for recipe '{query}': {e}")
        return None

    rows = db.execute(
        select(Recipe)
        .where(Recipe.vector_embedding.is_not(None))
        .order_by(Recipe.vector_embedding.cosine_distance(vec))
        .limit(5)
    ).scalars().all()

    best, best_score = None, -1.0
    for row in rows:
        if row.vector_embedding is None:
            continue
        score = _rerank(query_norm, row.name, cosine_similarity(vec, row.vector_embedding))
        if score > best_score:
            best_score, best = score, row

    if best and best_score >= threshold:
        logger.info(f"FOUND RECIPE MATCH: '{best.name}' with reranked score {best_score:.4f}")
        return {
            "id": best.id,
            "name": best.name,
            "calories": best.calories,
            "protein": best.protein,
            "carbs": best.carbs,
            "fat": best.fat,
            "typical_serving_grams": best.typical_serving_grams,
            "similarity_score": best_score,
        }

    logger.info(f"NO RECIPE MATCH ABOVE THRESHOLD {threshold}. Best was {best_score:.4f}")
    return None
