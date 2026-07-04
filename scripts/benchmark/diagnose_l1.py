"""
Stage-level diagnostic for Level 1 cases.
Traces the exact DB lookup for each ingredient to find where the calorie error originates.
"""
import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "backend", ".env"))

from sqlmodel import Session, create_engine, select
from sqlalchemy import text
from main import get_embedding, ICMRRaw, USDARaw, DATABASE_URL

engine = create_engine(DATABASE_URL)

CASES = [
    ("100g raw oats",      "oats"),
    ("200g chicken breast","chicken breast"),
]

with Session(engine) as db:
    for label, query in CASES:
        print(f"\n{'='*60}")
        print(f"Query: '{label}'")
        emb = get_embedding(query)

        icmr_dist = ICMRRaw.embedding.cosine_distance(emb)
        best_icmr = db.exec(select(ICMRRaw, icmr_dist).order_by(icmr_dist).limit(3)).all()

        usda_dist = USDARaw.embedding.cosine_distance(emb)
        best_usda = db.exec(select(USDARaw, usda_dist).order_by(usda_dist).limit(3)).all()

        print("\n  [ICMR top-3 matches]")
        for row, dist in best_icmr:
            print(f"    dist={dist:.3f} | {row.food_name:<40} | {row.calories:.1f} kcal/100g | cat={row.category}")

        print("\n  [USDA top-3 matches]")
        for row, dist in best_usda:
            print(f"    dist={dist:.3f} | {row.description:<40} | {row.calories:.1f} kcal/100g")
