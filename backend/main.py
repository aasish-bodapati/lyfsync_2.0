import os
import json
from typing import List, Optional
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


class StaplesReview(SQLModel, table=True):
    __tablename__ = "staples_review"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    serving_size: str
    ingredients_text: str
    instructions: str


class PortionPrior(SQLModel, table=True):
    __tablename__ = "portion_priors"

    id: Optional[int] = Field(default=None, primary_key=True)
    food_name: str = Field(index=True)
    unit: str
    gram_weight: float
    n_samples: int = Field(default=1)


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
    is_cooked_dish: bool


class DishExtractionResponse(BaseModel):
    items: List[LoggedItem]


class ParsedRawIngredient(BaseModel):
    raw_ingredient_name: str
    weight_g: float


class NewStapleCandidate(BaseModel):
    name: str
    serving_size: str
    ingredients_text: str
    instructions: str


class RAGScaleResponse(BaseModel):
    meal_type: str
    ingredients: List[ParsedRawIngredient]
    new_candidates: Optional[List[NewStapleCandidate]] = None


class SingleRecipeResponse(BaseModel):
    recipe: NewStapleCandidate


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
                        "mentioned in the user's log, along with their portion size/quantity.\n\n"
                        "CLASSIFICATION RULE:\n"
                        "- Set `is_cooked_dish` to True if the item is a cooked preparation, recipe, or staple made from multiple ingredients "
                        "(e.g., roti, dal tadka, chicken curry, pasta, lasagna, paratha, omelette, dosa).\n"
                        "- Set `is_cooked_dish` to False if the item is a single raw agricultural commodity, fruit, vegetable, or simple ingredient "
                        "(e.g., banana, raw almonds, avocado, milk, raw spinach, jaggery).\n\n"
                        "DECOMPOSITION RULES:\n"
                        "1. If a logged item contains multiple distinct components cooked or served together "
                        "(e.g., 'rice and chicken curry', 'roti with paneer'), decompose them into separate items "
                        "(e.g., split 'roti with paneer' into 'roti' and 'paneer').\n"
                        "2. If a logged cooked dish is a complex multi-ingredient meal (such as lasagna, pizza, tacos, burritos, pasta with sauce, sandwiches) "
                        "and is not a standard simple staple, decompose it into its primary constituent raw ingredients "
                        "(e.g., decompose 'beef lasagna' into 'ground beef', 'pasta sheets', 'tomato sauce', and 'mozzarella cheese')."
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
        
        # Check if a staple is matched within distance 0.38 (empirically derived threshold)
        staple_cand = next((c for c in candidates if c[0] == "staple"), None)
        
        if staple_cand and staple_cand[2] <= 0.38:
            model = staple_cand[1]
            templates[item.food_name] = {
                "type": "staple",
                "serving_size": model.serving_size,
                "ingredients_text": model.ingredients_text,
                "instructions": model.instructions
            }
        else:
            # Check if raw fallback matches within strict distance 0.30
            raw_match_valid = best_distance <= 0.30 if best_type in ("icmr", "usda") else False
            
            if raw_match_valid:
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
            else:
                # If it's a cooked dish and we have no close match in database, force decomposition
                if item.is_cooked_dish:
                    templates[item.food_name] = {
                        "type": "unmatched_cooked",
                        "serving_size": "1 portion",
                        "ingredients_text": "Unknown cooked recipe (requires decomposition)",
                        "instructions": "Decompose this dish into raw ingredients."
                    }
                else:
                    # Fallback to raw model even if distance is high, since it cannot be decomposed
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


