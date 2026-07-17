import os
import sys
import time
import sqlite3
import sqlite_vec
from sqlmodel import Session, create_engine, select, text

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BACKEND_DIR)

from embeddings import get_embedding, FoodNutrition

def load_vec_extension(dbapi_conn, connection_record):
    dbapi_conn.enable_load_extension(True)
    sqlite_vec.load(dbapi_conn)
    dbapi_conn.enable_load_extension(False)

def run_sqlite_vec_benchmark():
    db_path = os.path.join(BACKEND_DIR, "local_db.db")
    engine = create_engine(f"sqlite:///{db_path}")
    
    # Register the sqlite-vec extension loader event
    from sqlalchemy import event
    event.listen(engine, "connect", load_vec_extension)
    
    query = "apple"
    print(f"Generating query embedding for '{query}'...")
    query_vector = get_embedding(query)
    
    # Serialize query vector to blob or JSON string
    # sqlite-vec accepts JSON string directly
    import json
    query_vector_json = json.dumps(query_vector)
    
    print("\n=== BENCHMARKING SQLITE-VEC (469 records) ===")
    
    with Session(engine) as db:
        # Let's do it with a clean raw SQL query
        durations = []
        for i in range(5):
            start = time.perf_counter()
            row = db.execute(
                text(
                    "SELECT fdc_id, description, calories, protein, carbs, fat, "
                    "vec_distance_cosine(vector_embedding, :query_vec) as distance "
                    "FROM food_nutrition "
                    "WHERE vector_embedding IS NOT NULL "
                    "ORDER BY distance "
                    "LIMIT 1"
                ),
                {"query_vec": query_vector_json}
            ).fetchone()
            duration = time.perf_counter() - start
            durations.append(duration)
            print(f"sqlite-vec Run {i+1}/5: {duration:.4f} seconds")
            
        print(f"\nAverage sqlite-vec DB lookup time: {sum(durations)/len(durations):.4f} seconds")
        print(f"Best match found: {row[1]} with distance: {row[6]:.4f} (Similarity: {1 - row[6]:.4f})")

# FoodNutrition class is imported from embeddings

if __name__ == "__main__":
    run_sqlite_vec_benchmark()
