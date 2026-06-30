import os
import sys
from sqlmodel import create_engine, Session, select
from dotenv import load_dotenv
from openai import OpenAI

# Load env variables explicitly
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

# Import models
from main import USDARaw, ICMRRaw

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

BATCH_SIZE = 100

def get_embeddings(texts):
    print(f"Requesting embeddings for batch of {len(texts)} items...")
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    return [data.embedding for data in response.data]

def generate_embeddings():
    with Session(engine) as session:
        # 1. USDARaw
        print("Checking USDARaw records missing embeddings...")
        usda_statement = select(USDARaw).where(USDARaw.embedding == None)
        usda_records = session.exec(usda_statement).all()
        print(f"Found {len(usda_records)} USDARaw records to embed.")
        
        if usda_records:
            for i in range(0, len(usda_records), BATCH_SIZE):
                batch = usda_records[i:i+BATCH_SIZE]
                texts = [r.description for r in batch]
                try:
                    embeddings = get_embeddings(texts)
                    for record, emb in zip(batch, embeddings):
                        record.embedding = emb
                    session.commit()
                    print(f"  Processed {i + len(batch)}/{len(usda_records)} USDA records.")
                except Exception as e:
                    print(f"  Error processing USDA batch starting at {i}: {e}")
                    session.rollback()

        # 2. ICMRRaw
        print("Checking ICMRRaw records missing embeddings...")
        icmr_statement = select(ICMRRaw).where(ICMRRaw.embedding == None)
        icmr_records = session.exec(icmr_statement).all()
        print(f"Found {len(icmr_records)} ICMRRaw records to embed.")
        
        if icmr_records:
            for i in range(0, len(icmr_records), BATCH_SIZE):
                batch = icmr_records[i:i+BATCH_SIZE]
                texts = [r.food_name for r in batch]
                try:
                    embeddings = get_embeddings(texts)
                    for record, emb in zip(batch, embeddings):
                        record.embedding = emb
                    session.commit()
                    print(f"  Processed {i + len(batch)}/{len(icmr_records)} ICMR records.")
                except Exception as e:
                    print(f"  Error processing ICMR batch starting at {i}: {e}")
                    session.rollback()

        print("Embeddings generation complete!")

if __name__ == "__main__":
    generate_embeddings()
