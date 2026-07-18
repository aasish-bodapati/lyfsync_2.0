"""
models.py — All SQLModel database table definitions.
This is the single authority for the DB schema used by the application.
Production schema changes go through Supabase migrations; this file must stay in sync.
"""
from typing import Any
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Column
from pgvector.sqlalchemy import Vector


class FoodNutrition(SQLModel, table=True):
    """Reference table for atomic foods (USDA + curated). Per-100g values."""
    __tablename__ = "food_nutrition"  # type: ignore

    fdc_id: int | None = Field(default=None, primary_key=True)
    description: str
    calories: float
    protein: float
    carbs: float
    fat: float
    vector_embedding: Any = Field(default=None, sa_column=Column(Vector(1536)))
    source: str = Field(default="usda")


class Recipe(SQLModel, table=True):
    """Curated Indian recipe baselines. Macros are per typical_serving_grams."""
    __tablename__ = "recipes"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    name: str
    cuisine: str | None = None
    calories: float
    protein: float
    carbs: float
    fat: float
    typical_serving_grams: float
    vector_embedding: Any = Field(default=None, sa_column=Column(Vector(1536)))


class GeneratedRecipeCandidate(SQLModel, table=True):
    """LLM-generated recipe macros. status tracks the review lifecycle.
    lease_expires_at replaces the separate lock table for concurrency control."""
    __tablename__ = "generated_recipe_candidates"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    normalized_dish_name: str = Field(unique=True, index=True)
    ingredients_json: str
    calories: float
    protein: float
    carbs: float
    fat: float
    typical_serving_grams: float
    model_version: str
    status: str = Field(default="pending")  # pending, approved, rejected
    lease_expires_at: str | None = None      # ISO string; non-null means generation is in-flight
    created_at: str


class RecipeGenerationLog(SQLModel, table=True):
    """Append-only audit log for every generation attempt (success or failure)."""
    __tablename__ = "recipe_generation_logs"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    normalized_dish_name: str = Field(index=True)
    status: str                  # "success" or "failed"
    error_message: str | None = None
    created_at: str


class MealTable(SQLModel, table=True):
    """A persisted meal log entry."""
    __tablename__ = "meals"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    raw_text: str
    meal_type: str
    calories: float
    protein: float
    carbs: float
    fat: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MealItemTable(SQLModel, table=True):
    """A single resolved food item within a MealTable."""
    __tablename__ = "meal_items"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    meal_id: int = Field(foreign_key="meals.id")
    name: str
    weight_grams: float
    calories: float
    protein: float
    carbs: float
    fat: float
    source: str
    confidence: float | None = None
    quantity: float | None = None
    unit: str | None = None
    raw_or_cooked: str | None = None
    assumption_made: str | None = None
    ambiguity_reason: str | None = None
    needs_clarification: bool = False
