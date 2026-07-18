"""
nutrition_service.py — Core nutrition resolution logic.

Responsibilities:
  - LLM extraction (extract_meal_structure)
  - Weight estimation from units (item-specific conversions + global priors)
  - Food/recipe resolution and fallback orchestration (resolve_nutrition)
  - DB persistence (persist_meal)

Configuration (thresholds, unit maps) lives in:
  - backend/data/conversions.json
  - backend/data/aliases.json  (consumed by embeddings.py)
"""
import json
import logging
import os
from typing import List, Tuple
from openai import OpenAI
from sqlmodel import Session

import openai
from fastapi import HTTPException

from prompts import SYSTEM_PROMPT
from embeddings import find_closest_food, find_closest_recipe
from fallback import generate_recipe_fallback
from schemas import ExtractionItem, ParsedMeal, MealItem
from models import MealTable, MealItemTable

logger = logging.getLogger(__name__)

# ── Retrieval thresholds (one named place) ─────────────────────────────────────
FOOD_SIMILARITY_THRESHOLD = 0.70
RECIPE_SIMILARITY_THRESHOLD = 0.70
HIGH_CONFIDENCE_THRESHOLD = 0.80

# ── Unit maps ──────────────────────────────────────────────────────────────────
EXPLICIT_MASS_UNITS = {"g", "gram", "grams"}
VOLUME_UNITS = {"ml", "milliliter", "milliliters"}

_BASE = os.path.dirname(__file__)

with open(os.path.join(_BASE, "config", "conversions.json")) as _f:
    ITEM_SPECIFIC_CONVERSIONS: dict = json.load(_f)

PORTION_PRIORS = {
    "tbsp": 15.0,
    "tablespoon": 15.0,
    "tsp": 5.0,
    "teaspoon": 5.0,
    "handful": 30.0,
    "grams": 1.0,
    "gram": 1.0,
    "g": 1.0,
    "ml": 1.0,
    "milliliter": 1.0,
}

# ── Mixed-dish detection ───────────────────────────────────────────────────────
ATOMIC_FOOD_NAMES = {
    "beef", "chicken", "chicken breast", "chicken thigh", "egg", "egg white",
    "fish", "meat", "paneer", "pork", "rice", "tofu",
}
ATOMIC_PREPARATION_PREFIXES = {"baked", "boiled", "cooked", "grilled", "roasted", "steamed"}


def looks_like_mixed_dish(item_name: str, raw_or_cooked: str) -> bool:
    """True when a cooked item should only be resolved against recipe baselines."""
    if raw_or_cooked.lower() != "cooked":
        return False
    norm = " ".join(item_name.lower().split())
    if norm.endswith("s"):
        norm = norm[:-1]
    if norm in ATOMIC_FOOD_NAMES:
        return False
    parts = norm.split(maxsplit=1)
    if len(parts) == 2 and parts[0] in ATOMIC_PREPARATION_PREFIXES:
        return parts[1] not in ATOMIC_FOOD_NAMES
    return True


def _estimate_weight(item: ExtractionItem) -> Tuple[float, str | None]:
    """
    Returns (weight_grams, assumption_string) using a three-tier priority:
      1. Explicit mass/volume units
      2. Item-specific conversions loaded from data/conversions.json
      3. Global tablespoon/teaspoon priors; otherwise fall through to LLM estimate
    """
    unit = item.unit.lower()
    name = item.name.lower()
    assumption = item.assumption_made

    if unit in EXPLICIT_MASS_UNITS:
        return item.quantity, assumption or "Explicit weight provided"

    if unit in VOLUME_UNITS:
        return item.quantity, assumption or "Assumed 1 ml equals 1 g"

    for key, conversions in ITEM_SPECIFIC_CONVERSIONS.items():
        if key in name and unit in conversions:
            return (
                item.quantity * conversions[unit],
                assumption or f"Used item-specific prior for {key} ({unit})",
            )

    if unit in PORTION_PRIORS:
        return (
            item.quantity * PORTION_PRIORS[unit],
            assumption or f"Used deterministic prior for {item.unit}",
        )

    return item.estimated_weight_grams, assumption


# ── LLM extraction ─────────────────────────────────────────────────────────────

def extract_meal_structure(text: str, client: OpenAI) -> ParsedMeal:
    """Sends user text to OpenAI and returns a structured ParsedMeal."""
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        response_format=ParsedMeal,
        temperature=0.0,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise ValueError("Failed to extract structure from text.")
    return parsed


def safe_parse_text(text: str, client: OpenAI) -> ParsedMeal:
    try:
        return extract_meal_structure(text, client)
    except openai.APIError as e:
        logger.error(f"OpenAI API Error: {e}")
        raise HTTPException(status_code=502, detail="AI service unavailable")
    except ValueError as e:
        logger.error(f"Parsing Error: {e}")
        raise HTTPException(status_code=400, detail="Failed to parse meal description")


