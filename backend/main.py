# ==============================================================================
# LyfSync Nutrition Tracking API (main.py)
# This module implements the core FastAPI server, database SQLModels,
# and the multi-stage NLP pipeline for parsing natural language food logs.
# ==============================================================================

import os
import json
from typing import List, Optional, Dict
from datetime import datetime
from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlmodel import create_engine, Session, Field, SQLModel, select
from dotenv import load_dotenv
from sqlalchemy import Column
from pgvector.sqlalchemy import Vector
from openai import OpenAI

from prompts import (
    EXTRACT_DISHES_SYSTEM_PROMPT,
    PARSE_PORTIONS_SYSTEM_PROMPT,
    GENERATE_RECIPE_SYSTEM_PROMPT,
    JUDGE_RECIPE_SYSTEM_PROMPT,
    build_portion_prompt,
    JURY_GENERATION_PROMPT_TEMPLATE,
    build_jury_judge_prompt
)
import asyncio

# ##############################################################################
# DATABASE CONNECTION & SETUP
# ##############################################################################

# Load environment variables from the backend directory .env file
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path, override=True)

# Initialize SQLAlchemy/SQLModel database engine
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# Dependency to provide a database session to FastAPI endpoints
def get_db():
    with Session(engine) as session:
        yield session

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="LyfSync Nutrition Tracking API", version="1.0.0", lifespan=lifespan)


# ##############################################################################
# DATABASE TABLES (SQLModels)
# ##############################################################################

# Represents a completed meal log saved by the user
class Meal(SQLModel, table=True):
    __tablename__ = "meals"

    id: Optional[int] = Field(default=None, primary_key=True)
    raw_text: str             # The raw text input logged by the user
    meal_type: str            # breakfast, lunch, dinner, snack
    calories: float
    protein: float
    carbs: float
    fat: float
    created_at: datetime = Field(default_factory=datetime.utcnow)


# USDA Raw food database containing base ingredient nutrition mappings
class USDARaw(SQLModel, table=True):
    __tablename__ = "usda_raw"

    fdc_id: int = Field(primary_key=True)
    description: str = Field(index=True)
    calories: float = Field(default=0.0)
    protein: float = Field(default=0.0)
    carbs: float = Field(default=0.0)
    fat: float = Field(default=0.0)
    # 1536-dimensional vector embedding of the description for semantic search
    embedding: Optional[List[float]] = Field(sa_column=Column(Vector(1536), nullable=True))


# Indian food database (ICMR) containing regional food nutrition mappings
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
    # 1536-dimensional vector embedding of the food name for semantic search
    embedding: Optional[List[float]] = Field(sa_column=Column(Vector(1536), nullable=True))


# Staples table containing pre-computed recipe templates for cooked dishes
class Staple(SQLModel, table=True):
    __tablename__ = "staples"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True) # Name of the dish (e.g. 'Dal Tadka')
    serving_size: str                          # Baseline portion (e.g. '1 bowl (150g)')
    ingredients_text: str                      # Comma-separated raw ingredients and weights
    instructions: str                          # Standard cooking steps
    # Vector embedding of the staple name for semantic search
    embedding: Optional[List[float]] = Field(sa_column=Column(Vector(1536), nullable=True))


# Table to store new cooked dishes undergoing AI-Synthesizer (Jury) baseline review
class StaplesReview(SQLModel, table=True):
    __tablename__ = "staples_review"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    serving_size: str
    ingredients_text: str
    instructions: str


# Stores canonical serving sizes for foods (e.g., '1 slice of bread' -> 30g)
class ReferenceServing(SQLModel, table=True):
    __tablename__ = "reference_servings"

    id: Optional[int] = Field(default=None, primary_key=True)
    food_name: str = Field(index=True)
    unit: str                                  # Standardized unit (e.g., 'slice', 'piece')
    gram_weight: float                         # Gram weight conversion value
    n_samples: int = Field(default=1)





# API request schema containing user raw text log
class UserInput(BaseModel):
    text: str


# ##############################################################################
# CLIENT INITIALIZATIONS
# ##############################################################################