def scale_ingredients_with_rag(text: str, templates: dict, logged_items: List[LoggedItem]) -> RAGScaleResponse:
    context_lines = []
    for food_name, temp in templates.items():
        item_meta = next((item for item in logged_items if item.food_name == food_name), None)
        is_cooked = item_meta.is_cooked_dish if item_meta else False
        is_fallback = temp["type"] in ("raw", "unmatched_cooked")
        
        context_lines.append(
            f"Database template for '{food_name}':\n"
            f"  Portion baseline: {temp['serving_size']}\n"
            f"  Raw Ingredients: {temp['ingredients_text']}\n"
            f"  Cooking Steps: {temp['instructions']}\n"
            f"  Metadata: is_cooked_dish={is_cooked}, is_fallback_due_to_missing_template={is_fallback}, template_type={temp['type']}"
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
        "4. If a dish matches a staple template, scale all its raw ingredients proportionally.\n"
        "5. If a food item's template type is `unmatched_cooked`, it has no database recipe. You MUST decompose it into its standard, raw ingredients, and output those ingredients with their scaled uncooked weights in grams based on the user's portion.\n"
        "6. If a logged item is a raw commodity (like banana or almonds), simply output it with its estimated raw weight.\n"
        "7. Do NOT include water or salt in the raw ingredients list.\n"
        "8. PORTION WEIGHT PRIORS FOR RAW FALLBACKS:\n"
        "   - For raw fallback templates (type='raw') which use a '100g' baseline, use your general knowledge of standard food portions to estimate the weight consumed if the user logged an abstract or non-gram portion.\n"
        "     * E.g., if a standard order of fries is ~120-150g, and the user 'shared fries with three people' (divided by 4), scale the raw potato/fries ingredient weight to ~30-37g.\n"
        "     * E.g., if the user ate 'a bite' of a food, scale it down to ~10-15% of its standard serving weight.\n"
        "10. EXPLICIT WEIGHT ANCHORING RULE:\n"
        "    - If the user explicitly mentions the weight or quantity of a specific ingredient (e.g., 'made with 150g of whole wheat flour'), the final output weight for that specific ingredient MUST match the user's specified weight exactly. Do not split, halve, or divide it based on the number of portions.\n"
    )
    
    try:
        completion = llm_client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise nutrition scaling assistant. Ground all calculations on the provided database templates. "
                        "Scale raw ingredients and weights proportionally based on the user's portion. "
                        "Use general portion weight priors for raw fallbacks and generate standard new recipe templates in the new_candidates list for any new cooked dishes."
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


def generate_single_draft(dish_name: str) -> NewStapleCandidate:
    prompt = (
        f"Generate standard recipe and raw ingredient list for the following dish:\n"
        f"{dish_name}\n\n"
        "CRITICAL STAPLE & BASE RULES:\n\n"
        "1. THE GOLDEN BASELINE RULE:\n"
        "   - Make the recipe as standard, simple, and generic as possible so that it represents the GOLDEN BASELINE / GOLDEN AVERAGE of the dish.\n"
        "   - Avoid local variations, specialty recipes, or fancy restaurant-style versions.\n"
        "   - Focus exclusively on the core, staple ingredients that dictate the baseline caloric and macronutrient structure of the dish.\n\n"
        "2. AVERAGE KITCHEN INGREDIENTS:\n"
        "   - Use only raw, fundamental ingredients that you would find in an average home kitchen (e.g., raw meats, basic dairy like milk/cheese/cream/butter/sour cream, raw vegetables, standard grains, and common oils/fats).\n"
        "   - Do NOT include fancy, exotic, or garnish-only ingredients (e.g., saffron, cashews/almonds in basic curries, cream/butter in home-style curries, specific local spices, or food coloring) that are not essential to the staple food profile.\n\n"
        "3. LITERAL NAME MODIFIERS:\n"
        "   - If the dish name contains 'Plain' (e.g., 'Plain Dosa', 'Plain Naan', 'Plain Rice', 'Plain Paratha'), it must contain ONLY the absolute base grain/batter/meat. Do NOT include stuffing, gravies, potato masala, or heavy toppings.\n"
        "   - If the dish name contains a characterizing ingredient (e.g., 'Aloo Paratha' contains 'Aloo', 'Paneer Paratha' contains 'Paneer', 'Matar Paneer' contains 'Matar' and 'Paneer'), those exact raw ingredients MUST be listed in the ingredients list with non-zero weights.\n"
        "   - If the dish name contains 'Butter' or 'Ghee' (e.g., 'Butter Naan', 'Ghee Rice'), the raw ingredients list MUST contain 'Butter' or 'Ghee'. Otherwise, use standard neutral cooking oil.\n\n"
        "4. RAW INGREDIENT LISTING:\n"
        "   - Provide a comma-separated list of raw, uncooked ingredients and weights required to make exactly that 1 serving (e.g., '100g raw chicken breast, 50g raw basmati rice, 15g sunflower oil, 30g onion, 20g tomato, salt to taste').\n"
        "   - Do NOT list cooked states in the ingredients list.\n\n"
        "5. COOKING INSTRUCTIONS:\n"
        "   - Provide short, 3-4 step cooking instructions showing how these raw ingredients are combined to make the final dish.\n\n"
        "6. PORTION SIZE:\n"
        "   - Specify a realistic 1-person portion with approximate weight (e.g., '1 piece (30g)', '1 bowl (150g)', '1 plate (350g)').\n\n"
        "---\n\n"
        "SELF-CORRECTION PASS:\n"
        "Before outputting, review the list of generated ingredients for each dish:\n"
        "- Did 'Plain Dosa' get potato? If yes, remove it.\n"
        "- Did 'Butter Naan' get butter? If no, add it.\n"
        "- Did a basic home-style dish get premium cream or saffron? If yes, remove it to keep it as a basic staple.\n"
        "Only output the corrected, logically verified records in the requested schema."
    )
    completion = llm_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a precise, research-backed global nutrition and recipe database generator."},
            {"role": "user", "content": prompt}
        ],
        response_format=SingleRecipeResponse,
        temperature=0.3
    )
    return completion.choices[0].message.parsed.recipe

