import os
import sys
import time
import json
from sqlmodel import Session, create_engine, select

# Add backend directory to path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BACKEND_DIR)

from embeddings import get_embedding, cosine_similarity, FoodNutrition

def run_detailed_benchmark():
    db_path = os.path.join(BACKEND_DIR, "local_db.db")
    engine = create_engine(f"sqlite:///{db_path}")
    
    with Session(engine) as db:
        # 1. Fetch data
        total_foods = db.exec(select(FoodNutrition)).all()
        total_count = len(total_foods)
        embedded_foods = [f for f in total_foods if f.vector_embedding is not None]
        embedded_count = len(embedded_foods)
        
        print("=== DATABASE STATUS ===")
        print(f"Total foods in database: {total_count}")
        print(f"Foods with vector embeddings: {embedded_count}")
        
        if embedded_count == 0:
            print("\nWARNING: No vector embeddings found in the database.")
            return

        # Prepare parsed vectors once to measure raw loop time vs json load time
        parsed_candidates = []
        for food in embedded_foods:
            try:
                vec = json.loads(food.vector_embedding)
                parsed_candidates.append(vec)
            except Exception:
                pass

        # 2. Benchmark OpenAI API network call
        query = "apple"
        print(f"\n=== BENCHMARKING OpenAI API (Network) ===")
        network_times = []
        query_vector = None
        for i in range(3):
            start = time.perf_counter()
            query_vector = get_embedding(query)
            duration = time.perf_counter() - start
            network_times.append(duration)
            print(f"OpenAI Call {i+1}/3: {duration:.4f} seconds")
        avg_network = sum(network_times) / len(network_times)
        print(f"Average OpenAI API network time: {avg_network:.4f} seconds")

        if query_vector is None:
            return

        # 3. Benchmark Database Scan - Python JSON parsing + Cosine Similarity
        print(f"\n=== BENCHMARKING DB scan (469 records in Python) ===")
        db_scan_times = []
        for i in range(5):
            start = time.perf_counter()
            
            best_match = None
            best_score = -1.0
            for food in embedded_foods:
                try:
                    food_vector = json.loads(food.vector_embedding)  # JSON parsing in loop
                except Exception:
                    continue
                score = cosine_similarity(query_vector, food_vector)
                if score > best_score:
                    best_score = score
                    best_match = food
                    
            duration = time.perf_counter() - start
            db_scan_times.append(duration)
            print(f"DB Scan Run {i+1}/5 (with JSON loads): {duration:.4f} seconds")
        avg_db_scan = sum(db_scan_times) / len(db_scan_times)
        print(f"Average DB scan time (with JSON loads): {avg_db_scan:.4f} seconds")

        # 4. Benchmark Database Scan - Pre-parsed vectors (Cosine Similarity only)
        print(f"\n=== BENCHMARKING Pure Math (Cosine Similarity only) ===")
        math_times = []
        for i in range(5):
            start = time.perf_counter()
            
            best_match_idx = -1
            best_score = -1.0
            for idx, food_vector in enumerate(parsed_candidates):
                score = cosine_similarity(query_vector, food_vector)
                if score > best_score:
                    best_score = score
                    best_match_idx = idx
                    
            duration = time.perf_counter() - start
            math_times.append(duration)
            print(f"Pure Similarity Run {i+1}/5: {duration:.4f} seconds")
        avg_math = sum(math_times) / len(math_times)
        print(f"Average similarity loop time: {avg_math:.4f} seconds")

if __name__ == "__main__":
    run_detailed_benchmark()
