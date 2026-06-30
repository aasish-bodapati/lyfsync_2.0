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


class Staple(SQLModel, table=True):
    __tablename__ = "staples"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    serving_size: str
    ingredients_text: str
    instructions: str
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


# --- Pydantic Models for RAG Pipeline ---
class LoggedItem(BaseModel):
    food_name: str
    logged_portion: str


class DishExtractionResponse(BaseModel):
    items: List[LoggedItem]


class ParsedRawIngredient(BaseModel):
    raw_ingredient_name: str
    weight_g: float


class RAGScaleResponse(BaseModel):
    meal_type: str
    ingredients: List[ParsedRawIngredient]


# --- AI & Vector Helper Functions ---
def get_embedding(text: str) -> List[float]:
    try:
        response = llm_client.embeddings.create(
            model="text-embedding-3-small",
            input=[text]
        )
        return response.data[0].embedding
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI embedding generation failed: {str(e)}")


def extract_dishes(text: str) -> List[LoggedItem]:
    try:
        completion = llm_client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise food diary parser. Extract the distinct cooked dishes or raw food items "
                        "mentioned in the user's log, along with their portion size/quantity."
                    )
                },
                {"role": "user", "content": text}
            ],
            response_format=DishExtractionResponse,
            temperature=0.0
        )
        parsed = completion.choices[0].message.parsed
        if parsed:
            return parsed.items
        raise ValueError("Failed to parse response structure from OpenAI.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI dish extraction failed: {str(e)}")


def retrieve_grounding_templates(logged_items: List[LoggedItem], db: Session) -> dict:
    templates = {}
    for item in logged_items:
        query_emb = get_embedding(item.food_name)
        
        # 1. Search staples table first
        staples_dist = Staple.embedding.cosine_distance(query_emb)
        best_staple_row = db.exec(
            select(Staple, staples_dist).order_by(staples_dist).limit(1)
        ).first()
        
        # 2. Search raw tables for fallback
        icmr_dist = ICMRRaw.embedding.cosine_distance(query_emb)
        best_icmr_row = db.exec(
            select(ICMRRaw, icmr_dist).order_by(icmr_dist).limit(1)
        ).first()
        
        usda_dist = USDARaw.embedding.cosine_distance(query_emb)
        best_usda_row = db.exec(
            select(USDARaw, usda_dist).order_by(usda_dist).limit(1)
        ).first()
        
        candidates = []
        if best_staple_row:
            candidates.append(("staple", best_staple_row[0], best_staple_row[1]))
        if best_icmr_row:
            candidates.append(("icmr", best_icmr_row[0], best_icmr_row[1]))
        if best_usda_row:
            candidates.append(("usda", best_usda_row[0], best_usda_row[1]))
            
        if not candidates:
            continue
            
        candidates.sort(key=lambda x: x[2])
        best_type, best_model, best_distance = candidates[0]
        
        # Check if a staple is matched within distance 0.45
        staple_cand = next((c for c in candidates if c[0] == "staple"), None)
        
        if staple_cand and staple_cand[2] <= 0.45:
            model = staple_cand[1]
            templates[item.food_name] = {
                "type": "staple",
                "serving_size": model.serving_size,
                "ingredients_text": model.ingredients_text,
                "instructions": model.instructions
            }
        else:
            # Fall back to a raw ingredient template
            if best_type == "icmr":
                templates[item.food_name] = {
                    "type": "raw",
                    "serving_size": "100g",
                    "ingredients_text": f"100g {best_model.food_name}",
                    "instructions": "Consume raw or prep as desired."
                }
            elif best_type == "usda":
                templates[item.food_name] = {
                    "type": "raw",
                    "serving_size": "100g",
                    "ingredients_text": f"100g {best_model.description}",
                    "instructions": "Consume raw or prep as desired."
                }
                
    return templates


