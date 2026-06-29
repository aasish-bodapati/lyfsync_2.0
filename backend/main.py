import os
import json
from typing import List
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session
from dotenv import load_dotenv
from openai import OpenAI

from database import create_db_and_tables, get_session
from models import Meal, FoodItem

# Load environment variables
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(title="LyfSync Nutrition Tracking API", version="1.0.0", lifespan=lifespan)



# --- Pydantic Schemas ---
class FoodResponse(BaseModel):
    name: str
    calories: float
    protein: float
    carbs: float
    fat: float

class MealResponse(BaseModel):
    meal_type: str
    items: List[FoodResponse]
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float

class UserInput(BaseModel):
    text: str





# --- Client Initializations ---
llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# --- AI Parsing Services ---
def parse_with_openai(request: UserInput) -> MealResponse:
    try:
        completion = llm_client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise nutrition and macronutrient estimation assistant. "
                        "Analyze the user's input, extract all individual food items, estimate their macros "
                        "(calories in kcal, protein, carbs, and fat in grams), categorize the meal "
                        "(breakfast, lunch, dinner, or snack), and compute the total sum of all items."
                    )
                },
                {"role": "user", "content": request.text}
            ],
            response_format=MealResponse,
        )
        parsed = completion.choices[0].message.parsed
        if parsed:
            return parsed
        raise ValueError("Failed to parse response structure from OpenAI.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI parsing failed: {str(e)}")


# --- Endpoints ---
@app.post("/api/v1/meals/parse", response_model=MealResponse)
def parse_meal(request: UserInput, session: Session = Depends(get_session)):
    """
    Parses natural language meal logs, persists them to the DB, and returns the breakdown.
    """
    parsed_meal = parse_with_openai(request)
    
    # Create DB models
    db_items = [
        FoodItem(
            name=item.name,
            calories=item.calories,
            protein=item.protein,
            carbs=item.carbs,
            fat=item.fat
        )
        for item in parsed_meal.items
    ]
    
    db_meal = Meal(
        meal_type=parsed_meal.meal_type,
        total_calories=parsed_meal.total_calories,
        total_protein=parsed_meal.total_protein,
        total_carbs=parsed_meal.total_carbs,
        total_fat=parsed_meal.total_fat,
        items=db_items
    )
    
    session.add(db_meal)
    session.commit()
    session.refresh(db_meal)
    
    return parsed_meal

@app.get("/api/v1/meals", response_model=List[MealResponse])
def get_meals(session: Session = Depends(get_session)):
    """
    Retrieves the history of all logged meals with their itemized food details.
    """
    from sqlmodel import select
    statement = select(Meal)
    results = session.exec(statement).all()
    return results

@app.get("/health")
def health_check():
    return {
        "status": "Server is running successfully",
        "status_code": 200
    }