async def generate_jury_baseline(dish_name: str) -> NewStapleCandidate:
    # Run 3 drafts in parallel
    drafts = await asyncio.gather(
        asyncio.to_thread(generate_single_draft, dish_name),
        asyncio.to_thread(generate_single_draft, dish_name),
        asyncio.to_thread(generate_single_draft, dish_name)
    )
    
    # Judge call
    drafts_text = "\n\n".join([f"Draft {i+1}:\n{d.model_dump_json(indent=2)}" for i, d in enumerate(drafts)])
    
    judge_prompt = f"""We need the ultimate golden baseline recipe for '{dish_name}'.
    
Here are 3 independent drafts generated by our baseline recipe AI:

{drafts_text}

INSTRUCTIONS:
1. Analyze the 3 drafts. Identify the most statistically sound, common-sense golden baseline values.
2. If one draft hallucinates a weird ingredient (e.g., cashews in basic dal), ignore it.
3. Average or pick the most credible ingredient weights and portion sizes.
4. Output the final, synthesized golden baseline recipe.
"""
    
    def run_judge():
        completion = llm_client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are the head judge of a nutrition AI jury. Synthesize the drafts into one perfect golden baseline recipe."},
                {"role": "user", "content": judge_prompt}
            ],
            response_format=SingleRecipeResponse,
            temperature=0.0
        )
        return completion.choices[0].message.parsed.recipe
        
    return await asyncio.to_thread(run_judge)

async def run_jury_and_update_review(dish_name: str, review_id: int):
    try:
        final_recipe = await generate_jury_baseline(dish_name)
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


# --- Endpoints ---
@app.post("/api/v1/meals/parse", response_model=Meal)
def parse_meal(request: UserInput, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
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
    scaled_res = scale_ingredients_with_rag(request.text, templates, logged_items)
    
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
        
        if best_db_dist > 0.75:
            match_name = best_db_model.food_name if best_db_type == 'icmr' else best_db_model.description
            print(f"WARNING: Skipping macro calculation for '{ing.raw_ingredient_name}'. Best match was '{match_name}' with distance {best_db_dist:.3f}")
            continue
        
        weight_factor = ing.weight_g / 100.0
        total_calories += best_db_model.calories * weight_factor
        total_protein += best_db_model.protein * weight_factor
        total_carbs += best_db_model.carbs * weight_factor
        total_fat += best_db_model.fat * weight_factor
        
    # 5. Persist meal and review candidates
    db_meal = Meal(
        raw_text=request.text,
        meal_type=scaled_res.meal_type,
        calories=round(total_calories, 2),
        protein=round(total_protein, 2),
        carbs=round(total_carbs, 2),
        fat=round(total_fat, 2)
    )
    db.add(db_meal)
    
    # Save review candidates: only for cooked dishes that fell back to raw templates
    # Gate in Python: item must be a cooked dish (is_cooked_dish=True) AND template type must be 'raw'
    if scaled_res.new_candidates:
        cooked_fallback_names = {
            item.food_name
            for item in logged_items
            if item.is_cooked_dish and templates.get(item.food_name, {}).get("type") in ("raw", "unmatched_cooked")
        }
        for cand in scaled_res.new_candidates:
            if cand.name not in cooked_fallback_names:
                # Cross-check by name substring match as LLM may slightly rename
                is_relevant = any(fn.lower() in cand.name.lower() or cand.name.lower() in fn.lower() for fn in cooked_fallback_names)
                if not is_relevant:
                    continue
            exists_staples = db.exec(select(Staple).where(Staple.name == cand.name)).first()
            exists_review = db.exec(select(StaplesReview).where(StaplesReview.name == cand.name)).first()
            if not exists_staples and not exists_review:
                review_row = StaplesReview(
                    name=cand.name,
                    serving_size=cand.serving_size,
                    ingredients_text=cand.ingredients_text,
                    instructions=cand.instructions
                )
                db.add(review_row)
                db.flush()
                background_tasks.add_task(run_jury_and_update_review, cand.name, review_row.id)
                
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

