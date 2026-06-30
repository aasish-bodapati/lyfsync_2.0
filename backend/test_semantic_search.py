import os
import sys
from sqlmodel import create_engine, Session, select
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

from main import USDARaw, ICMRRaw

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL not found.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_embedding(text: str):
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=[text]
    )
    return response.data[0].embedding

def search(query: str):
    print(f"\n🔍 Searching for: '{query}'")
    query_emb = get_embedding(query)
    
    with Session(engine) as session:
        # Query USDA Raw Table
        usda_results = session.exec(
            select(USDARaw)
            .order_by(USDARaw.embedding.cosine_distance(query_emb))
            .limit(3)
        ).all()
        
        # Query ICMR Raw Table
        icmr_results = session.exec(
            select(ICMRRaw)
            .order_by(ICMRRaw.embedding.cosine_distance(query_emb))
            .limit(3)
        ).all()
        
        # Display Results
        print("--- USDA raw matches ---")
        for r in usda_results:
            print(f"  {r.description:<50} | Cal={r.calories:<6} | P={r.protein:<5} | C={r.carbs:<5} | F={r.fat:<5}")
            
        print("--- ICMR raw matches ---")
        for r in icmr_results:
            print(f"  {r.food_name:<50} | Cal={r.calories:<6} | P={r.protein:<5} | C={r.carbs:<5} | F={r.fat:<5}")

if __name__ == "__main__":
    test_queries = [
        "yellow lentils",
        "ghee butter",
        "skinless chicken",
        "paneer cheese",
        "wheat flour"
    ]
    for q in test_queries:
        search(q)
