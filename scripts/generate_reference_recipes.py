import os
import sys
import json
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from typing import List

# Load environment variables
load_dotenv("/Users/aasish/Documents/lyfsync_2.0/backend/.env", override=True)

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("Error: OPENAI_API_KEY not found in environment.")
    sys.exit(1)

client = OpenAI(api_key=api_key)

# 1. Pydantic models for structured output (Macros calculated mathematically, not by LLM)
class ReferenceRecipeItem(BaseModel):
    name: str
    serving_size: str
    ingredients_text: str
    instructions: str

class BatchResponse(BaseModel):
    recipes: List[ReferenceRecipeItem]

# Curated list of 180 most common generic Indian dishes, split into 5 balanced batches
batches = [
    # Batch 1: Staples, Rice & Breads
    [
        "Roti / Chapati", "Plain Paratha", "Aloo Paratha", "Paneer Paratha", "Gobi Paratha",
        "Methi Paratha", "Poori", "Bhatura", "Plain Naan", "Butter Naan", "Garlic Naan",
        "Tandoori Roti", "Missi Roti", "Rumali Roti", "Plain Basmati Rice", "Brown Rice",
        "Jeera Rice", "Ghee Rice", "Peas Pulao", "Vegetable Biryani", "Chicken Biryani",
        "Mutton Biryani", "Egg Biryani", "Paneer Biryani", "Curd Rice", "Lemon Rice",
        "Tamarind Rice", "Tomato Rice", "Coconut Rice", "Khichdi", "Oats Khichdi",
        "Daliya (savory)", "Sweet Daliya", "Plain Oatmeal (cooked in water)", "Masala Oats",
        "Ragi Roti"
    ],
    # Batch 2: Vegetarian Dals & Gravies
    [
        "Dal Tadka", "Dal Fry", "Dal Makhani", "Panchmel Dal", "Chana Dal", "Sambar",
        "Rasam", "Kadhi Pakora", "Rajma Masala", "Chole Masala", "Kala Chana Masala",
        "Lobia Curry (Black eyed peas)", "Paneer Butter Masala", "Palak Paneer", "Shahi Paneer",
        "Kadai Paneer", "Matar Paneer", "Paneer Bhurji", "Malai Kofta", "Aloo Gobi",
        "Aloo Baingan", "Aloo Jeera", "Bhindi Masala (okra stir fry)", "Baingan Bharta",
        "Cabbage Poriyal", "Beans Poriyal", "Bhindi Fry", "Lauki Ki Sabzi (Bottle gourd)",
        "Turai Ki Sabzi (Ridge gourd)", "Kathal Ki Sabzi (Jackfruit curry)", "Mushroom Masala",
        "Vegetable Kurma", "Mixed Vegetable Curry", "Dum Aloo", "Tindora Fry",
        "Karela Masala (Bitter gourd)", "Sarson Ka Saag"
    ],
    # Batch 3: Non-Vegetarian & Egg Curries/Starters
    [
        "Chicken Curry (home style)", "Butter Chicken", "Chicken Tikka Masala", "Kadai Chicken",
        "Chicken Korma", "Chicken Sukka", "Pepper Chicken", "Mutton Curry",
        "Mutton Rogan Josh", "Mutton Keema Masala", "Fish Curry (generic)", "Fish Fry",
        "Prawn Curry", "Egg Curry", "Egg Bhurji (Scrambled eggs)", "Plain Omelette",
        "Egg White Omelette", "Boiled Egg (single)", "Scrambled Eggs (plain)", "Sunny Side Up Egg",
        "Chicken Fry", "Tandoori Chicken (1 piece)", "Chicken Tikka (6 pieces)", "Fish Tikka",
        "Mutton Seekh Kabab", "Chicken Seekh Kabab", "Egg Roast (Kerala style)"
    ],
    # Batch 4: Breakfast, Snacks & Street Foods
    [
        "Plain Dosa", "Masala Dosa", "Onion Dosa", "Rava Dosa", "Set Dosa",
        "Plain Idli (2 pieces)", "Rava Idli (2 pieces)", "Medu Vada (2 pieces)",
        "Masala Vada (2 pieces)", "Upma", "Semiya Upma", "Plain Poha",
        "Indori Poha", "Sabudana Khichdi", "Sabudana Vada", "Plain Uttapam",
        "Onion Uttapam", "Bread Butter Toast", "Bread Omelette", "French Toast (sweet)",
        "Samosa (1 piece)", "Kachori (1 piece)", "Onion Pakora (plate)", "Mix Veg Pakora",
        "Paneer Pakora", "Bread Pakora", "Aloo Bonda", "Dhokla (3 pieces)",
        "Khandvi (4 pieces)", "Thepla (1 piece)", "Pav Bhaji (1 plate)", "Vada Pav (1 piece)",
        "Misal Pav (1 plate)", "Bhel Puri", "Sev Puri", "Pani Puri (6 pieces)",
        "Dahi Puri", "Aloo Tikki", "Papdi Chaat", "Dahi Vada"
    ],
    # Batch 5: Desserts, Drinks & Sides
    [
        "Gulab Jamun (2 pieces)", "Rasgulla (2 pieces)", "Rice Kheer", "Semiyan Payasam",
        "Gajar Ka Halwa", "Moong Dal Halwa", "Suji Ka Halwa", "Rasmalai (2 pieces)",
        "Jalebi (2 pieces)", "Shrikhand", "Kulfi", "Mysore Pak (1 piece)",
        "Besan Ladoo (1 piece)", "Motichoor Ladoo (1 piece)", "Kaju Katli (2 pieces)",
        "Plain Yogurt / Dahi", "Boondi Raita", "Cucumber Raita", "Mint Raita",
        "Coconut Chutney", "Green Chutney (Coriander-mint)", "Tamarind Chutney",
        "Masala Papad", "Roasted Papad", "Sweet Lassi", "Mango Lassi",
        "Salted Lassi", "Masala Buttermilk (Chaas)", "Garam Chai (Milk tea)",
        "Filter Coffee", "Black Coffee", "Green Tea", "Lemon Tea",
        "Badam Milk", "Coconut Water", "Aam Panna", "Jaljeera",
        "Lemonade (Shikanji)"
    ]
]

