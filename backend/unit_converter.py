import json
import os
from typing import Optional, Tuple
from sqlmodel import Session, select

# ─── Load data files at module import time ─────────────────────────────────────
_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def _load(filename: str) -> dict:
    path = os.path.join(_DATA_DIR, filename)
    with open(path, "r") as f:
        return json.load(f)

FOOD_DENSITY: dict = _load("food_density.json")
WHOLE_OBJECT_WEIGHTS: dict = _load("whole_object_weights.json")

# ─── Universal unit constants ──────────────────────────────────────────────────
UNIVERSAL_UNITS = {
    "g": 1.0, "gram": 1.0, "grams": 1.0,
    "kg": 1000.0, "kilo": 1000.0, "kilogram": 1000.0,
    "oz": 28.35, "ounce": 28.35, "ounces": 28.35,
    "lb": 453.6, "pound": 453.6, "pounds": 453.6,
}

VOLUME_UNITS_ML = {
    "ml": 1.0, "milliliter": 1.0, "milliliters": 1.0,
    "l": 1000.0, "liter": 1000.0, "liters": 1000.0,
    "cup": 240.0, "cups": 240.0,
    "tbsp": 15.0, "tablespoon": 15.0, "tablespoons": 15.0,
    "tsp": 5.0, "teaspoon": 5.0, "teaspoons": 5.0,
}

# ─── State Resolver ────────────────────────────────────────────────────────────
def _resolve_cooking_state(food_name: str, explicit_state: str) -> str:
    if explicit_state in ("raw", "cooked"):
        return explicit_state
    name_lower = food_name.lower()
    if any(k in name_lower for k in ["rice", "chicken", "meat", "beef", "pork", "lamb", "fish", "salmon", "pasta", "noodle", "potato", "biryani", "curry", "dosa", "idli", "roti", "dal"]):
        return "cooked"
    if any(k in name_lower for k in ["flour", "oil", "sugar", "spice", "jaggery", "oat", "raw"]):
        return "raw"
    if any(k in name_lower for k in ["milk", "cheese", "butter", "bread", "yogurt", "curd"]):
        return "raw"
    return "unknown"

# ─── Density lookup ────────────────────────────────────────────────────────────
def _find_density(food_name: str) -> Optional[float]:
    """Best-effort density match by substring."""
    food_lower = food_name.lower()
    # Exact match first
    if food_lower in FOOD_DENSITY:
        return FOOD_DENSITY[food_lower]
    # Substring match
    for k, v in FOOD_DENSITY.items():
        if k in food_lower or food_lower in k:
            return v
    return None

# ─── Whole-object lookup ───────────────────────────────────────────────────────
def _find_whole_weight(unit: str) -> Optional[float]:
    unit_lower = unit.lower()
    if unit_lower in WHOLE_OBJECT_WEIGHTS:
        return WHOLE_OBJECT_WEIGHTS[unit_lower]
    for k, v in WHOLE_OBJECT_WEIGHTS.items():
        if k in unit_lower or unit_lower in k:
            return v
    return None

# ─── Main converter ───────────────────────────────────────────────────────────
def convert_to_grams(
    food_name: str,
    quantity: float,
    unit: str,
    state: str,
    db: Session
) -> Tuple[Optional[float], float, str]:
    """
    Returns (weight_g, converter_confidence, final_state)
    weight_g is None if conversion fails (trigger clarification).
    """
    final_state = _resolve_cooking_state(food_name, state)
    # Import here to avoid circular import
    from main import ReferenceServing

    unit_lower = unit.lower().strip()
    food_lower = food_name.lower().strip()

    # Layer 1: Explicit Weight (g, kg, oz, lb)
    if unit_lower in UNIVERSAL_UNITS:
        return (quantity * UNIVERSAL_UNITS[unit_lower], 1.0, final_state)

    # Layer 2: Volume × Density
    if unit_lower in VOLUME_UNITS_ML:
        volume_ml = quantity * VOLUME_UNITS_ML[unit_lower]
        density = _find_density(food_lower)
        if density is not None:
            return (volume_ml * density, 0.9, final_state)
        # Volume unit found but density unknown — still return volume as approximate (water density)
        if unit_lower in ("ml", "milliliter", "milliliters", "l", "liter", "liters"):
            return (volume_ml * 1.0, 0.85, final_state)  # water density fallback for liquids
        return (None, 0.0, final_state)  # volume unit with no density = clarification needed

    # Layer 3: ReferenceServing DB lookup (canonical serving sizes)
    priors = db.exec(
        select(ReferenceServing).where(ReferenceServing.unit == unit_lower)
    ).all()
    for p in priors:
        if p.food_name.lower() == food_lower:
            return (quantity * p.gram_weight, 1.0, final_state)
    for p in priors:
        if p.food_name.lower() in food_lower or food_lower in p.food_name.lower():
            return (quantity * p.gram_weight, 0.95, final_state)

    # Layer 4: Fractional Whole objects (pizza_whole, cake_whole, loaf, etc.)
    whole_weight = _find_whole_weight(unit_lower)
    if whole_weight is not None:
        return (quantity * whole_weight, 0.8, final_state)

    # Layer 5: Generic colloquial fallbacks (very low confidence)
    if unit_lower in ("piece", "slice"):
        if "bread" in food_lower: return (quantity * 30.0, 0.7, final_state)
        if "cheese" in food_lower: return (quantity * 20.0, 0.7, final_state)
        if "pizza" in food_lower: return (quantity * 112.0, 0.7, final_state)  # 1/8th of pizza
        if "cake" in food_lower: return (quantity * 125.0, 0.65, final_state)
        if "egg" in food_lower: return (quantity * 53.0, 0.8, final_state)
    if unit_lower == "handful":
        return (quantity * 30.0, 0.6, final_state)
    if unit_lower in ("bowl", "plate"):
        density = _find_density(food_lower)
        if density:
            return (quantity * 250.0 * density, 0.5, final_state)
        return (quantity * 200.0, 0.45, final_state)
    if unit_lower == "scoop":
        if any(k in food_lower for k in ["whey", "protein", "casein"]):
            return (quantity * 31.0, 0.75, final_state)
        return (quantity * 30.0, 0.5, final_state)
    if unit_lower == "glass":
        return (quantity * 240.0, 0.7, final_state)

    # Layer 6: Complete failure — requires clarification
    return (None, 0.0, final_state)
