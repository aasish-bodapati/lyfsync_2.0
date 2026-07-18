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
    confidence: float | None = None


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
    source: str | None = None
    confidence: float | None = None

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

def safe_parse_text(text: str) -> ParsedMeal:
    try:
        return parse_nutrition_from_text(text)
    except openai.APIError as e:
        print(f"OpenAI API Error: {e}")
        raise HTTPException(status_code=502, detail="AI service unavailable")
    except ValueError as e:
        print(f"Parsing Error: {e}")
        raise HTTPException(status_code=400, detail="Failed to parse meal description")

def resolve_nutrition(parsed_meal: ParsedMeal, db: Session, client: OpenAI) -> tuple[float, float, float, float, List[MealItem]]:
    total_cal = total_prot = total_carb = total_fat = 0.0
    resolved_items = []
    
    for item in parsed_meal.items:
        match = find_closest_food(item.name, db, client)
        
        if match:
            scale = item.weight_grams / 100.0
            item_cal = match["calories"] * scale
            item_prot = match["protein"] * scale
            item_carb = match["carbs"] * scale
            item_fat = match["fat"] * scale
            confidence = match["similarity_score"]
            source = "db_match_high" if confidence >= 0.80 else "db_match_low"
        else:
            item_cal = item.calories
            item_prot = item.protein
            item_carb = item.carbs
            item_fat = item.fat
            confidence = None
            source = "llm_fallback"
            
        total_cal += item_cal
        total_prot += item_prot
        total_carb += item_carb
        total_fat += item_fat
        
        resolved_items.append(MealItem(
            name=item.name,
            weight_grams=item.weight_grams,
            calories=round(item_cal, 2),
            protein=round(item_prot, 2),
            carbs=round(item_carb, 2),
            fat=round(item_fat, 2),
            source=source,
            confidence=confidence
        ))
        
    return total_cal, total_prot, total_carb, total_fat, resolved_items

def persist_meal(db: Session, text: str, meal_type: str, totals: tuple[float, float, float, float], items: List[MealItem]) -> MealTable:
    db_meal = MealTable(
        raw_text=text,
        meal_type=meal_type,
        calories=round(totals[0], 2),
        protein=round(totals[1], 2),
        carbs=round(totals[2], 2),
        fat=round(totals[3], 2)
    )
    try:
        db.add(db_meal)
        db.flush() # Get the ID without committing yet
        
        for item in items:
            db_item = MealItemTable(
                meal_id=db_meal.id,
                name=item.name,
                weight_grams=item.weight_grams,
                calories=item.calories,
                protein=item.protein,
                carbs=item.carbs,
                fat=item.fat,
                source=item.source,
                confidence=item.confidence
            )
            db.add(db_item)
            
        db.commit()
        db.refresh(db_meal)
    except Exception as e:
        db.rollback()
        print(f"Database Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save meal")
        
    return db_meal

@app.post("/api/v1/meals/parse", response_model=Meal)
def parse_meal(request: UserInput, db: Session = Depends(get_db)):
    """
    Parses a natural language meal log, sums up the estimated macros, 
    and saves it to the database.
    """
    llm_result = safe_parse_text(request.text)
    total_cal, total_prot, total_carb, total_fat, resolved_items = resolve_nutrition(llm_result, db, llm_client)
    
    db_meal = persist_meal(db, request.text, llm_result.meal_type, (total_cal, total_prot, total_carb, total_fat), resolved_items)
    
    return Meal(
        meal_type=db_meal.meal_type,
        items=resolved_items,
        total_calories=db_meal.calories,
        total_protein=db_meal.protein,
        total_carbs=db_meal.carbs,
        total_fat=db_meal.fat
    )


@app.get("/api/v1/meals", response_model=List[MealTable])
def list_meals(db: Session = Depends(get_db)):
    """Retrieves all previously logged meals from the database."""
    meals = db.exec(select(MealTable)).all()
    return meals


@app.get("/health")
def health_check():
    """Simple API health check endpoint."""
    return {
        "status": "Server is running successfully",
        "status_code": 200
    }