# OpenAI client for Embeddings and Structured Output parser completion calls
llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ##############################################################################
# PYDANTIC SCHEMAS FOR NLP PIPELINE
# ##############################################################################

# Represents an extracted dish from the user text (Stage 1)
class ExtractedDish(BaseModel):
    original_name: str
    logged_portion: str
    is_cooked_dish: bool

class DishExtractionResponse(BaseModel):
    items: List[ExtractedDish]


# Core Unified Node that flows through the pipeline
class FoodNode(BaseModel):
    # Stage 1: Extraction
    original_name: str
    logged_portion: str
    is_cooked_dish: bool
    
    # Stage 2: Grounding
    food_id: Optional[str] = None
    db_type: Optional[str] = None
    canonical_name: Optional[str] = None
    retrieval_conf: float = 1.0
    
    # Stage 3: Parsing
    quantity: float = 0.0
    unit: str = ""
    state: str = "unknown"
    quantifier_type: str = "explicit"
    is_decomposed: bool = False
    
    # Stage 4/5: Conversion & Macros
    weight_g: Optional[float] = None
    calories: float = 0.0
    protein: float = 0.0
    carbs: float = 0.0
    fat: float = 0.0
    
    # Final confidence
    confidence: float = 1.0


# Structured portion component extracted by LLM parser (Stage 3)
class ParsedComponent(BaseModel):
    source_index: int         # Links back to FoodNode list index
    food_name: str            # Raw food name
    quantity: float
    unit: str
    state: str
    quantifier_type: str


# Represents standard recipe format for review candidates
class NewStapleCandidate(BaseModel):
    name: str
    serving_size: str
    ingredients_text: str
    instructions: str


# Structured output response from portion parsing LLM
class PortionExtractionResponse(BaseModel):
    meal_type: str
    components: List[ParsedComponent]
    new_candidates: Optional[List[NewStapleCandidate]] = None


# Wrapper response for single baseline recipe draft
class SingleRecipeResponse(BaseModel):
    recipe: NewStapleCandidate


# ##############################################################################
# SERVICES
# ##############################################################################

def llm_parse(system_prompt: str, user_content: str, response_format, temperature: float = 0.0):
    """Wrapper for all OpenAI structured completions."""
    completion = llm_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        response_format=response_format,
        temperature=temperature
    )
    parsed = completion.choices[0].message.parsed
    if not parsed:
        raise ValueError("Failed to parse response structure from OpenAI.")
    return parsed


def get_embedding(text: str) -> List[float]:
    """Generates a 1536-dimensional vector embedding for text."""
    try:
        response = llm_client.embeddings.create(model="text-embedding-3-small", input=[text])
        return response.data[0].embedding
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI embedding generation failed: {str(e)}")








