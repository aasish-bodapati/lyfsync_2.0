import os, sys
# Ensure backend directory is in the path
sys.path.append('backend')
from dotenv import load_dotenv
load_dotenv('backend/.env', override=True)

from fastapi.testclient import TestClient
from main import app

# Create a simulated test client for our FastAPI app
client = TestClient(app)

def test_health_endpoint():
    """Verify that the health check endpoint returns 200 OK and correct JSON."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "Server is running successfully",
        "status_code": 200
    }

def test_parse_meal_endpoint():
    """Verify that the parse endpoint queries OpenAI, sums macros, and returns the meal."""
    # We send a test request
    response = client.post("/api/v1/meals/parse", json={"text": "I ate 2 eggs for breakfast"})
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify the structure and values returned from the database
    assert data["id"] is not None
    assert data["raw_text"] == "I ate 2 eggs for breakfast"
    assert data["meal_type"] == "breakfast"
    assert data["calories"] > 0
    assert data["protein"] > 0
    assert data["carbs"] >= 0
    assert data["fat"] > 0
