import os
from typing import List
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import create_engine, Session, Field, SQLModel, select, text
from dotenv import load_dotenv
from openai import OpenAI
import openai
from datetime import datetime, timezone
from pydantic_settings import BaseSettings, SettingsConfigDict

from prompts import SYSTEM_PROMPT
from embeddings import find_closest_food

# ##############################################################################
# DATABASE & APP SETUP
# ##############################################################################

dotenv_path = os.path.dirname(__file__)

class Settings(BaseSettings):
    database_url: str
    openai_api_key: str

    model_config = SettingsConfigDict(env_file=os.path.join(dotenv_path, ".env"))

settings = Settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)

def get_db():
    """Dependency to provide a database session to FastAPI endpoints."""
    with Session(engine) as session:
        yield session

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Enable pgvector and create tables on startup if they don't exist
    if "postgresql" in settings.database_url:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
    SQLModel.metadata.create_all(engine)
    yield

app = FastAPI(title="LyfSync Nutrition Tracking API (Simplified)", version="1.0.0", lifespan=lifespan)
llm_client = OpenAI(api_key=settings.openai_api_key)



# ##############################################################################
# DATABASE TABLE
# ##############################################################################

class MealTable(SQLModel, table=True):
    """Represents a completed meal log saved by the user."""
    __tablename__ = "meals"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    raw_text: str             
    meal_type: str            # breakfast, lunch, dinner, snack
    calories: float
    protein: float
    carbs: float
    fat: float
    created_at: datetime = Field(default_factory= lambda: datetime.now(timezone.utc))

class MealItemTable(SQLModel, table=True):
    """Represents a single food item in a meal."""
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


# ##############################################################################
# PYDANTIC SCHEMAS (For API Validation & LLM Output)
# ##############################################################################

class MealItem(BaseModel):
    name: str
    weight_grams: float
    calories: float
    protein: float
    carbs: float
    fat: float

class Meal(BaseModel):
    meal_type: str
    items: List[MealItem]
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float

class ParsedMeal(BaseModel):
    """The complete structured response expected from the LLM."""
    meal_type: str
    items: List[MealItem]

class UserInput(BaseModel):
    """API request schema containing user raw text log."""
    text: str


# ##############################################################################
# HELPER FUNCTIONS
# ##############################################################################

def parse_nutrition_from_text(text: str) -> ParsedMeal:
    """Sends the user text to OpenAI and returns structured nutrition data."""
    completion = llm_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ],
        response_format=ParsedMeal,
        temperature=0.0
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise ValueError("Failed to parse nutrition data from text.")
    return parsed


# ##############################################################################
# API ENDPOINTS
# ##############################################################################

@app.post("/api/v1/meals/parse", response_model=Meal)
def parse_meal(request: UserInput, db: Session = Depends(get_db)):
    """
    Parses a natural language meal log, sums up the estimated macros, 
    and saves it to the local SQLite database.
    """
    # 1. Ask the LLM to parse the text and estimate macros
    try:
        llm_result = parse_nutrition_from_text(request.text)
    except openai.APIError as e:
        print(f"OpenAI API Error: {e}")
        raise HTTPException(status_code=502, detail="AI service unavailable")
    except ValueError as e:
        print(f"Parsing Error: {e}")
        raise HTTPException(status_code=400, detail="Failed to parse meal description")

    # 2. Sum up the macros from all identified foods (checking local database for semantic matches)
    total_cal = 0.0
    total_prot = 0.0
    total_carb = 0.0
    total_fat = 0.0

    for item in llm_result.items:
        # Check if we have a semantic vector match in our local food database
        match = find_closest_food(item.name, db)
        if match:
            # Scale database nutritional values (stored per 100g) by the LLM-determined weight
            scale = item.weight_grams / 100.0
            total_cal += match["calories"] * scale
            total_prot += match["protein"] * scale
            total_carb += match["carbs"] * scale
            total_fat += match["fat"] * scale
        else:
            # Fall back to LLM estimations
            total_cal += item.calories
            total_prot += item.protein
            total_carb += item.carbs
            total_fat += item.fat

    # 3. Create and save the DB record for the meal
    db_meal = MealTable(
        raw_text=request.text,
        meal_type=llm_result.meal_type,
        calories=round(total_cal, 2),
        protein=round(total_prot, 2),
        carbs=round(total_carb, 2),
        fat=round(total_fat, 2)
    )
    
    db.add(db_meal)
    db.commit()
    db.refresh(db_meal)
    
    # 4. Save the individual meal items
    response_items = []
    for item in llm_result.items:
        match = find_closest_food(item.name, db)
        source = "db_match" if match else "llm_fallback"
        
        # Recalculate scaled macros just for this item
        if match:
            scale = item.weight_grams / 100.0
            item_cal = match["calories"] * scale
            item_prot = match["protein"] * scale
            item_carb = match["carbs"] * scale
            item_fat = match["fat"] * scale
        else:
            item_cal = item.calories
            item_prot = item.protein
            item_carb = item.carbs
            item_fat = item.fat
            
        db_item = MealItemTable(
            meal_id=db_meal.id,
            name=item.name,
            weight_grams=item.weight_grams,
            calories=round(item_cal, 2),
            protein=round(item_prot, 2),
            carbs=round(item_carb, 2),
            fat=round(item_fat, 2),
            source=source
        )
        db.add(db_item)
        
        # Build the response object for this item
        response_items.append(
            MealItem(
                name=db_item.name,
                weight_grams=db_item.weight_grams,
                calories=db_item.calories,
                protein=db_item.protein,
                carbs=db_item.carbs,
                fat=db_item.fat
            )
        )
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save meal")
    
    # 5. Return the expected API schema
    return Meal(
        meal_type=db_meal.meal_type,
        items=response_items,
        total_calories=db_meal.calories,
        total_protein=db_meal.protein,
        total_carbs=db_meal.carbs,
        total_fat=db_meal.fat
    )


@app.get("/api/v1/meals", response_model=List[MealTable])
def list_meals(db: Session = Depends(get_db)):
    """Retrieves all previously logged meals from the SQLite database."""
    meals = db.exec(select(MealTable)).all()
    return meals


@app.get("/health")
def health_check():
    """Simple API health check endpoint."""
    return {
        "status": "Server is running successfully",
        "status_code": 200
    }