# ── Nutrition resolution ───────────────────────────────────────────────────────

def resolve_nutrition(
    parsed_meal: ParsedMeal,
    db: Session,
    client: OpenAI,
    persist: bool = True,
) -> Tuple[float, float, float, float, List[MealItem]]:
    """
    Resolves each extracted item to DB macros.
    Resolution order per item:
      1. Recipe DB   (for cooked mixed dishes)
      2. LLM fallback recipe generation (if recipe DB misses)
      3. Food DB     (for atomic/prepared single ingredients)
    """
    total_cal = total_prot = total_carb = total_fat = 0.0
    resolved_items: List[MealItem] = []

    for item in parsed_meal.items:
        actual_weight, assumption = _estimate_weight(item)

        match = None
        match_type = None
        scale = 1.0

        if looks_like_mixed_dish(item.name, item.raw_or_cooked):
            recipe_match = find_closest_recipe(item.name, db, client, threshold=RECIPE_SIMILARITY_THRESHOLD)
            if recipe_match:
                match = recipe_match
                match_type = "recipe"
                scale = actual_weight / match["typical_serving_grams"]
            else:
                generated = generate_recipe_fallback(item.name, db, client, persist=persist)
                if generated and generated.get("status") == "success":
                    match = generated
                    match_type = "generated_recipe"
                    scale = actual_weight / generated["typical_serving_grams"]
                    item.needs_clarification = True
                    note = "Provisional recipe generated."
                    item.ambiguity_reason = (
                        f"{item.ambiguity_reason} | {note}" if item.ambiguity_reason else note
                    )
                    assumption = f"{assumption} | Generated recipe" if assumption else "Generated recipe"
                else:
                    unresolved = (
                        generated.get("unresolved_ingredients", []) if generated else ["Fallback unavailable"]
                    )
                    note = f"Recipe generation failed. Unresolved ingredients: {', '.join(unresolved)}"
                    item.ambiguity_reason = (
                        f"{item.ambiguity_reason} | {note}" if item.ambiguity_reason else note
                    )
                    item.needs_clarification = True
        else:
            food_match = find_closest_food(item.name, db, client, threshold=FOOD_SIMILARITY_THRESHOLD)
            if food_match:
                match = food_match
                match_type = "food"
                scale = actual_weight / 100.0

        if match:
            item_cal = match["calories"] * scale
            item_prot = match["protein"] * scale
            item_carb = match["carbs"] * scale
            item_fat = match["fat"] * scale
            confidence = match.get("similarity_score")

            if match_type == "generated_recipe":
                source = "generated_recipe"
            else:
                band = "high" if (confidence or 0) >= HIGH_CONFIDENCE_THRESHOLD else "low"
                source = f"{match_type}_match_{band}"
        else:
            item_cal = item_prot = item_carb = item_fat = 0.0
            confidence = None
            source = "unresolved"
            item.needs_clarification = True

        total_cal += item_cal
        total_prot += item_prot
        total_carb += item_carb
        total_fat += item_fat

        resolved_items.append(
            MealItem(
                name=item.name,
                weight_grams=actual_weight,
                calories=round(item_cal, 2),
                protein=round(item_prot, 2),
                carbs=round(item_carb, 2),
                fat=round(item_fat, 2),
                source=source,
                confidence=confidence,
                quantity=item.quantity,
                unit=item.unit,
                raw_or_cooked=item.raw_or_cooked,
                assumption_made=assumption,
                ambiguity_reason=item.ambiguity_reason,
                needs_clarification=item.needs_clarification,
            )
        )

    return total_cal, total_prot, total_carb, total_fat, resolved_items


def persist_meal(
    db: Session,
    text: str,
    meal_type: str,
    totals: Tuple[float, float, float, float],
    items: List[MealItem],
) -> MealTable:
    """Saves a resolved meal and all its items in a single transaction."""
    db_meal = MealTable(
        raw_text=text,
        meal_type=meal_type,
        calories=round(totals[0], 2),
        protein=round(totals[1], 2),
        carbs=round(totals[2], 2),
        fat=round(totals[3], 2),
    )
    try:
        db.add(db_meal)
        db.flush()

        for item in items:
            db.add(
                MealItemTable(
                    meal_id=db_meal.id,
                    name=item.name,
                    weight_grams=item.weight_grams,
                    calories=item.calories,
                    protein=item.protein,
                    carbs=item.carbs,
                    fat=item.fat,
                    source=item.source,
                    confidence=item.confidence,
                    quantity=item.quantity,
                    unit=item.unit,
                    raw_or_cooked=item.raw_or_cooked,
                    assumption_made=item.assumption_made,
                    ambiguity_reason=item.ambiguity_reason,
                    needs_clarification=item.needs_clarification,
                )
            )

        db.commit()
        db.refresh(db_meal)
    except Exception as e:
        db.rollback()
        logger.error(f"Database Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save meal")

    return db_meal
