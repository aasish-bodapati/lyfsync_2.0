import os
from typing import List
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import create_engine, Session, Field, SQLModel, select
from dotenv import load_dotenv
from openai import OpenAI
import openai
from datetime import datetime, timezone


from prompts import SYSTEM_PROMPT

# ##############################################################################
# DATABASE & APP SETUP
# ##############################################################################

dotenv_path = os.path.dirname(__file__)

load_dotenv(os.path.join(dotenv_path, ".env"))

# We use an absolute path so the DB is always found in the backend directory
backend_dir = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite:///{os.path.join(backend_dir, 'local_db.db')}"
# check_same_thread=False is needed for SQLite to run safely in multi-threaded FastAPI
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

def get_db():
    """Dependency to provide a database session to FastAPI endpoints."""
    with Session(engine) as session:
        yield session

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically create the SQLite database tables on startup if they don't exist
    SQLModel.metadata.create_all(engine)
    yield

app = FastAPI(title="LyfSync Nutrition Tracking API (Simplified)", version="1.0.0", lifespan=lifespan)
llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# Whenever ANY endpoint raises an OpenAI error, this function intercepts it:
@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    # Log the real error to your terminal so you can debug it:
    print(f"CRITICAL ERROR: {str(exc)}")
    
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Our team has been notified."}
    )

# ##############################################################################
# DATABASE TABLE
# ##############################################################################

class Meal(SQLModel, table=True):
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


# ##############################################################################
# PYDANTIC SCHEMAS (For API Validation & LLM Output)
# ##############################################################################

class FoodItem(BaseModel):
    """Represents a single parsed food item with estimated macros."""
    food_name: str
    weight_grams: float
    calories: float
    protein: float
    carbohydrates: float
    fats: float

class MealItem(BaseModel):
    """The complete structured response expected from the LLM."""
    meal_type: str
    foods: List[FoodItem]

class UserInput(BaseModel):
    """API request schema containing user raw text log."""
    text: str


# ##############################################################################
# HELPER FUNCTIONS
# ##############################################################################

def parse_nutrition_from_text(text: str) -> MealItem:
    """Sends the user text to OpenAI and returns structured nutrition data."""
    completion = llm_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ],
        response_format=MealItem,
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
    llm_result = parse_nutrition_from_text(request.text)

    # 2. Sum up the macros from all identified foods
    total_cal = sum(item.calories for item in llm_result.foods)
    total_prot = sum(item.protein for item in llm_result.foods)
    total_carb = sum(item.carbohydrates for item in llm_result.foods)
    total_fat = sum(item.fats for item in llm_result.foods)

    # 3. Create and save the DB record
    db_meal = Meal(
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
    
    return db_meal


@app.get("/api/v1/meals", response_model=List[Meal])
def list_meals(db: Session = Depends(get_db)):
    """Retrieves all previously logged meals from the SQLite database."""
    meals = db.exec(select(Meal)).all()
    return meals


@app.get("/health")
def health_check():
    """Simple API health check endpoint."""
    return {
        "status": "Server is running successfully",
        "status_code": 200
    }
