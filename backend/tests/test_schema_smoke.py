import os
import pytest
from sqlalchemy import create_engine, text

def test_production_schema_smoke():
    """
    Smoke test to verify that the Supabase (Postgres) schema matches our
    codebase expectations, specifically checking the new lease_expires_at 
    and cuisine columns.
    
    This only runs if DATABASE_URL is set and points to Postgres.
    """
    from dotenv import load_dotenv
    import os
    
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    load_dotenv(dotenv_path)
    
    db_url = os.environ.get("DATABASE_URL")
    if not db_url or "postgres" not in db_url:
        pytest.fail("No postgres DATABASE_URL found. Test must run against staging!")
        
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        # 1. Verify lease_expires_at is in generated_recipe_candidates
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'generated_recipe_candidates' 
              AND column_name = 'lease_expires_at'
        """)).fetchone()
        
        assert result is not None, "Missing 'lease_expires_at' column in 'generated_recipe_candidates'!"
        
        # 2. Verify cuisine is in recipes
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'recipes' 
              AND column_name = 'cuisine'
        """)).fetchone()
        
        assert result is not None, "Missing 'cuisine' column in 'recipes'!"
        
        # 3. Verify recipe_generation_locks was dropped
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'recipe_generation_locks'
        """)).fetchone()
        
        assert result is None, "'recipe_generation_locks' table still exists but should be dropped!"
