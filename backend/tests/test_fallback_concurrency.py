import pytest
from datetime import datetime, timezone, timedelta
import threading
from sqlmodel import Session, create_engine
import sys
import os
from dotenv import load_dotenv
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from fallback import generate_recipe_fallback
from models import GeneratedRecipeCandidate

# Configure Postgres engine
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path)

db_url = os.environ.get("DATABASE_URL")
if not db_url or "postgres" not in db_url:
    raise ValueError("DATABASE_URL is not set to a Postgres connection")

# Engine for the test
engine = create_engine(db_url, pool_size=5, max_overflow=10)

def test_atomic_lease_blocks_concurrent_threads(monkeypatch):
    """
    Test that the true atomic upsert in fallback.py blocks a second thread
    from acquiring a lease on the same dish using a live PostgreSQL database.
    """
    # Clean up any previous test state
    test_dish_name = "postgres race condition dish"
    with Session(engine) as session:
        session.execute(text("DELETE FROM recipe_generation_logs WHERE normalized_dish_name = :name"), {"name": test_dish_name})
        session.execute(text("DELETE FROM generated_recipe_candidates WHERE normalized_dish_name = :name"), {"name": test_dish_name})
        session.commit()

    class MockClient:
        class beta:
            class chat:
                class completions:
                    @staticmethod
                    def parse(*args, **kwargs):
                        # Block to simulate a slow generation API call
                        import time
                        time.sleep(1.5)
                        raise ValueError("Should not matter")
    
    mock_client = MockClient()

    results = []
    
    # We use independent sessions for each thread to simulate independent requests to Postgres
    def worker():
        with Session(engine) as session:
            res = generate_recipe_fallback(test_dish_name, session, mock_client)
            results.append(res)
            
    # Launch two threads simulating concurrent API requests
    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    
    assert len(results) == 2
    
    statuses = [r["status"] for r in results]
    assert statuses == ["failed", "failed"]
    
    reasons = [r["unresolved_ingredients"][0] for r in results]
    
    assert "Should not matter" in reasons
    assert "Concurrent generation in progress" in reasons

    # Clean up again
    with Session(engine) as session:
        session.execute(text("DELETE FROM recipe_generation_logs WHERE normalized_dish_name = :name"), {"name": test_dish_name})
        session.execute(text("DELETE FROM generated_recipe_candidates WHERE normalized_dish_name = :name"), {"name": test_dish_name})
        session.commit()
