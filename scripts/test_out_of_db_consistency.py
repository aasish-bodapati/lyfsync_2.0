import os
import sys
import json
from collections import defaultdict

# Ensure backend directory is in path for import resolution
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi.testclient import TestClient
from main import app, engine, StaplesReview
from sqlmodel import Session, select, delete

client = TestClient(app)

def test_out_of_db_consistency():
    # Pick a dish we know is NOT in the staples or raw databases
    test_query = "I ate a slice of Tiramisu."
    num_runs = 5
    
    print(f"🚀 Running Sanity Check: LLM Consistency for Out-of-DB Dish")
    print(f"Query: '{test_query}'")
    print(f"Runs: {num_runs}\n")
    
    # Clean the review queue to ensure a fresh test
    with Session(engine) as session:
        session.exec(delete(StaplesReview).where(StaplesReview.name.ilike("%Tiramisu%")))
        session.commit()

    results = []

    for i in range(num_runs):
        print(f"--- Run {i+1} ---")
        response = client.post("/api/v1/meals/parse", json={"text": test_query})
        
        if response.status_code != 200:
            print(f"Error: {response.text}")
            continue
            
        data = response.json()
        
        macros = {
            "calories": data["calories"],
            "protein": data["protein"],
            "carbs": data["carbs"],
            "fat": data["fat"]
        }
        
        # Fetch the generated recipe from StaplesReview table
        with Session(engine) as session:
            review_item = session.exec(select(StaplesReview).where(StaplesReview.name.ilike("%Tiramisu%"))).first()
            if review_item:
                ingredients = review_item.ingredients_text
                # Delete it so the next run generates it freshly
                session.delete(review_item)
                session.commit()
            else:
                ingredients = "No recipe generated in staples_review"
        
        print(f"Macros: {macros}")
        print(f"Ingredients: {ingredients}\n")
        
        results.append({
            "macros": macros,
            "ingredients": ingredients
        })
        
    # Analyze Consistency
    first_run_macros = results[0]["macros"]
    first_run_ingredients = results[0]["ingredients"]
    
    is_consistent = True
    macro_variance = False
    ingredient_variance = False
    
    for i, res in enumerate(results[1:], start=2):
        if res["macros"] != first_run_macros:
            macro_variance = True
            is_consistent = False
            print(f"❌ Macro mismatch on run {i}!")
        if res["ingredients"] != first_run_ingredients:
            ingredient_variance = True
            is_consistent = False
            print(f"❌ Ingredient mismatch on run {i}!")

    print("==========================================")
    if is_consistent:
        print("✅ 100% CONSISTENT: The LLM hallucinated the exact same recipe and weights across all runs.")
    else:
        print("⚠️ INCONSISTENT: The LLM output drifted across runs.")
        if macro_variance:
            print("- Macros drifted")
        if ingredient_variance:
            print("- Ingredients drifted")
            
if __name__ == "__main__":
    test_out_of_db_consistency()
