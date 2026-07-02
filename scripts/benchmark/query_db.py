import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
from sqlmodel import Session, select, create_engine
from main import USDARaw, ICMRRaw, Staple
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "backend", ".env"))
engine = create_engine(os.getenv("DATABASE_URL"))

def query_usda(query_str):
    with Session(engine) as session:
        results = session.exec(select(USDARaw).where(USDARaw.description.ilike(f"%{query_str}%"))).all()
        for r in results:
            print(f"USDA [{r.fdc_id}]: {r.description} - C: {r.calories}, P: {r.protein}, Cb: {r.carbs}, F: {r.fat}")

def query_staple(query_str):
    with Session(engine) as session:
        results = session.exec(select(Staple).where(Staple.name.ilike(f"%{query_str}%"))).all()
        for r in results:
            print(f"Staple: {r.name} - SS: {r.serving_size}")

if __name__ == "__main__":
    print("--- USDA ---")
    query_usda("egg, whole")
    query_usda("chicken, broiler")
    print("--- Staples ---")
    query_staple("butter chicken")
    query_staple("pizza")
