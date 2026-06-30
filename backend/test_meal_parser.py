import os
import sys
from fastapi.testclient import TestClient
from sqlmodel import Session, select, delete

# Ensure backend directory is in path
sys.path.append(os.path.dirname(__file__))

from main import app, StaplesReview, engine

client = TestClient(app)

benchmark_scenarios = [
    # 1. NLP Hard & Very Hard
    "Lunch was leftover butter chicken from yesterday, maybe around a bowl and a half, with some rice.",
    "I picked around the fries, ate most of the burger but left the top bun.",
    
    # 2. Cooking Reasoning
    "Chicken thighs, air fried.",
    "Cooked in a tablespoon of butter but I left most of it in the pan.",
    
    # 3. Cultural Foods
    "Two idlis with sambar.",
    "Poha with peanuts.",
    
    # 4. Edge Cases
    "A bite of cheesecake.",
    "Shared fries with three people."
]

def run_tests():
    print("🧹 Clearing staples_review table for benchmark run...")
    with Session(engine) as session:
        session.exec(delete(StaplesReview))
        session.commit()
        
    print("🚀 Running RAG Meal Parser Benchmark Tests...")
    
    for idx, log in enumerate(benchmark_scenarios):
        print(f"\n==========================================")
        print(f"📝 Benchmark Case {idx + 1}: \"{log}\"")
        print(f"==========================================")
        
        try:
            response = client.post("/api/v1/meals/parse", json={"text": log})
            
            if response.status_code != 200:
                print(f"❌ API Error: Status {response.status_code}")
                print(response.json())
                continue
                
            data = response.json()
            print(f"🟢 Meal Type: {data['meal_type'].upper()}")
            print(f"📊 Calculated Macros:")
            print(f"  Calories: {data['calories']} kcal")
            print(f"  Protein:  {data['protein']}g")
            print(f"  Carbs:    {data['carbs']}g")
            print(f"  Fat:      {data['fat']}g")
            
            computed_cal = (data['protein'] * 4.0) + (data['carbs'] * 4.0) + (data['fat'] * 9.0)
            diff = abs(data['calories'] - computed_cal)
            
            print(f"🔍 Math Verification:")
            print(f"  Expected (Atwater sum): {computed_cal:.2f} kcal")
            print(f"  Difference: {diff:.2f} kcal")
            
        except Exception as e:
            print(f"❌ Test crashed: {e}")

    print("\n==========================================")
    print("📋 Checking staples_review database table...")
    print("==========================================")
    with Session(engine) as session:
        items = session.exec(select(StaplesReview)).all()
        print(f"Found {len(items)} items in review queue:")
        for item in items:
            print(f"\n📌 Candidate: \"{item.name}\"")
            print(f"  Serving Size: {item.serving_size}")
            print(f"  Ingredients:  {item.ingredients_text}")
            print(f"  Instructions: {item.instructions}")

if __name__ == "__main__":
    run_tests()
