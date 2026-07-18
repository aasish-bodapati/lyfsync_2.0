import pytest
from datetime import datetime, timezone
import json
from sqlmodel import Session, SQLModel, create_engine, select
import openai
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fallback import generate_recipe_fallback, GeneratedRecipeStructure, GeneratedIngredient
from models import FoodNutrition, GeneratedRecipeCandidate, RecipeGenerationLog
from embeddings import normalize_recipe_name

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="mock_client")
def mock_client_fixture(monkeypatch):
    class MockMessage:
        def __init__(self, parsed):
            self.parsed = parsed
            
    class MockChoice:
        def __init__(self, parsed):
            self.message = MockMessage(parsed)
            
    class MockCompletions:
        def parse(self, *args, **kwargs):
            parsed = GeneratedRecipeStructure(
                dish_name="unknown dish",
                typical_serving_grams=300.0,
                ingredients=[
                    GeneratedIngredient(name="chicken", weight_grams=200.0),
                    GeneratedIngredient(name="rice", weight_grams=100.0)
                ],
                assumptions="Mocked assumptions"
            )
            return type('obj', (object,), {'choices': [MockChoice(parsed)]})()
            
    class MockBetaChat:
        completions = MockCompletions()
        
    class MockBeta:
        chat = MockBetaChat()
        
    class MockClient:
        beta = MockBeta()
        
    return MockClient()

def test_fallback_successful_generation(session, mock_client, monkeypatch):
    """Test generating a recipe, mapping ingredients, and returning macros."""
    # Mock batched embeddings and search
    monkeypatch.setattr("fallback.get_embeddings_batch", lambda texts, client: [[0.1] * 1536 for _ in texts])
    
    def mock_find_closest_food_with_vector(query, vector, db, threshold=0.70):
        if query == "chicken":
            return {"calories": 165.0, "protein": 31.0, "carbs": 0.0, "fat": 3.6, "similarity_score": 0.9}
        if query == "rice":
            return {"calories": 130.0, "protein": 2.7, "carbs": 28.0, "fat": 0.3, "similarity_score": 0.9}
        return None
        
    monkeypatch.setattr("fallback.find_closest_food_with_vector", mock_find_closest_food_with_vector)
    
    result = generate_recipe_fallback("unknown dish", session, mock_client)
    
    assert result is not None
    assert result["status"] == "success"
    assert result["typical_serving_grams"] == 300.0
    
    # 200g chicken (330 kcal) + 100g rice (130 kcal) = 460 kcal
    assert result["calories"] == 460.0
    
    # Check DB
    candidate = session.exec(select(GeneratedRecipeCandidate)).first()
    assert candidate.status == "pending"
    assert candidate.calories == 460.0
    
    log = session.exec(select(RecipeGenerationLog)).first()
    assert log.status == "success"
    
    # Check lock was released (lease_expires_at cleared)
    candidate = session.exec(select(GeneratedRecipeCandidate)).first()
    assert candidate is not None
    assert candidate.lease_expires_at is None

def test_fallback_unresolved_ingredients_fails_safely(session, mock_client, monkeypatch):
    """Verify that ANY unresolved ingredient fails the generation completely."""
    monkeypatch.setattr("fallback.get_embeddings_batch", lambda texts, client: [[0.1] * 1536 for _ in texts])
    
    def mock_find_closest_food_with_vector(query, vector, db, threshold=0.70):
        if query == "chicken":
            return {"calories": 165.0, "protein": 31.0, "carbs": 0.0, "fat": 3.6, "similarity_score": 0.9}
        return None # Rice fails to resolve
        
    monkeypatch.setattr("fallback.find_closest_food_with_vector", mock_find_closest_food_with_vector)
    
    result = generate_recipe_fallback("unknown dish", session, mock_client)
    
    assert result is not None
    assert result["status"] == "failed"
    assert "rice" in result["unresolved_ingredients"]
    
    # Verify candidate was NOT saved
    candidate = session.exec(select(GeneratedRecipeCandidate)).first()
    assert candidate is None
    
    # Verify failure log was saved
    log = session.exec(select(RecipeGenerationLog)).first()
    assert log.status == "failed"
    assert "rice" in log.error_message

def test_fallback_cache_hit(session, mock_client):
    """Test that a previously generated recipe is returned from cache."""
    now_iso = datetime.now(timezone.utc).isoformat()
    candidate = GeneratedRecipeCandidate(
        normalized_dish_name="cached dish",
        ingredients_json="{}",
        calories=500.0,
        protein=30.0,
        carbs=40.0,
        fat=10.0,
        typical_serving_grams=250.0,
        model_version="test",
        status="approved",
        created_at=now_iso
    )
    session.add(candidate)
    session.commit()
    
    result = generate_recipe_fallback("cached dish", session, None)
    
    assert result is not None
    assert result["status"] == "success"
    assert result["calories"] == 500.0
    assert result["typical_serving_grams"] == 250.0

