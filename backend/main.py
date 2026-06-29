import os
import json
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlmodel import create_engine, Session, Field
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

app = FastAPI(title="LyfSync Nutrition Tracking API", version="1.0.0")



# --- Pydantic Schemas ---
class FoodResponse(BaseModel):
    name: str
    quantity: int
    calories: float
    protein: float
    carbs: float
    fat: float

class MealItem(BaseModel):
    meal_type: str
    items: List[FoodResponse]

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
def parse_with_openai(request: UserInput) -> MealItem:
    try:
        completion = llm_client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise nutrition and macronutrient estimation assistant. "
                        "Analyze the user's input, extract all individual food items, and categorize the meal "
                        "(breakfast, lunch, dinner, or snack). For each food item, identify the quantity "
                        "(default to 1 if not specified) and estimate the macros (calories in kcal, protein, "
                        "carbs, and fat in grams) for the ENTIRE PORTION of that food item consumed."
                    )
                },
                {"role": "user", "content": request.text}
            ],
            response_format=MealItem,
        )
        parsed = completion.choices[0].message.parsed
        if parsed:
            return parsed
        raise ValueError("Failed to parse response structure from OpenAI.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI parsing failed: {str(e)}")


# --- Endpoints ---
@app.post("/api/v1/meals/parse", response_model=MealResponse)
def parse_meal(request: UserInput):
    """
    Parses natural language meal logs and returns an itemized macronutrient breakdown.
    """
    parsed = parse_with_openai(request)
    
    total_calories = sum(item.calories for item in parsed.items)
    total_protein = sum(item.protein for item in parsed.items)
    total_carbs = sum(item.carbs for item in parsed.items)
    total_fat = sum(item.fat for item in parsed.items)
    
    return MealResponse(
        meal_type=parsed.meal_type,
        items=parsed.items,
        total_calories=total_calories,
        total_protein=total_protein,
        total_carbs=total_carbs,
        total_fat=total_fat
    )

@app.get("/health")
def health_check():
    return {
        "status": "Server is running successfully",
        "status_code": 200
    }
