import os, sys
sys.path.append('backend')
from dotenv import load_dotenv
load_dotenv('backend/.env', override=True)

from sqlmodel import create_engine, Session, select
from main import Meal, DATABASE_URL
print(f"DATABASE_URL: {DATABASE_URL}")
engine = create_engine(DATABASE_URL)

# Force creation of tables for testing
from main import SQLModel
SQLModel.metadata.create_all(engine)

with Session(engine) as session:
    print("Testing database write...")
    test_meal = Meal(raw_text="2 eggs", meal_type="breakfast", calories=140.0, protein=12.0, carbs=1.0, fat=10.0)
    session.add(test_meal)
    session.commit()
    
    print("Testing database select...")
    meals = session.exec(select(Meal)).all()
    print(f"Found {len(meals)} meals in the SQLite database successfully!")