class FoodResolver:
    """Owns the DB session. Handles embedding search, ID lookups, and match routing."""
    def __init__(self, db: Session):
        self.db = db

    def fetch_by_id(self, food_id: str, db_type: str):
        """O(1) DB lookup by canonical ID."""
        try:
            if db_type == "usda":
                fdc_id = int(food_id.split("_")[1])
                return self.db.exec(select(USDARaw).where(USDARaw.fdc_id == fdc_id)).first()
            elif db_type == "icmr":
                return self.db.get(ICMRRaw, int(food_id.split("_")[1]))
            elif db_type == "staple":
                return self.db.get(Staple, int(food_id.split("_")[1]))
        except Exception as e:
            print(f"Error looking up {food_id}: {e}")
        return None

    def resolve(self, food_name: str, is_cooked_dish: bool) -> Optional[tuple]:
        """Returns (food_id, db_type, canonical_name, distance, ret_conf, matched_model) or None."""
        emb = get_embedding(food_name)
        candidates = []

        if is_cooked_dish:
            dist = Staple.embedding.cosine_distance(emb)
            row = self.db.exec(select(Staple, dist).order_by(dist).limit(1)).first()
            if row: candidates.append(("staple", row[0], row[1]))

        dist = ICMRRaw.embedding.cosine_distance(emb)
        row = self.db.exec(select(ICMRRaw, dist).order_by(dist).limit(1)).first()
        if row: candidates.append(("icmr", row[0], row[1]))

        dist = USDARaw.embedding.cosine_distance(emb)
        row = self.db.exec(select(USDARaw, dist).order_by(dist).limit(1)).first()
        if row: candidates.append(("usda", row[0], row[1]))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[2])
        best_type, best_model, best_distance = candidates[0]
        staple_cand = next((c for c in candidates if c[0] == "staple"), None)

        if staple_cand and staple_cand[2] <= 0.38:
            model = staple_cand[1]
            ret_conf = max(0.0, 1.0 - (staple_cand[2] / 0.75))
            return (f"STAPLE_{model.id}", "staple", model.name, staple_cand[2], ret_conf, model)

        raw_match_valid = best_distance <= 0.30 if best_type in ("icmr", "usda") else False
        ret_conf = max(0.0, 1.0 - (best_distance / 0.75))

        if raw_match_valid:
            canonical_name = best_model.food_name if best_type == "icmr" else best_model.description
            item_id = f"ICMR_{best_model.id}" if best_type == "icmr" else f"USDA_{best_model.fdc_id}"
            return (item_id, best_type, canonical_name, best_distance, ret_conf, best_model)

        if is_cooked_dish:
            return ("UNMATCHED", "none", "Unknown Cooked Dish", 1.0, 0.0, None)

        canonical_name = best_model.food_name if best_type == "icmr" else best_model.description
        item_id = f"ICMR_{best_model.id}" if best_type == "icmr" else f"USDA_{best_model.fdc_id}"
        return (item_id, best_type, canonical_name, best_distance, ret_conf, best_model)





# ##############################################################################
# BACKGROUND JURY TASKS
# ##############################################################################

async def run_jury_and_update_review(dish_name: str, review_id: int):
    """Background worker task to trigger the Jury baseline synthesis process."""
    try:
        prompt = JURY_GENERATION_PROMPT_TEMPLATE.format(dish_name=dish_name)
        
        drafts = await asyncio.gather(
            asyncio.to_thread(llm_parse, GENERATE_RECIPE_SYSTEM_PROMPT, prompt, SingleRecipeResponse, 0.3),
            asyncio.to_thread(llm_parse, GENERATE_RECIPE_SYSTEM_PROMPT, prompt, SingleRecipeResponse, 0.3),
            asyncio.to_thread(llm_parse, GENERATE_RECIPE_SYSTEM_PROMPT, prompt, SingleRecipeResponse, 0.3)
        )
        
        drafts_text = "\n\n".join([f"Draft {i+1}:\n{d.recipe.model_dump_json(indent=2)}" for i, d in enumerate(drafts)])
        judge_prompt = build_jury_judge_prompt(dish_name, drafts_text)
        
        final_res = await asyncio.to_thread(llm_parse, JUDGE_RECIPE_SYSTEM_PROMPT, judge_prompt, SingleRecipeResponse, 0.0)
        final_recipe = final_res.recipe
        
        with Session(engine) as session:
            review_row = session.get(StaplesReview, review_id)
            if review_row:
                review_row.serving_size = final_recipe.serving_size
                review_row.ingredients_text = final_recipe.ingredients_text
                review_row.instructions = final_recipe.instructions
                session.commit()
                print(f"Jury successfully updated staples_review for {dish_name}")
    except Exception as e:
        print(f"Jury background task failed for {dish_name}: {e}")

# ##############################################################################
# PIPELINE STAGES
# ##############################################################################


