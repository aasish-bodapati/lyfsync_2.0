import os
import json
import psycopg2
from psycopg2.extras import execute_values
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class RecipeOutput(BaseModel):
    name: str
    cuisine: str
    category: str
    description: str
    ingredients: str
    cooking_instructions: str
    prep_time_mins: int
    cook_time_mins: int
    calories_per_100g: float
    protein_per_100g: float
    carbs_per_100g: float
    fat_per_100g: float
    typical_serving_grams: float
    servings_per_recipe: int

class RecipeBatch(BaseModel):
    recipes: list[RecipeOutput]

SYSTEM_PROMPT = """You are a culinary expert and certified nutritionist specializing in traditional Indian home cooking.
Your task is to generate the single most canonical, golden-baseline recipe for each dish provided.
The recipe must reflect the most widely accepted, home-style version across India, using only average household ingredients.

Provide accurate macronutrient estimates per 100 grams of the prepared dish.
- 'description' should be a 1-2 line summary.
- 'ingredients' should be a plain text list separated by newlines.
- 'cooking_instructions' should be step-by-step instructions as a numbered plain text list.
- 'typical_serving_grams' is the weight in grams of one typical home serving (e.g. one bowl, one plate). This is used to calculate how many calories a user ate.
- 'servings_per_recipe' is how many people the recipe as written will feed.
"""

def generate_and_insert_batch(cursor, dishes: list[dict], batch_num: int):
    dish_names = [d["name"] for d in dishes]
    print(f"  Batch {batch_num}: {', '.join(dish_names)}")
    
    # Pass context about cuisine and category so OpenAI matches what we want
    dishes_context = "\n".join([f"- {d['name']} (Cuisine: {d['cuisine']}, Category: {d['category']})" for d in dishes])
    
    response = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Generate the golden-baseline home-style recipe for each of these {len(dishes)} Indian dishes:\n{dishes_context}\n\nEnsure 'name', 'cuisine', and 'category' strictly match the requested values."
            }
        ],
        response_format=RecipeBatch,
        temperature=0.3,
    )
    
    recipes_data = response.choices[0].message.parsed.recipes
    
    insert_values = []
    for recipe in recipes_data:
        insert_values.append((
            recipe.name,
            recipe.cuisine,
            recipe.category,
            recipe.description,
            recipe.ingredients,
            recipe.cooking_instructions,
            recipe.prep_time_mins,
            recipe.cook_time_mins,
            recipe.calories_per_100g,
            recipe.protein_per_100g,
            recipe.carbs_per_100g,
            recipe.fat_per_100g,
            recipe.typical_serving_grams,
            recipe.servings_per_recipe,
            "openai"
        ))

    insert_query = """
    INSERT INTO recipes (
        name, cuisine, category, description, ingredients, cooking_instructions, 
        prep_time_mins, cook_time_mins, calories, protein, carbs, fat,
        typical_serving_grams, servings_per_recipe, source
    ) VALUES %s
    ON CONFLICT (name) DO NOTHING;
    """
    
    execute_values(cursor, insert_query, insert_values)


def seed_recipes():
    print(f"Connecting to database: {DATABASE_URL}")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # Load dish list
    dish_list_path = os.path.join(BACKEND_DIR, "data", "dish_list.json")
    with open(dish_list_path, "r") as f:
        data = json.load(f)
        all_dishes = data.get("dishes", [])
        
    print(f"Loaded {len(all_dishes)} dishes from dish_list.json")

    # Fetch existing dishes to avoid regenerating them
    cursor.execute("SELECT name FROM recipes;")
    existing_dishes = set(row[0] for row in cursor.fetchall())
    
    dishes_to_generate = [d for d in all_dishes if d["name"] not in existing_dishes]
    
    print(f"{len(existing_dishes)} dishes already exist in DB. {len(dishes_to_generate)} remaining to generate.")

    batch_size = 5
    for i in range(0, len(dishes_to_generate), batch_size):
        batch = dishes_to_generate[i:i+batch_size]
        try:
            generate_and_insert_batch(cursor, batch, (i // batch_size) + 1)
            conn.commit()
            print(f"  ✅ Batch {(i // batch_size) + 1} committed successfully.")
        except Exception as e:
            print(f"  ❌ Error processing batch {(i // batch_size) + 1}: {e}")
            conn.rollback()

    conn.close()
    print("Seeding complete!")

if __name__ == "__main__":
    seed_recipes()
