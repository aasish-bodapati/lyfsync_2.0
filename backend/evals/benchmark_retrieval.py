import os
import json
import logging
from sqlmodel import Session
from openai import OpenAI
from dotenv import load_dotenv

# Setup paths and imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from main import get_db
from embeddings import find_closest_food, find_closest_recipe

load_dotenv()
client = OpenAI()

BENCHMARK_DATA = [
    # Recipes
    {"query": "chicken biryani", "type": "recipe", "expected_match": "Chicken Biryani"},
    {"query": "palak paneer", "type": "recipe", "expected_match": "Palak Paneer"},
    {"query": "masala dosa", "type": "recipe", "expected_match": "Masala Dosa"},
    {"query": "dal makhani", "type": "recipe", "expected_match": "Dal Makhani"},
    {"query": "butter chicken", "type": "recipe", "expected_match": "Butter Chicken"},
    {"query": "paneer tikka", "type": "recipe", "expected_match": "Paneer Tikka"},
    {"query": "chole bhature", "type": "recipe", "expected_match": "Chole Bhature"},
    {"query": "aloo paratha", "type": "recipe", "expected_match": "Aloo Paratha"},
    
    # Foods
    {"query": "raw chicken breast", "type": "food", "expected_match": "Chicken breast"},
    {"query": "paneer", "type": "food", "expected_match": "Cheese"}, # Alias maps paneer->cheese for USDA DB
    {"query": "milk", "type": "food", "expected_match": "Milk"},
    {"query": "egg", "type": "food", "expected_match": "Egg"},
    {"query": "white rice", "type": "food", "expected_match": "Rice"},
    {"query": "apples", "type": "food", "expected_match": "Apple"},
    {"query": "curd", "type": "food", "expected_match": "Yogurt"}, # Alias maps curd->yogurt
]

def run_retrieval_benchmark():
    top1_correct = 0
    total = len(BENCHMARK_DATA)
    
    db = next(get_db())
    try:
        for idx, item in enumerate(BENCHMARK_DATA):
            query = item["query"]
            target = item["expected_match"].lower()
            q_type = item["type"]
            
            print(f"[{idx+1}/{total}] Query: '{query}' -> Expected: '{target}' ({q_type})")
            
            # Since find_closest_x returns the SINGLE best match, we can only evaluate Top-1 natively right now.
            # (To do top-5 we would need to return the list from find_closest_x).
            if q_type == "recipe":
                match = find_closest_recipe(query, db, client, threshold=0.0)
            else:
                match = find_closest_food(query, db, client, threshold=0.0)
                
            if match:
                matched_name = match["description"].lower() if q_type == "food" else match["name"].lower()
                if target in matched_name or matched_name in target:
                    top1_correct += 1
                    print(f"  [PASS] Top-1 Matched: {matched_name}")
                else:
                    print(f"  [FAIL] Expected '{target}', Got '{matched_name}'")
            else:
                print(f"  [FAIL] No match returned at all.")
                
    finally:
        db.close()
        
    print("\n" + "="*40)
    print("RETRIEVAL BENCHMARK RESULTS")
    print("="*40)
    print(f"Total Queries: {total}")
    print(f"Top-1 Accuracy: {top1_correct / total * 100:.1f}% ({top1_correct}/{total})")

if __name__ == "__main__":
    # Suppress verbose HTTP logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    run_retrieval_benchmark()
