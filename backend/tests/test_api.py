import os
import sys
from dotenv import load_dotenv
from fastapi.testclient import TestClient
import pytest
from sqlmodel import create_engine, SQLModel, Session





dotenv_path= os.path.dirname(os.path.dirname(__file__))
sys.path.append(dotenv_path)


from main import app, get_db, MealTable, ParsedMeal, ExtractionItem


load_dotenv(os.path.join(dotenv_path, ".env"))




@pytest.fixture(name= "session")
def session_fixture():
    test_engine= create_engine("sqlite:///./test_db.db", connect_args= {"check_same_thread": False})
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        yield session
    SQLModel.metadata.drop_all(test_engine)
    if os.path.exists("./test_db.db"):
        os.remove("./test_db.db")



@pytest.fixture(name="client")
def client_fixture(session):
    def get_db_override():
        yield session
    app.dependency_overrides[get_db] = get_db_override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "Server is running successfully", "status_code": 200}


import openai
import main

def test_parse_meal_unresolved_audit_flags(client, monkeypatch):
    """P0: Verify unresolved foods return correct fallback flags and 0.0 macros."""
    def mock_parse(text):
        return ParsedMeal(
            meal_type="breakfast",
            items=[ExtractionItem(name="dragonfruit", quantity=1.0, unit="piece", estimated_weight_grams=100.0, raw_or_cooked="raw")]
        )
    monkeypatch.setattr(main, "parse_nutrition_from_text", mock_parse)

    def mock_find_closest_food(query, db, client_instance, threshold=0.60):
        return None
    monkeypatch.setattr(main, "find_closest_food", mock_find_closest_food)

    response = client.post("/api/v1/meals/parse", json={"text": "I ate a dragonfruit"})
    assert response.status_code == 200
    data = response.json()

    assert data["total_calories"] == 0.0
    item = data["items"][0]
    assert item["source"] == "unresolved"
    assert item["needs_clarification"] is True
    assert item["confidence"] is None
    assert item["calories"] == 0.0

def test_parse_meal_resolved_db_match(client, monkeypatch):
    """P0: Verify confident matches scale macros and return db_match_high."""
    def mock_parse(text):
        return ParsedMeal(
            meal_type="lunch",
            items=[ExtractionItem(name="rice", quantity=200.0, unit="grams", estimated_weight_grams=200.0, raw_or_cooked="cooked", needs_clarification=False)]
        )
    monkeypatch.setattr(main, "parse_nutrition_from_text", mock_parse)

    def mock_find_closest_food(query, db, client_instance, threshold=0.60):
        # 100g of rice has 130 calories
        return {"calories": 130.0, "protein": 2.7, "carbs": 28.0, "fat": 0.3, "similarity_score": 0.85}
    monkeypatch.setattr(main, "find_closest_food", mock_find_closest_food)

    response = client.post("/api/v1/meals/parse", json={"text": "200g of rice"})
    assert response.status_code == 200
    data = response.json()

    item = data["items"][0]
    assert item["source"] == "db_match_high"
    assert item["needs_clarification"] is False
    assert item["confidence"] == 0.85
    assert item["calories"] == 260.0  # 130 * (200/100)

def test_parse_meal_low_confidence_match(client, monkeypatch):
    """P2: Verify matches between 0.60 and 0.79 return db_match_low."""
    def mock_parse(text):
        return ParsedMeal(
            meal_type="snack",
            items=[ExtractionItem(name="weird snack", quantity=1.0, unit="piece", estimated_weight_grams=100.0, raw_or_cooked="raw")]
        )
    monkeypatch.setattr(main, "parse_nutrition_from_text", mock_parse)

    def mock_find_closest_food(query, db, client_instance, threshold=0.60):
        return {"calories": 100.0, "protein": 1.0, "carbs": 10.0, "fat": 5.0, "similarity_score": 0.65}
    monkeypatch.setattr(main, "find_closest_food", mock_find_closest_food)

    response = client.post("/api/v1/meals/parse", json={"text": "weird snack"})
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["source"] == "db_match_low"
    assert item["confidence"] == 0.65

def test_parse_meal_ambiguity_propagation(client, monkeypatch):
    """P1: Verify extraction flags survive into the API response."""
    def mock_parse(text):
        return ParsedMeal(
            meal_type="dinner",
            items=[ExtractionItem(
                name="dal", 
                quantity=1.0,
                unit="bowl",
                estimated_weight_grams=150.0, 
                raw_or_cooked="cooked",
                assumption_made="Assumed 1 bowl is 150g",
                ambiguity_reason="Vague quantity",
                needs_clarification=True
            )]
        )
    monkeypatch.setattr(main, "parse_nutrition_from_text", mock_parse)

    def mock_find_closest_food(*args, **kwargs):
        return {"calories": 100.0, "protein": 5.0, "carbs": 15.0, "fat": 2.0, "similarity_score": 0.90}
    monkeypatch.setattr(main, "find_closest_food", mock_find_closest_food)

    response = client.post("/api/v1/meals/parse", json={"text": "some dal"})
    assert response.status_code == 200
    item = response.json()["items"][0]
    
    assert item["assumption_made"] == "Assumed 1 bowl is 150g"
    assert item["ambiguity_reason"] == "Vague quantity"
    assert item["needs_clarification"] is True

def test_parse_meal_failure_handling(client, monkeypatch):
    """P1: Verify ValueError -> 400, and APIError -> 502."""
    def mock_value_error(text):
        raise ValueError("Invalid format")
    monkeypatch.setattr(main, "parse_nutrition_from_text", mock_value_error)
    
    response = client.post("/api/v1/meals/parse", json={"text": "gibberish"})
    assert response.status_code == 400

    def mock_api_error(text):
        raise openai.APIError("OpenAI is down", request=None, body=None)
    monkeypatch.setattr(main, "parse_nutrition_from_text", mock_api_error)
    
    response = client.post("/api/v1/meals/parse", json={"text": "valid but API down"})
    assert response.status_code == 502

def test_parse_meal_dish_ingredient_dedup(client, monkeypatch):
    """Bonus: Verify mock extraction logic returns ingredients, not overarching dish."""
    def mock_parse(text):
        # Emulate the prompt extracting only ingredients and ignoring the dish name
        return ParsedMeal(
            meal_type="dinner",
            items=[
                ExtractionItem(name="chicken", quantity=150.0, unit="grams", estimated_weight_grams=150.0, raw_or_cooked="raw"),
                ExtractionItem(name="rice", quantity=200.0, unit="grams", estimated_weight_grams=200.0, raw_or_cooked="raw")
            ]
        )
    monkeypatch.setattr(main, "parse_nutrition_from_text", mock_parse)

    def mock_find_closest_food(*args, **kwargs):
        return {"calories": 100.0, "protein": 5.0, "carbs": 15.0, "fat": 2.0, "similarity_score": 0.90}
    monkeypatch.setattr(main, "find_closest_food", mock_find_closest_food)

    response = client.post("/api/v1/meals/parse", json={"text": "I had chicken biryani made with 200g rice and 150g chicken"})
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["items"]) == 2
    item_names = [item["name"] for item in data["items"]]
    assert "chicken" in item_names
    assert "rice" in item_names
    assert "biryani" not in item_names
    

def test_list_meals(client, session):
    test_meal = MealTable(raw_text="2 eggs", meal_type="breakfast", calories=140.0, protein=12.0, carbs=1.0, fat=10.0)
    session.add(test_meal)
    session.commit()



    response = client.get("/api/v1/meals")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0

    
 
