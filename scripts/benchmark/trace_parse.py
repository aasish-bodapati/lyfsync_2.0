import sys
import os
import json

# Setup paths so we can import from backend
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "backend", ".env"))

from sqlmodel import Session, create_engine, select
from main import (
    DATABASE_URL, get_embedding, extract_dishes, retrieve_grounding_templates,
    scale_ingredients_with_rag, ICMRRaw, USDARaw
)

def trace_parse(text: str):
    engine = create_engine(DATABASE_URL)
    with Session(engine) as db:
        print(f"\n{'='*80}")
        print(f"INPUT: \"{text}\"")
        print(f"{'='*80}\n")
        
        # 1. Extraction
        print("↓ [Dish Extraction]")
        try:
            logged_items = extract_dishes(text)
            if not logged_items:
                print("  (No items extracted)")
                return
            for item in logged_items:
                print(f"  - {item.food_name} | portion: {item.logged_portion} | is_cooked: {item.is_cooked_dish}")
        except Exception as e:
            print(f"  FAILED: {e}")
            return
            
        # 2. Template Retrieval
        print("\n↓ [Template Retrieval]")
        templates = retrieve_grounding_templates(logged_items, db)
        for item in logged_items:
            temp = templates.get(item.food_name)
            if temp:
                print(f"  - {item.food_name}: Matched type='{temp['type']}' | base_serving='{temp['serving_size']}'")
            else:
                print(f"  - {item.food_name}: No template found")
                
        # 3. Scaling
        print("\n↓ [Scaling Decision]")
        try:
            scaled_res = scale_ingredients_with_rag(text, templates, logged_items, db)
            print(f"  Meal Type: {scaled_res.meal_type}")
            for ing in scaled_res.ingredients:
                print(f"  - {ing.raw_ingredient_name}: {ing.weight_g:.1f}g")
        except Exception as e:
            print(f"  FAILED: {e}")
            return
            
        # 4. DB Macro Lookup
        print("\n↓ [Nutrition Lookup]")
        total_cal = 0
        for ing in scaled_res.ingredients:
            ing_emb = get_embedding(ing.raw_ingredient_name)
            
            icmr_dist = ICMRRaw.embedding.cosine_distance(ing_emb)
            best_icmr = db.exec(select(ICMRRaw, icmr_dist).order_by(icmr_dist).limit(1)).first()
            
            usda_dist = USDARaw.embedding.cosine_distance(ing_emb)
            best_usda = db.exec(select(USDARaw, usda_dist).order_by(usda_dist).limit(1)).first()
            
            candidates = []
            if best_icmr: candidates.append(("ICMR", best_icmr[0], best_icmr[1]))
            if best_usda: candidates.append(("USDA", best_usda[0], best_usda[1]))
            
            if not candidates:
                print(f"  - {ing.raw_ingredient_name}: NO MATCH")
                continue
                
            candidates.sort(key=lambda x: x[2])
            best_db_type, best_db_model, best_db_dist = candidates[0]
            
            match_name = best_db_model.food_name if best_db_type == 'ICMR' else best_db_model.description
            
            if best_db_dist > 0.75:
                print(f"  - {ing.raw_ingredient_name} ({ing.weight_g}g) -> REJECTED (dist {best_db_dist:.3f}): {match_name}")
                continue
                
            factor = ing.weight_g / 100.0
            cal = best_db_model.calories * factor
            total_cal += cal
            print(f"  - {ing.raw_ingredient_name} ({ing.weight_g}g) -> matched [{best_db_type}] '{match_name}' (dist: {best_db_dist:.3f})")
            print(f"      -> {best_db_model.calories} kcal/100g * {factor:.2f} = {cal:.1f} kcal")
            
        print("\n↓ [Final Macros]")
        print(f"  Total Calories: {total_cal:.1f} kcal")
        print(f"{'='*80}\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        trace_parse(sys.argv[1])
    else:
        print("Usage: python trace_parse.py \"your meal text\"")
