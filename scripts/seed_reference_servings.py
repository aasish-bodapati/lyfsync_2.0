"""
Seed the reference_servings table on Supabase from the pre-built reference_servings.json.
Run once. Safe to re-run — clears and re-seeds the table.
"""
import os
import sys
import json
from sqlmodel import create_engine, Session, SQLModel, delete
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"), override=True)
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from main import ReferenceServing

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL not found.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)

def seed():
    json_path = os.path.join(os.path.dirname(__file__), "reference_servings.json")
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found. Run export_reference_servings.py first.")
        sys.exit(1)

    with open(json_path, "r") as f:
        records = json.load(f)

    print(f"Loaded {len(records)} portion priors from JSON.")
    print("Ensuring database tables exist...")
    SQLModel.metadata.create_all(engine)

    db_records = [
        ReferenceServing(
            food_name=r["food"],
            unit=r["unit"],
            gram_weight=r["gram_weight"],
            n_samples=r["n_samples"],
        )
        for r in records
    ]

    with Session(engine) as session:
        print("Clearing existing reference_servings rows...")
        session.exec(delete(ReferenceServing))
        session.commit()

        print(f"Inserting {len(db_records)} rows...")
        session.add_all(db_records)
        session.commit()

    print(f"✅ Successfully seeded {len(db_records)} portion priors into Supabase!")

if __name__ == "__main__":
    seed()
