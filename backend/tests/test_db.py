import os
import sys
from dotenv import load_dotenv

dotenv_path= os.path.dirname(os.path.dirname(__file__))
sys.path.append(dotenv_path)

from sqlmodel import SQLModel, Session, create_engine, select
from main import Meal

load_dotenv(os.path.join(dotenv_path, ".env"))

TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
SQLModel.metadata.create_all(engine)

print(TEST_DATABASE_URL)


def test_meal_database_write_and_read():

    with Session(engine) as session:
        test_meal = Meal(raw_text="2 eggs", meal_type="breakfast", calories=140.0, protein=12.0, carbs=1.0, fat=10.0)
        session.add(test_meal)
        session.commit()

        meals = session.exec(select(Meal).limit(5)).all()
        print(f"Success! Found {len(meals)} meals in database.")

        for m in meals:
            print(m)
