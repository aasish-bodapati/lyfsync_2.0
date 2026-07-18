"""
main.py — FastAPI application entrypoint.

Responsibilities:
  - App/DB startup
  - Route definitions (thin: delegate all logic to nutrition_service)

Schema authority: Supabase migrations.
create_all() is restricted to non-Postgres environments (local SQLite testing only).
"""
import os
import logging
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException, Depends
from sqlmodel import create_engine, Session, SQLModel, select, text
from openai import OpenAI
from pydantic_settings import BaseSettings, SettingsConfigDict

from schemas import UserInput, Meal
from models import MealTable
from nutrition_service import safe_parse_text, resolve_nutrition, persist_meal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    database_url: str
    openai_api_key: str

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), ".env")
    )


settings = Settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
llm_client = OpenAI(api_key=settings.openai_api_key)


def get_db():
    with Session(engine) as session:
        yield session


@asynccontextmanager
async def lifespan(app: FastAPI):
    is_postgres = "postgresql" in settings.database_url
    if is_postgres:
        # Enable pgvector extension (idempotent)
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
    else:
        # SQLite / local dev only — production uses Supabase migrations
        SQLModel.metadata.create_all(engine)
    yield


app = FastAPI(
    title="LyfSync Nutrition Tracking API",
    version="2.0.0",
    lifespan=lifespan,
)


@app.post("/api/v1/meals/parse", response_model=Meal)
def parse_meal(request: UserInput, db: Session = Depends(get_db)):
    """
    Parses a natural-language meal log, resolves macros, and persists to DB.
    """
    parsed = safe_parse_text(request.text, llm_client)
    total_cal, total_prot, total_carb, total_fat, items = resolve_nutrition(
        parsed, db, llm_client
    )
    db_meal = persist_meal(
        db, request.text, parsed.meal_type,
        (total_cal, total_prot, total_carb, total_fat), items
    )
    return Meal(
        meal_type=db_meal.meal_type,
        items=items,
        total_calories=db_meal.calories,
        total_protein=db_meal.protein,
        total_carbs=db_meal.carbs,
        total_fat=db_meal.fat,
    )


@app.get("/api/v1/meals", response_model=List[MealTable])
def list_meals(db: Session = Depends(get_db)):
    """Returns all persisted meal logs."""
    return db.exec(select(MealTable)).all()


@app.get("/health")
def health_check():
    return {"status": "Server is running successfully", "status_code": 200}
