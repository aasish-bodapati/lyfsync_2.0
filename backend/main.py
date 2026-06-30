import os
import json
from typing import List, Optional
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import create_engine, Session, Field, SQLModel, select
from dotenv import load_dotenv
from sqlalchemy import Column
from pgvector.sqlalchemy import Vector
from openai import OpenAI

# Load environment variables
load_dotenv(override=True)

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

def get_db():
    with Session(engine) as session:
        yield session

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure vector extension is enabled before creating tables
    from sqlalchemy import text
    with Session(engine) as session:
        session.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        session.commit()
    # Initialize SQLModel tables on startup
    SQLModel.metadata.create_all(engine)
    yield

app = FastAPI(title="LyfSync Nutrition Tracking API", version="1.0.0", lifespan=lifespan)


# --- Database Models & Pydantic Schemas ---
class Meal(SQLModel, table=True):
    __tablename__ = "meals"

    id: Optional[int] = Field(default=None, primary_key=True)
    raw_text: str
    meal_type: str
    calories: float
    protein: float
    carbs: float
    fat: float
    created_at: datetime = Field(default_factory=datetime.utcnow)


class USDARaw(SQLModel, table=True):
    __tablename__ = "usda_raw"

    fdc_id: int = Field(primary_key=True)
    description: str = Field(index=True)
    calories: float = Field(default=0.0)
    protein: float = Field(default=0.0)
    carbs: float = Field(default=0.0)
    fat: float = Field(default=0.0)
    embedding: Optional[List[float]] = Field(sa_column=Column(Vector(1536), nullable=True))


class ICMRRaw(SQLModel, table=True):
    __tablename__ = "icmr_raw"

    id: Optional[int] = Field(default=None, primary_key=True)
    food_code: str = Field(index=True, unique=True)
    food_name: str = Field(index=True)
    category: str
    calories: float = Field(default=0.0)
    protein: float = Field(default=0.0)
    carbs: float = Field(default=0.0)
    fat: float = Field(default=0.0)
    embedding: Optional[List[float]] = Field(sa_column=Column(Vector(1536), nullable=True))


class MealResponse(BaseModel):
    meal_type: str
    calories: float
    protein: float
    carbs: float
    fat: float


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
                        "Analyze the user's input, categorize the meal (breakfast, lunch, dinner, or snack), "
                        "and estimate the total macros (calories in kcal, protein, carbs, and fat in grams) "
                        "for the entire meal consumed."
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
@app.post("/api/v1/meals/parse", response_model=Meal)
def parse_meal(request: UserInput, db: Session = Depends(get_db)):
    """
    Parses natural language meal logs, estimates macros, and persists the meal to the database.
    """
    parsed = parse_with_openai(request)
    
    db_meal = Meal(
        raw_text=request.text,
        meal_type=parsed.meal_type,
        calories=parsed.calories,
        protein=parsed.protein,
        carbs=parsed.carbs,
        fat=parsed.fat
    )
    db.add(db_meal)
    db.commit()
    db.refresh(db_meal)
    return db_meal


@app.get("/api/v1/meals", response_model=List[Meal])
def list_meals(db: Session = Depends(get_db)):
    """
    Retrieves all previously logged meals from the database.
    """
    meals = db.exec(select(Meal)).all()
    return meals


@app.get("/health")
def health_check():
    return {
        "status": "Server is running successfully",
        "status_code": 200
    }

