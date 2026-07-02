import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
from sqlmodel import Session, select, create_engine
from main import USDARaw, ICMRRaw, Staple
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "backend", ".env"))
engine = create_engine(os.getenv("DATABASE_URL"))

def search(term, table):
    with Session(engine) as session:
        if table == "usda":
            results = session.exec(select(USDARaw).where(USDARaw.description.ilike(f"%{term}%")).limit(5)).all()
            for r in results:
                print(f"USDA [{r.fdc_id}]: {r.description} - C:{r.calories} P:{r.protein} F:{r.fat} Cb:{r.carbs}")
        elif table == "icmr":
            results = session.exec(select(ICMRRaw).where(ICMRRaw.name.ilike(f"%{term}%")).limit(5)).all()
            for r in results:
                print(f"ICMR: {r.name} - C:{r.calories} P:{r.protein} F:{r.fat} Cb:{r.carbs}")
        elif table == "staple":
            results = session.exec(select(Staple).where(Staple.name.ilike(f"%{term}%")).limit(5)).all()
            for r in results:
                print(f"Staple: {r.name} - SS:{r.serving_size}")

search("egg, whole", "usda")
search("chicken, broiler", "usda")
search("rice, white", "usda")
search("oats", "usda")
search("milk, whole", "usda")
search("rajma", "staple")
search("butter chicken", "staple")
