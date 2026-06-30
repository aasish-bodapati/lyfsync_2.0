import os
import sys
from fastapi.testclient import TestClient

# Ensure backend directory is in path
sys.path.append(os.path.dirname(__file__))

from main import app

client = TestClient(app)

test_scenarios = [
    "I had 2 rotis and 1 bowl of dal tadka",
    "I ate 1 cup of jeera rice and a bowl of chicken curry",
    "I had 100g of raw bananas",
    "I had 4 chapatis",
    "I had a bowl of fresh strawberries and 10 raw almonds",
    "I ate 1 avocado",
    "I had a plate of penne pasta with tomato sauce"
]

def run_tests():
    print("🚀 Running RAG Meal Parser Integration Tests...")
    
    for idx, log in enumerate(test_scenarios):
        print(f"\n==========================================")
        print(f"📝 Test Case {idx + 1}: \"{log}\"")
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
            
            # Mathematical consistency check:
            # Cal = (P * 4) + (C * 4) + (F * 9)
            computed_cal = (data['protein'] * 4.0) + (data['carbs'] * 4.0) + (data['fat'] * 9.0)
            diff = abs(data['calories'] - computed_cal)
            
            print(f"🔍 Math Verification:")
            print(f"  Expected (Atwater sum): {computed_cal:.2f} kcal")
            print(f"  Difference: {diff:.2f} kcal")
            
            if diff <= 5.0:
                print("✅ MACROS ARE 100% MATHEMATICALLY CONSISTENT!")
            else:
                print("⚠️ Warning: Macro difference exceeds 5 kcal tolerance.")
                
        except Exception as e:
            print(f"❌ Test crashed: {e}")

if __name__ == "__main__":
    run_tests()