def test_fallback_daily_limit(session, mock_client):
    """Test that generation stops if the global cap is reached."""
    import fallback
    now_iso = datetime.now(timezone.utc).isoformat()
    
    # Add 20 success logs for today
    for _ in range(fallback.MAX_RECIPE_GENERATIONS_PER_DAY):
        log = RecipeGenerationLog(
            normalized_dish_name="some dish",
            status="success",
            created_at=now_iso
        )
        session.add(log)
    session.commit()
    
    result = generate_recipe_fallback("new dish", session, mock_client)
    assert result["status"] == "failed"
    assert "Global daily generation cap reached" in result["unresolved_ingredients"]

def test_fallback_concurrency_lock(session, mock_client):
    """Test that concurrent requests are blocked via the lease on GeneratedRecipeCandidate."""
    from datetime import timedelta
    now_iso = datetime.now(timezone.utc).isoformat()
    future_iso = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()

    # Simulate an active lease (generation in-flight) for 'concurrent dish'
    candidate = GeneratedRecipeCandidate(
        normalized_dish_name="concurrent dish",
        ingredients_json="",
        calories=0, protein=0, carbs=0, fat=0,
        typical_serving_grams=0,
        model_version="pending",
        status="pending",
        lease_expires_at=future_iso,
        created_at=now_iso,
    )
    session.add(candidate)
    session.commit()

    result = generate_recipe_fallback("concurrent dish", session, mock_client)
    assert result["status"] == "failed"
    assert "Concurrent generation in progress" in result["unresolved_ingredients"]

def test_fallback_evaluator_readonly(session, mock_client, monkeypatch):
    """Test that persist=False prevents ANY database mutations."""
    monkeypatch.setattr("fallback.get_embeddings_batch", lambda texts, client: [[0.1] * 1536 for _ in texts])
    
    def mock_find_closest_food_with_vector(*args, **kwargs):
        return {"calories": 100.0, "protein": 10.0, "carbs": 10.0, "fat": 10.0, "similarity_score": 0.9}
        
    monkeypatch.setattr("fallback.find_closest_food_with_vector", mock_find_closest_food_with_vector)
    
    result = generate_recipe_fallback("unknown dish", session, mock_client, persist=False)
    
    assert result["status"] == "success"

    # Verify NOTHING was saved
    assert session.exec(select(GeneratedRecipeCandidate)).first() is None
    assert session.exec(select(RecipeGenerationLog)).first() is None
def test_fallback_invalid_generation(session, monkeypatch):
    """Test that boundary violations (weights, counts) result in safe failures."""
    
    def create_mock_client_with_parsed(parsed_obj):
        class MockChoice:
            def __init__(self, parsed):
                self.message = type('MockMsg', (), {'parsed': parsed})()
        class MockCompletions:
            def parse(self, *args, **kwargs):
                return type('MockResp', (), {'choices': [MockChoice(parsed_obj)]})()
        return type('MockClient', (), {'beta': type('MockBeta', (), {'chat': type('MockChat', (), {'completions': MockCompletions()})()})()})()

    # 1. Zero weight ingredient
    parsed_zero = GeneratedRecipeStructure(
        dish_name="bad dish", typical_serving_grams=300.0,
        ingredients=[GeneratedIngredient(name="air", weight_grams=0.0)], assumptions=""
    )
    res_zero = generate_recipe_fallback("bad dish", session, create_mock_client_with_parsed(parsed_zero))
    assert res_zero["status"] == "failed"
    assert "Invalid ingredient weight" in res_zero["unresolved_ingredients"][0]

    # 2. Huge weight ingredient
    parsed_huge = GeneratedRecipeStructure(
        dish_name="bad dish huge", typical_serving_grams=300.0,
        ingredients=[GeneratedIngredient(name="salt", weight_grams=5000.0)], assumptions=""
    )
    res_huge = generate_recipe_fallback("bad dish huge", session, create_mock_client_with_parsed(parsed_huge))
    assert res_huge["status"] == "failed"
    assert "Invalid ingredient weight" in res_huge["unresolved_ingredients"][0]
    
    # 3. Empty ingredients list
    parsed_empty = GeneratedRecipeStructure(
        dish_name="bad dish empty", typical_serving_grams=300.0,
        ingredients=[], assumptions=""
    )
    res_empty = generate_recipe_fallback("bad dish empty", session, create_mock_client_with_parsed(parsed_empty))
    assert res_empty["status"] == "failed"
    assert "Invalid ingredient count" in res_empty["unresolved_ingredients"][0]
    
    # 4. Oversized serving
    parsed_oversized = GeneratedRecipeStructure(
        dish_name="bad dish oversized", typical_serving_grams=5000.0,
        ingredients=[GeneratedIngredient(name="chicken", weight_grams=100.0)], assumptions=""
    )
    res_oversized = generate_recipe_fallback("bad dish oversized", session, create_mock_client_with_parsed(parsed_oversized))
    assert res_oversized["status"] == "failed"
    assert "Invalid serving weight" in res_oversized["unresolved_ingredients"][0]