def scale_ingredients_with_rag(text: str, templates: dict) -> RAGScaleResponse:
    context_lines = []
    for food_name, temp in templates.items():
        context_lines.append(
            f"Database template for '{food_name}':\n"
            f"  Portion baseline: {temp['serving_size']}\n"
            f"  Raw Ingredients: {temp['ingredients_text']}\n"
            f"  Cooking Steps: {temp['instructions']}"
        )
    templates_context = "\n\n".join(context_lines)
    
    prompt = (
        f"User logged: \"{text}\"\n\n"
        f"REFERENCE DATABASE TEMPLATES:\n"
        f"{templates_context}\n\n"
        "INSTRUCTIONS:\n"
        "1. Categorize the meal (breakfast, lunch, dinner, or snack).\n"
        "2. For each food item the user consumed, match it against the reference templates.\n"
        "3. Estimate the scale factor and output the constituent raw ingredients and their scaled uncooked weights in grams.\n"
        "4. If a dish matches a template, scale all its raw ingredients proportionally. For example, if the standard "
        "portion is '2 pieces (100g)' and uses 100g flour, and the user ate 1 piece, scale it to 50g flour. If the user ate 4 pieces, scale it to 200g flour.\n"
        "5. If a logged item is a raw commodity (like banana or almonds), simply output it with its estimated raw weight.\n"
        "6. Do NOT include water or salt in the raw ingredients list.\n"
    )
    
    try:
        completion = llm_client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise nutrition scaling assistant. Ground all calculations on the provided database templates. "
                        "Scale raw ingredients and weights proportionally based on the user's portion."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            response_format=RAGScaleResponse,
            temperature=0.0
        )
        parsed = completion.choices[0].message.parsed
        if parsed:
            return parsed
        raise ValueError("Failed to parse scale response from OpenAI.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI portion scaling failed: {str(e)}")


# --- Endpoints ---
@app.post("/api/v1/meals/parse", response_model=Meal)
def parse_meal(request: UserInput, db: Session = Depends(get_db)):
    """
    Parses natural language meal logs, estimates macros, and persists the meal to the database.
    """
    # 1. Extract dishes
    logged_items = extract_dishes(request.text)
    if not logged_items:
        raise HTTPException(status_code=400, detail="No food items could be extracted from your query.")
        
    # 2. Retrieve templates
    templates = retrieve_grounding_templates(logged_items, db)
    
    # 3. Scale ingredients
    scaled_res = scale_ingredients_with_rag(request.text, templates)
    
    # 4. Calculate macros mathematically using DB lookups
    total_calories = 0.0
    total_protein = 0.0
    total_carbs = 0.0
    total_fat = 0.0
    
    for ing in scaled_res.ingredients:
        ing_emb = get_embedding(ing.raw_ingredient_name)
        
        icmr_dist = ICMRRaw.embedding.cosine_distance(ing_emb)
        best_icmr = db.exec(
            select(ICMRRaw, icmr_dist).order_by(icmr_dist).limit(1)
        ).first()
        
        usda_dist = USDARaw.embedding.cosine_distance(ing_emb)
        best_usda = db.exec(
            select(USDARaw, usda_dist).order_by(usda_dist).limit(1)
        ).first()
        
        candidates = []
        if best_icmr:
            candidates.append(("icmr", best_icmr[0], best_icmr[1]))
        if best_usda:
            candidates.append(("usda", best_usda[0], best_usda[1]))
            
        if not candidates:
            continue
            
        candidates.sort(key=lambda x: x[2])
        best_db_type, best_db_model, best_db_dist = candidates[0]
        
        weight_factor = ing.weight_g / 100.0
        total_calories += best_db_model.calories * weight_factor
        total_protein += best_db_model.protein * weight_factor
        total_carbs += best_db_model.carbs * weight_factor
        total_fat += best_db_model.fat * weight_factor
        
    # 5. Persist meal
    db_meal = Meal(
        raw_text=request.text,
        meal_type=scaled_res.meal_type,
        calories=round(total_calories, 2),
        protein=round(total_protein, 2),
        carbs=round(total_carbs, 2),
        fat=round(total_fat, 2)
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

