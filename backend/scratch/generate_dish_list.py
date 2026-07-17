import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class Dish(BaseModel):
    name: str
    cuisine: str
    category: str

class DishList(BaseModel):
    dishes: list[Dish]

def generate_dish_list():
    prompt = """
    Generate a curated list of exactly 250 traditional Indian dishes.
    Categorize them according to the following breakdown:
    - 50 North Indian mains (lunch/dinner)
    - 40 South Indian mains (lunch/dinner)
    - 25 West Indian (Gujarati/Maharashtrian) mains (lunch/dinner)
    - 20 East Indian (Bengali/Odia) mains (lunch/dinner)
    - 40 Breakfast dishes (across all regions)
    - 35 Snacks & street food (across all regions)
    - 25 Desserts & sweets (across all regions)
    - 15 Rice dishes (across all regions)
    
    Ensure the 'category' field is one of: "breakfast", "lunch", "dinner", "snack", "dessert". 
    (Mains can be randomly assigned to lunch or dinner).
    Ensure the 'cuisine' field represents the region (e.g., "North Indian", "South Indian", "West Indian", "East Indian", or specific state like "Punjabi", "Bengali").
    """
    
    print("Generating dish list via OpenAI...")
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": "You are a culinary expert specializing in Indian cuisine."},
            {"role": "user", "content": prompt}
        ],
        response_format=DishList,
    )
    
    dish_list = completion.choices[0].message.parsed.dict()
    
    output_path = os.path.join(BACKEND_DIR, "data", "dish_list.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(dish_list, f, indent=4)
        
    print(f"Generated {len(dish_list['dishes'])} dishes and saved to {output_path}")

if __name__ == "__main__":
    generate_dish_list()
