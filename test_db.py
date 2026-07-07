import os, sys
sys.path.append('backend')
from dotenv import load_dotenv
load_dotenv('backend/.env', override=True)

from sqlmodel import create_engine, Session, select
from main import ReferenceServing, DATABASE_URL
print(f"DATABASE_URL: {DATABASE_URL[:20]}...")
engine = create_engine(DATABASE_URL)
with Session(engine) as session:
    print("Testing select...")
    all_priors = session.exec(select(ReferenceServing)).all()
    print(f"Found {len(all_priors)} priors.")