class MealPipeline:
    """Orchestrates the NLP parsing pipeline. Each method is one stage."""
    def __init__(self, text: str, db: Session, background_tasks: BackgroundTasks):
        self.text = text
        self.db = db
        self.background_tasks = background_tasks
        self.resolver = FoodResolver(db)

        self.nodes: List[FoodNode] = []
        self.meal_type = "unknown"
        self.grounding_context: Dict[str, dict] = {}
        self.new_candidates = []
        self.needs_clarification = False

    def execute(self) -> Meal:
        self.extract()
        if not self.nodes:
            raise HTTPException(status_code=400, detail="No food items could be extracted from your query.")
        self.ground()
        self.parse_portions()
        self.convert()
        self.nutrition()
        return self.persist()

    def extract(self):
        """Stage 1: Segment user text into discrete FoodNodes via LLM."""
        try:
            parsed = llm_parse(EXTRACT_DISHES_SYSTEM_PROMPT, self.text, DishExtractionResponse)
            for item in parsed.items:
                self.nodes.append(FoodNode(
                    original_name=item.original_name,
                    logged_portion=item.logged_portion,
                    is_cooked_dish=item.is_cooked_dish
                ))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"OpenAI dish extraction failed: {str(e)}")

    def ground(self):
        """Stage 2: Resolve each FoodNode against the DB and build LLM context templates."""
        for node in self.nodes:
            res = self.resolver.resolve(node.original_name, node.is_cooked_dish)
            if res:
                food_id, db_type, canonical_name, distance, ret_conf, matched_model = res
                node.food_id = food_id
                node.db_type = db_type
                node.canonical_name = canonical_name
                node.retrieval_conf = ret_conf
                
                if db_type == "staple":
                    template = {
                        "template_type": "staple",
                        "serving_size": matched_model.serving_size,
                        "ingredients_text": matched_model.ingredients_text,
                        "instructions": matched_model.instructions
                    }
                elif db_type in ("usda", "icmr"):
                    name = matched_model.food_name if db_type == "icmr" else matched_model.description
                    template = {
                        "template_type": "raw",
                        "serving_size": "100g",
                        "ingredients_text": f"100g {name}",
                        "instructions": "Consume raw or prep as desired."
                    }
                else:
                    template = {
                        "template_type": "unmatched_cooked",
                        "serving_size": "1 portion",
                        "ingredients_text": "Unknown cooked recipe (requires decomposition)",
                        "instructions": "Decompose this dish into raw ingredients."
                    }
                self.grounding_context[node.original_name] = template

    def parse_portions(self):
        """Stage 3: LLM extracts structured quantity/unit/state and handles dish decomposition."""
        prompt = build_portion_prompt(self.text, self.nodes, self.grounding_context)
        try:
            parsed = llm_parse(PARSE_PORTIONS_SYSTEM_PROMPT, prompt, PortionExtractionResponse)
            self.meal_type = parsed.meal_type
            if parsed.new_candidates:
                self.new_candidates.extend(parsed.new_candidates)

            new_nodes = []
            for comp in parsed.components:
                source_node = self.nodes[comp.source_index] if 0 <= comp.source_index < len(self.nodes) else None
                if not source_node: continue

                is_decomposed = (source_node.original_name.lower() != comp.food_name.lower() and source_node.is_cooked_dish)
                new_nodes.append(FoodNode(
                    original_name=comp.food_name,
                    logged_portion=source_node.logged_portion,
                    is_cooked_dish=False if is_decomposed else source_node.is_cooked_dish,
                    food_id=None if is_decomposed else source_node.food_id,
                    db_type=None if is_decomposed else source_node.db_type,
                    canonical_name=None if is_decomposed else source_node.canonical_name,
                    retrieval_conf=0.0 if is_decomposed else source_node.retrieval_conf,
                    quantity=comp.quantity,
                    unit=comp.unit,
                    state=comp.state,
                    quantifier_type=comp.quantifier_type,
                    is_decomposed=is_decomposed
                ))
            self.nodes = new_nodes
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"OpenAI portion parsing failed: {str(e)}")

    def convert(self):
        """Stage 4: Convert units to grams and resolve cooking state."""
        from unit_converter import convert_to_grams
        for node in self.nodes:
            parser_conf = 1.0 if node.quantifier_type == "explicit" else 0.5
            weight_g, converter_conf, final_state = convert_to_grams(
                node.original_name, node.quantity, node.unit, node.state, self.db
            )
            node.state = final_state
            node.weight_g = weight_g
            if weight_g is None:
                self.needs_clarification = True
                print(f"WARNING: Clarification needed. Could not convert {node.quantity} {node.unit} of {node.original_name}")
                node.confidence = 0.0
            else:
                node.confidence = parser_conf * converter_conf

    def nutrition(self):
        """Stage 5: Look up macros. Runs a fallback embedding search for decomposed ingredients."""
        for node in self.nodes:
            if node.weight_g is None: continue

            # Decomposed ingredients (or cooked dishes that weren't decomposed) need their own grounding search in raw/US/ICMR databases.
            if node.is_decomposed or not node.food_id or node.db_type == "staple":
                res = self.resolver.resolve(node.original_name, False)
                if not res:
                    self.needs_clarification = True
                    continue
                food_id, db_type, canonical_name, distance, ret_conf, _ = res
                node.food_id, node.db_type, node.canonical_name, node.retrieval_conf = food_id, db_type, canonical_name, ret_conf
                if distance > 0.75:
                    self.needs_clarification = True
                    print(f"WARNING: Match distance {distance:.3f} too high for {node.original_name}")
                    continue

            db_model = self.resolver.fetch_by_id(node.food_id, node.db_type)
            if not db_model:
                self.needs_clarification = True
                continue

            wf = node.weight_g / 100.0
            node.calories = db_model.calories * wf
            node.protein = db_model.protein * wf
            node.carbs = db_model.carbs * wf
            node.fat = db_model.fat * wf
            node.confidence *= node.retrieval_conf
            if node.confidence < 0.6:
                self.needs_clarification = True

    def persist(self) -> Meal:
        """Stage 6: Clamp macros, save the Meal, and spawn background Jury tasks."""
        total_cal = sum((n.calories for n in self.nodes if n.weight_g is not None), 0.0)
        total_prot = sum((n.protein for n in self.nodes if n.weight_g is not None), 0.0)
        total_carb = sum((n.carbs for n in self.nodes if n.weight_g is not None), 0.0)
        total_fat = sum((n.fat for n in self.nodes if n.weight_g is not None), 0.0)

        CAL_CAP = 3500.0
        if total_cal > CAL_CAP:
            ratio = CAL_CAP / total_cal
            total_cal, total_prot, total_carb, total_fat = CAL_CAP, total_prot * ratio, total_carb * ratio, total_fat * ratio

        db_meal = Meal(
            raw_text=self.text,
            meal_type=self.meal_type,
            calories=round(total_cal, 2),
            protein=round(total_prot, 2),
            carbs=round(total_carb, 2),
            fat=round(total_fat, 2)
        )
        self.db.add(db_meal)

        if self.new_candidates:
            cooked_fallback_names = {
                k for k, v in self.grounding_context.items()
                if v.get("template_type") in ("raw", "unmatched_cooked")
            }
            for cand in self.new_candidates:
                is_relevant = any(fn.lower() in cand.name.lower() or cand.name.lower() in fn.lower() for fn in cooked_fallback_names)
                if not is_relevant and cand.name not in cooked_fallback_names:
                    continue
                exists_staples = self.db.exec(select(Staple).where(Staple.name == cand.name)).first()
                exists_review = self.db.exec(select(StaplesReview).where(StaplesReview.name == cand.name)).first()
                if not exists_staples and not exists_review:
                    review_row = StaplesReview(name=cand.name, serving_size=cand.serving_size,
                                               ingredients_text=cand.ingredients_text, instructions=cand.instructions)
                    self.db.add(review_row)
                    self.db.commit()
                    self.db.refresh(review_row)
                    self.background_tasks.add_task(run_jury_and_update_review, cand.name, review_row.id)

        self.db.commit()
        self.db.refresh(db_meal)
        return db_meal




@app.post("/api/v1/meals/parse", response_model=Meal)
def parse_meal(request: UserInput, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Parses natural language meal logs, estimates macros, and persists the meal to the database.
    This endpoint executes the multi-stage parsing pipeline using the unified MealPipeline.
    """
    pipeline = MealPipeline(request.text, db, background_tasks)
    return pipeline.execute()


@app.get("/api/v1/meals", response_model=List[Meal])
def list_meals(db: Session = Depends(get_db)):
    """
    Retrieves all previously logged meals from the database.
    """
    meals = db.exec(select(Meal)).all()
    return meals


@app.get("/health")
def health_check():
    """
    Simple API health check endpoint.
    """
    return {
        "status": "Server is running successfully",
        "status_code": 200
    }
