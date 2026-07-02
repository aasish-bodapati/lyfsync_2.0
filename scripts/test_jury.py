import os
import sys
import json
import time

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))
from fastapi.testclient import TestClient
from main import app, engine, StaplesReview
from sqlmodel import Session, select, delete

client = TestClient(app)

def test_jury():
    dish_name = "Cheesecake"
    test_query = f"I ate a slice of {dish_name}."
    
    print(f"🚀 Running Jury Background Task Test")
    
    # Clean the review queue
    with Session(engine) as session:
        session.exec(delete(StaplesReview).where(StaplesReview.name.ilike(f"%{dish_name}%")))
        session.commit()

    print(f"Sending API request: '{test_query}'")
    start_time = time.time()
    
    # The TestClient will block until the background tasks finish
    response = client.post("/api/v1/meals/parse", json={"text": test_query})
    
    if response.status_code != 200:
        print(f"Error: {response.text}")
        return
        
    duration = time.time() - start_time
    print(f"✅ Request completed in {duration:.2f} seconds.")
    
    print("\n--- Inspecting StaplesReview Queue ---")
    with Session(engine) as session:
        all_reviews = session.exec(select(StaplesReview)).all()
        for r in all_reviews:
            print(f"[{r.id}] {r.name}: {r.serving_size}")
            if "tiramisu" in r.name.lower():
                print(f"   Ingredients: {r.ingredients_text}")

if __name__ == "__main__":
    test_jury()
