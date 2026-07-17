import os
import json
from openai import OpenAI
from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

STAPLE_DISHES = [
    "Dal Tadka",
    "Chapati / Roti",
    "Rajma",
    "Chole",
    "Aloo Sabzi",
    "Palak Paneer",
    "Khichdi",
    "Sambar",
    "Aloo Gobi",
    "Jeera Rice",
]

SYSTEM_PROMPT = """You are a culinary expert specializing in traditional Indian home cooking.
Your task is to generate the single most canonical, golden-baseline recipe for each dish provided.
The recipe must reflect the most widely accepted, home-style version across India, using only
average household ingredients (nothing exotic or restaurant-specific).
Respond ONLY with a valid JSON array. No extra text. Each object must have:
- "name": exact dish name (string)
- "ingredients": ingredients as a plain text list separated by newlines (string)
- "cooking_instructions": step-by-step instructions as a numbered plain text list (string)
"""

def generate_batch(dishes: list[str], run_label: str, batch_num: int) -> list[dict]:
    print(f"  Batch {batch_num}: {', '.join(dishes)}")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Generate the golden-baseline home-style recipe for each of these 5 staple Indian dishes: {', '.join(dishes)}. Return a JSON object with a 'recipes' key containing the array."
            }
        ],
        temperature=0.3,
    )
    data = json.loads(response.choices[0].message.content)
    return data.get("recipes", [])


def generate_recipes(run_label: str) -> list[dict]:
    print(f"\n--- Run {run_label}: Calling OpenAI in 2 batches... ---")
    batch1 = generate_batch(STAPLE_DISHES[:5], run_label, 1)
    batch2 = generate_batch(STAPLE_DISHES[5:], run_label, 2)
    return batch1 + batch2


def compare_all_runs(all_runs: list[list[dict]]):
    n = len(all_runs)
    print("\n" + "=" * 70)
    print(f"VARIANCE REPORT ACROSS {n} RUNS")
    print("=" * 70)

    # Build per-dish data indexed by dish name
    dish_names = [r["name"] for r in all_runs[0]]

    for dish in dish_names:
        print(f"\n📌 {dish}")

        # Collect ingredient sets and step counts across all runs
        ing_sets = []
        step_counts = []
        for run_idx, run in enumerate(all_runs):
            recipe = next((r for r in run if r["name"] == dish), None)
            if recipe:
                ing_set = set(line.strip() for line in recipe["ingredients"].splitlines() if line.strip())
                ing_sets.append(ing_set)
                steps = [l for l in recipe["cooking_instructions"].splitlines() if l.strip()]
                step_counts.append(len(steps))
            else:
                ing_sets.append(set())
                step_counts.append(0)

        # Ingredients that appear in ALL runs (consensus core)
        consensus_ings = ing_sets[0].copy()
        for s in ing_sets[1:]:
            consensus_ings &= s

        # Ingredients that appeared in SOME but not all runs (variable)
        all_ings = set().union(*ing_sets)
        variable_ings = all_ings - consensus_ings

        print(f"   ✅ Consensus ingredients ({len(consensus_ings)}): stable across all {n} runs")
        if variable_ings:
            print(f"   ⚠️  Variable ingredients ({len(variable_ings)}): {', '.join(sorted(variable_ings))}")

        # Step count
        min_steps, max_steps = min(step_counts), max(step_counts)
        if min_steps == max_steps:
            print(f"   ✅ Steps: always {min_steps} steps")
        else:
            print(f"   ⚠️  Steps: ranged {min_steps}–{max_steps} across runs ({step_counts})")


if __name__ == "__main__":
    NUM_RUNS = 5
    all_runs = []

    for i in range(1, NUM_RUNS + 1):
        run = generate_recipes(str(i))
        print(f"   Got {len(run)} recipes")
        all_runs.append(run)

    compare_all_runs(all_runs)

    print("\n\n--- Full Run 1 Sample (Rajma) ---")
    for r in all_runs[0]:
        if "Rajma" in r["name"]:
            print(f"\nIngredients:\n{r['ingredients']}")
            print(f"\nInstructions:\n{r['cooking_instructions']}")
            break
