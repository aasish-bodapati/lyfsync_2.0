"""
schemas.py — Pydantic models for API I/O and LLM structured output.
Nothing here touches the database; nothing in models.py references these.
"""
from typing import List
from pydantic import BaseModel


class UserInput(BaseModel):
    """API request body: raw natural-language meal description."""
    text: str


class ExtractionItem(BaseModel):
    """One food item as extracted by the LLM from user text."""
    name: str
    quantity: float
    unit: str
    estimated_weight_grams: float
    raw_or_cooked: str
    assumption_made: str | None = None
    ambiguity_reason: str | None = None
    needs_clarification: bool = False


class ParsedMeal(BaseModel):
    """Full structured LLM extraction result."""
    meal_type: str
    items: List[ExtractionItem]


class MealItem(BaseModel):
    """A resolved food item returned to the API caller."""
    name: str
    weight_grams: float
    calories: float
    protein: float
    carbs: float
    fat: float
    source: str | None = None
    confidence: float | None = None
    quantity: float | None = None
    unit: str | None = None
    raw_or_cooked: str | None = None
    assumption_made: str | None = None
    ambiguity_reason: str | None = None
    needs_clarification: bool = False


class Meal(BaseModel):
    """Full meal response returned by /api/v1/meals/parse."""
    meal_type: str
    items: List[MealItem]
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
