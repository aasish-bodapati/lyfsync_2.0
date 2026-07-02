import os
import sys
import asyncio
import json

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))
from main import generate_jury_baseline

async def run():
    print("🚀 Running Isolated LLM Jury Test for 'Tiramisu'...")
    try:
        final_recipe = await generate_jury_baseline("Tiramisu")
        print("\n✅ JURY CONSENSUS RECIPE:")
        print(json.dumps(final_recipe.model_dump(), indent=2))
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(run())
