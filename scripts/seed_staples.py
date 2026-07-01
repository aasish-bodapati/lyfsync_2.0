import os
import sys
import json
from sqlmodel import create_engine, Session, SQLModel, delete
from dotenv import load_dotenv
from openai import OpenAI

# Load env variables explicitly
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"), override=True)

# Add backend directory to sys.path for import resolution
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

# Import models
from main import Staple

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL not found.")
    sys.exit(1)

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("Error: OPENAI_API_KEY not found.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
openai_client = OpenAI(api_key=api_key)

def seed_staples():
    # 1. Load templates from JSON
    template_path = os.path.join(os.path.dirname(__file__), "..", "backend", "data", "reference_recipe_templates.json")
    if not os.path.exists(template_path):
        print(f"Error: Template file not found at {template_path}")
        sys.exit(1)
        
    with open(template_path, "r", encoding="utf-8") as f:
        recipes = json.load(f)
        
    print(f"Loaded {len(recipes)} recipe templates from JSON.")
    
    # 2. Recreate tables if needed
    print("Ensuring database tables exist...")
    SQLModel.metadata.create_all(engine)
    
    # 3. Generate embeddings in batches of 100 to avoid rate limits and minimize API calls
    print("Generating name embeddings...")
    batch_size = 100
    db_records = []
    
    for i in range(0, len(recipes), batch_size):
        batch = recipes[i:i + batch_size]
        names = [item["name"] for item in batch]
        
        print(f"  Generating embeddings for batch {i // batch_size + 1} ({len(names)} items)...")
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=names
        )
        
        for idx, item in enumerate(batch):
            record = Staple(
                name=item["name"],
                serving_size=item["serving_size"],
                ingredients_text=item["ingredients_text"],
                instructions=item["instructions"],
                embedding=response.data[idx].embedding
            )
            db_records.append(record)
            
    # 4. Clean old table and bulk-insert new records
    print("Seeding records into table 'staples'...")
    with Session(engine) as session:
        # Clear existing entries (removes the manually-seeded 20 staples)
        session.exec(delete(Staple))
        session.commit()
        
        # Add all and commit
        session.add_all(db_records)
        session.commit()
        
    print(f"Successfully seeded {len(db_records)} staples into the database!")

if __name__ == "__main__":
    seed_staples()
