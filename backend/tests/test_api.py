import os
import sys
from dotenv import load_dotenv
from fastapi.testclient import TestClient
import pytest
from sqlmodel import create_engine, SQLModel, Session





dotenv_path= os.path.dirname(os.path.dirname(__file__))
sys.path.append(dotenv_path)


from main import app, get_db, Meal, ParsedMeal, FoodItem


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


def test_parse_meal(client, monkeypatch):
    def mock_parse(text):
        return ParsedMeal(
            meal_type="breakfast",
            foods=[
                FoodItem(food_name="egg", weight_grams=100.0, calories=140.0, protein=12.0, carbohydrates=1.0, fats=10.0)
            ]
        )

    import main
    monkeypatch.setattr(main, "parse_nutrition_from_text", mock_parse)

    def mock_find_closest_food(query, db, threshold=0.80):
        return None
    monkeypatch.setattr(main, "find_closest_food", mock_find_closest_food)

    response = client.post("/api/v1/meals/parse", json={"text": "I ate 2 eggs and a banana for breakfast"})
    
    assert response.status_code == 200
    data = response.json()

    assert data["meal_type"] == "breakfast"
    assert data["total_calories"] > 0
    assert data["total_protein"] > 0
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "egg"
    

def test_list_meals(client, session):
    test_meal = Meal(raw_text="2 eggs", meal_type="breakfast", calories=140.0, protein=12.0, carbs=1.0, fat=10.0)
    session.add(test_meal)
    session.commit()



    response = client.get("/api/v1/meals")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0

    
 