def generate_all():
    all_recipes = []
    
    for idx, batch in enumerate(batches):
        print(f"\n⚡ Generating Batch {idx + 1}/{len(batches)} (contains {len(batch)} dishes)...")
        prompt = (
            f"Generate standard recipes and raw ingredient lists for the following Indian dishes:\n"
            f"{', '.join(batch)}\n\n"
            "CRITICAL STAPLE & BASE RULES:\n\n"
            "1. THE GOLDEN BASELINE RULE:\n"
            "   - Make the recipe as standard, simple, and generic as possible so that it represents the GOLDEN BASELINE / GOLDEN AVERAGE of the dish.\n"
            "   - Avoid local variations, specialty recipes, or fancy restaurant-style versions.\n"
            "   - Focus exclusively on the core, staple ingredients that dictate the baseline caloric and macronutrient structure of the dish.\n\n"
            "2. STAPLE INGREDIENTS ONLY:\n"
            "   - Use only common, daily staple ingredients (such as basic flours, rice, standard dals, common vegetables, milk, curd, paneer, eggs, simple meats, and standard cooking oils/ghee).\n"
            "   - Do NOT include fancy, exotic, or garnish-only ingredients (e.g., saffron, cashews/almonds in basic curries, cream/butter in home-style curries, specific local spices, or food coloring) that are not essential to the staple food profile.\n\n"
            "3. LITERAL NAME MODIFIERS:\n"
            "   - If the dish name contains 'Plain' (e.g., 'Plain Dosa', 'Plain Naan', 'Plain Rice', 'Plain Paratha'), it must contain ONLY the absolute base grain/batter/meat. Do NOT include stuffing, gravies, potato masala, or heavy toppings.\n"
            "   - If the dish name contains a characterizing ingredient (e.g., 'Aloo Paratha' contains 'Aloo', 'Paneer Paratha' contains 'Paneer', 'Matar Paneer' contains 'Matar' and 'Paneer'), those exact raw ingredients MUST be listed in the ingredients list with non-zero weights.\n"
            "   - If the dish name contains 'Butter' or 'Ghee' (e.g., 'Butter Naan', 'Ghee Rice'), the raw ingredients list MUST contain 'Butter' or 'Ghee'. Otherwise, use standard neutral cooking oil.\n\n"
            "4. RAW INGREDIENT LISTING:\n"
            "   - Provide a comma-separated list of raw, uncooked ingredients and weights required to make exactly that 1 serving (e.g., '100g raw chicken breast, 50g raw basmati rice, 15g sunflower oil, 30g onion, 20g tomato, salt to taste').\n"
            "   - Do NOT list cooked states in the ingredients list.\n\n"
            "5. COOKING INSTRUCTIONS:\n"
            "   - Provide short, 3-4 step cooking instructions showing how these raw ingredients are combined to make the final dish.\n\n"
            "6. PORTION SIZE:\n"
            "   - Specify a realistic 1-person portion with approximate weight (e.g., '1 piece (30g)', '1 bowl (150g)', '1 plate (350g)').\n\n"
            "---\n\n"
            "SELF-CORRECTION PASS:\n"
            "Before outputting, review the list of generated ingredients for each dish:\n"
            "- Did 'Plain Dosa' get potato? If yes, remove it.\n"
            "- Did 'Butter Naan' get butter? If no, add it.\n"
            "- Did a basic home-style dish get premium cream or saffron? If yes, remove it to keep it as a basic staple.\n"
            "Only output the corrected, logically verified records in the requested schema."
        )
        
        try:
            completion = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise, research-backed Indian nutrition and recipe database generator. Output recipes in the requested schema."
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format=BatchResponse,
                temperature=0.2
            )
            batch_recipes = completion.choices[0].message.parsed.recipes
            all_recipes.extend(batch_recipes)
            print(f"✅ Batch {idx + 1} generated successfully: {len(batch_recipes)} items.")
        except Exception as e:
            print(f"❌ Failed to generate Batch {idx + 1}: {e}")
            
    # Save results to JSON
    output_dir = "/Users/aasish/Documents/lyfsync_2.0/backend/data"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "reference_recipe_templates.json")
    
    # Convert Pydantic models to dicts for serialization
    data_to_save = [item.model_dump() for item in all_recipes]
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        
    print(f"\n🎉 Generation completed! Saved {len(data_to_save)} standard reference recipe templates to {output_path}")

if __name__ == "__main__":
    generate_all()
