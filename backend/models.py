from typing import List, Optional
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship

class MealBase(SQLModel):
    meal_type: str
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    logged_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )

class Meal(MealBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relationship to FoodItem
    items: List["FoodItem"] = Relationship(
        back_populates="meal",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

class FoodItemBase(SQLModel):
    name: str
    calories: float
    protein: float
    carbs: float
    fat: float

class FoodItem(FoodItemBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    meal_id: Optional[int] = Field(default=None, foreign_key="meal.id")
    
    # Relationship back to Meal
    meal: Optional[Meal] = Relationship(back_populates="items")
