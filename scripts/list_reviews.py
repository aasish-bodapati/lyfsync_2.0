import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))
from sqlmodel import Session, select, create_engine
from main import StaplesReview
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
engine = create_engine(os.getenv("DATABASE_URL"))

with Session(engine) as session:
    items = session.exec(select(StaplesReview)).all()
    for item in items:
        print(f"[{item.id}] {item.name}: {item.serving_size}")
