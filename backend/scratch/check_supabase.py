from sqlmodel import create_engine, Session, text
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")
db_url = os.getenv("DATABASE_URL")
engine = create_engine(db_url)

with Session(engine) as session:
    try:
        total = session.exec(text("SELECT count(*) FROM food_nutrition;")).first()[0]
        cooked = session.exec(text("SELECT count(*) FROM food_nutrition WHERE description ILIKE '%cooked%' OR description ILIKE '%boiled%' OR description ILIKE '%baked%' OR description ILIKE '%roasted%' OR description ILIKE '%fried%';")).first()[0]
        raw = session.exec(text("SELECT count(*) FROM food_nutrition WHERE description ILIKE '%raw%';")).first()[0]
        print(f"Total foods: {total}")
        print(f"Cooked/Boiled/Baked/Fried: {cooked}")
        print(f"Raw: {raw}")
    except Exception as e:
        print(f"Error: {e}")
