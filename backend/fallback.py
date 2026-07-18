"""
fallback.py — LLM-based generated-recipe fallback.

Invoked when a cooked mixed dish has no match in the curated Recipe table.
Concurrency is controlled via lease_expires_at on GeneratedRecipeCandidate
(replaces the removed RecipeGenerationLock table).
"""
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import openai
from openai import OpenAI
from pydantic import BaseModel
from sqlmodel import Session, select

from embeddings import (
    normalize_recipe_name,
    normalize_food_name,
    find_closest_food_with_vector,
    get_embeddings_batch,
)
from models import GeneratedRecipeCandidate, RecipeGenerationLog
from prompts import RECIPE_GENERATION_PROMPT

logger = logging.getLogger(__name__)

MAX_RECIPE_GENERATIONS_PER_DAY = 20
FAILURE_CACHE_MINUTES = 60
LEASE_DURATION_MINUTES = 5


class GeneratedIngredient(BaseModel):
    name: str
    weight_grams: float


class GeneratedRecipeStructure(BaseModel):
    dish_name: str
    typical_serving_grams: float
    ingredients: List[GeneratedIngredient]
    assumptions: str | None = None


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def generate_recipe_fallback(
    dish_name: str,
    db: Session,
    client: OpenAI,
    persist: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Attempts to generate a structured recipe for an unknown dish.
    Returns {"status": "success", ...macros...} or {"status": "failed", ...}.
    """
    normalized = normalize_recipe_name(dish_name)
    now = _now_utc()
    now_iso = now.isoformat()
    today_prefix = now.strftime("%Y-%m-%d")

    # 1. Success cache
    existing = db.execute(
        select(GeneratedRecipeCandidate)
        .where(GeneratedRecipeCandidate.normalized_dish_name == normalized)
    ).scalar_one_or_none()

    if existing:
        # Concurrency guard: if an in-flight lease is active, block the caller
        if existing.lease_expires_at:
            lease_exp = datetime.fromisoformat(existing.lease_expires_at)
            if now < lease_exp:
                logger.warning(f"CONCURRENT REQUEST BLOCKED: {normalized}")
                return {"status": "failed", "unresolved_ingredients": ["Concurrent generation in progress"]}

        # Success cache: completed candidate
        if existing.status in ("pending", "approved") and existing.calories > 0:
            logger.info(f"CACHE HIT: Found existing generated recipe for {normalized}")
            return {
                "status": "success",
                "calories": existing.calories,
                "protein": existing.protein,
                "carbs": existing.carbs,
                "fat": existing.fat,
                "typical_serving_grams": existing.typical_serving_grams,
                "ingredients_json": existing.ingredients_json,
            }

    # 2. Failure cache
    recent_failure = db.execute(
        select(RecipeGenerationLog)
        .where(
            RecipeGenerationLog.normalized_dish_name == normalized,
            RecipeGenerationLog.status == "failed",
        )
        .order_by(RecipeGenerationLog.id.desc())  # type: ignore
    ).scalars().first()

    if recent_failure:
        failure_dt = datetime.fromisoformat(recent_failure.created_at)
        if (now - failure_dt) < timedelta(minutes=FAILURE_CACHE_MINUTES):
            logger.info(f"CACHE HIT: Recent failure for {normalized}. Skipping.")
            return {"status": "failed", "unresolved_ingredients": [recent_failure.error_message]}

    if persist:
        # 3. Global daily cap
        today_runs = db.execute(
            select(RecipeGenerationLog)
            .where(RecipeGenerationLog.created_at.startswith(today_prefix))
        ).scalars().all()
        if len(today_runs) >= MAX_RECIPE_GENERATIONS_PER_DAY:
            logger.warning(f"GLOBAL CAP REACHED: Skipping {normalized}")
            return {"status": "failed", "unresolved_ingredients": ["Global daily generation cap reached"]}

        # Acquire lease atomically
        from sqlalchemy import update
        from sqlalchemy.exc import IntegrityError, OperationalError
        
        lease_exp_iso = (now + timedelta(minutes=LEASE_DURATION_MINUTES)).isoformat()
        
        # 1. Try to acquire lease on an existing row
        stmt = (
            update(GeneratedRecipeCandidate)
            .where(GeneratedRecipeCandidate.normalized_dish_name == normalized)
            .where(
                (GeneratedRecipeCandidate.lease_expires_at.is_(None)) | 
                (GeneratedRecipeCandidate.lease_expires_at < now_iso)
            )
            .values(lease_expires_at=lease_exp_iso)
        )
        try:
            result = db.execute(stmt)
            rowcount = result.rowcount
        except OperationalError:
            # SQLite specific: database is locked during concurrent writes
            db.rollback()
            logger.warning(f"CONCURRENT REQUEST BLOCKED: {normalized}")
            return {"status": "failed", "unresolved_ingredients": ["Concurrent generation in progress"]}
        
        if rowcount == 0:
            # 2. If no rows updated, it either doesn't exist or is currently locked by someone else
            try:
                placeholder = GeneratedRecipeCandidate(
                    normalized_dish_name=normalized,
                    ingredients_json="",
                    calories=0, protein=0, carbs=0, fat=0,
                    typical_serving_grams=0,
                    model_version="pending",
                    status="pending",
                    lease_expires_at=lease_exp_iso,
                    created_at=now_iso,
                )
                db.add(placeholder)
                db.commit()
            except (IntegrityError, OperationalError):
                db.rollback()
                logger.warning(f"CONCURRENT REQUEST BLOCKED: {normalized}")
                return {"status": "failed", "unresolved_ingredients": ["Concurrent generation in progress"]}
        else:
            db.commit()

    try:
        # 5. Generate
        logger.info(f"GENERATING RECIPE: {normalized}")
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": RECIPE_GENERATION_PROMPT},
                {"role": "user", "content": f"Extract the standard recipe ingredients for 1 serving of: {normalized}"},
            ],
            response_format=GeneratedRecipeStructure,
            temperature=0.0,
        )
        parsed = completion.choices[0].message.parsed
        if not parsed:
            raise ValueError("Parsed recipe structure was None.")

        if not (1 <= len(parsed.ingredients) <= 20):
            raise ValueError(f"Invalid ingredient count: {len(parsed.ingredients)}")
        if not (0 < parsed.typical_serving_grams < 2000):
            raise ValueError(f"Invalid serving weight: {parsed.typical_serving_grams}g")
        for ing in parsed.ingredients:
            if not (0 < ing.weight_grams < 2000):
                raise ValueError(f"Invalid ingredient weight for {ing.name}: {ing.weight_grams}g")

        # 6. Resolve macros (batched)
        norm_names = [normalize_food_name(ing.name) for ing in parsed.ingredients]
        vectors = get_embeddings_batch(norm_names, client)

        total_cal = total_pro = total_carb = total_fat = 0.0
        unresolved: List[str] = []

        for ing, norm, vec in zip(parsed.ingredients, norm_names, vectors):
            match = find_closest_food_with_vector(norm, vec, db, threshold=0.70)
            if match:
                scale = ing.weight_grams / 100.0
                total_cal += match["calories"] * scale
                total_pro += match["protein"] * scale
                total_carb += match["carbs"] * scale
                total_fat += match["fat"] * scale
            else:
                unresolved.append(ing.name)

        if unresolved:
            raise ValueError(f"Unresolved ingredients: {', '.join(unresolved)}")

        # 7. Persist
        if persist:
            candidate = db.execute(
                select(GeneratedRecipeCandidate)
                .where(GeneratedRecipeCandidate.normalized_dish_name == normalized)
            ).scalar_one_or_none()

            if candidate:
                candidate.ingredients_json = parsed.model_dump_json()
                candidate.calories = total_cal
                candidate.protein = total_pro
                candidate.carbs = total_carb
                candidate.fat = total_fat
                candidate.typical_serving_grams = parsed.typical_serving_grams
                candidate.model_version = "gpt-4o-mini"
                candidate.status = "pending"
                candidate.lease_expires_at = None
            else:
                candidate = GeneratedRecipeCandidate(
                    normalized_dish_name=normalized,
                    ingredients_json=parsed.model_dump_json(),
                    calories=total_cal, protein=total_pro, carbs=total_carb, fat=total_fat,
                    typical_serving_grams=parsed.typical_serving_grams,
                    model_version="gpt-4o-mini",
                    status="pending",
                    lease_expires_at=None,
                    created_at=now_iso,
                )
            db.add(candidate)
            db.add(RecipeGenerationLog(
                normalized_dish_name=normalized,
                status="success",
                created_at=now_iso,
            ))
            db.commit()

        logger.info(f"SUCCESS: Generated {normalized} with {total_cal:.1f} kcal")
        return {
            "status": "success",
            "calories": total_cal,
            "protein": total_pro,
            "carbs": total_carb,
            "fat": total_fat,
            "typical_serving_grams": parsed.typical_serving_grams,
            "ingredients_json": parsed.model_dump_json(),
            "unresolved_ingredients": [],
        }

    except Exception as e:
        logger.error(f"Failed to generate recipe for {normalized}: {e}")
        if persist:
            # Release lease
            stale = db.execute(
                select(GeneratedRecipeCandidate)
                .where(GeneratedRecipeCandidate.normalized_dish_name == normalized)
            ).scalar_one_or_none()
            if stale and stale.calories == 0:
                db.delete(stale)
            db.add(RecipeGenerationLog(
                normalized_dish_name=normalized,
                status="failed",
                error_message=str(e),
                created_at=now_iso,
            ))
            db.commit()

        unresolved_list = [str(e)]
        if "Unresolved ingredients:" in str(e):
            unresolved_list = [i.strip() for i in str(e).split("Unresolved ingredients: ")[1].split(",")]
        return {"status": "failed", "unresolved_ingredients": unresolved_list}
