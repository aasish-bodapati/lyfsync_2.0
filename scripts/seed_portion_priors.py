"""
Seed the portion_priors table on Supabase from the pre-built portion_priors.json.
Run once. Safe to re-run — clears and re-seeds the table.
"""
import os
import sys
import json
from sqlmodel import create_engine, Session, SQLModel, delete
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"), override=True)
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from main import PortionPrior

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL not found.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)

def seed():
    json_path = os.path.join(os.path.dirname(__file__), "portion_priors.json")
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found. Run export_portion_priors.py first.")
        sys.exit(1)

    with open(json_path, "r") as f:
        records = json.load(f)

    print(f"Loaded {len(records)} portion priors from JSON.")
    print("Ensuring database tables exist...")
    SQLModel.metadata.create_all(engine)

    db_records = [
        PortionPrior(
            food_name=r["food"],
            unit=r["unit"],
            gram_weight=r["gram_weight"],
            n_samples=r["n_samples"],
        )
        for r in records
    ]

    with Session(engine) as session:
        print("Clearing existing portion_priors rows...")
        session.exec(delete(PortionPrior))
        session.commit()

        print(f"Inserting {len(db_records)} rows...")
        session.add_all(db_records)
        session.commit()

    print(f"✅ Successfully seeded {len(db_records)} portion priors into Supabase!")

if __name__ == "__main__":
    seed()
