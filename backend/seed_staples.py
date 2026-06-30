import os
import sys
from sqlmodel import create_engine, Session, SQLModel, delete
from dotenv import load_dotenv
from openai import OpenAI

# Load env variables explicitly
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

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

# Clean, standard generic staple cooked dishes
staple_recipes = [
    {
        "name": "Roti / Chapati",
        "serving_size": "1 piece (40g)",
        "ingredients_text": "30g Whole Wheat Flour (Atta), water as needed",
        "instructions": "1. Mix whole wheat flour with water and knead into a soft dough. 2. Divide the dough into small balls and roll each into a thin circle. 3. Cook on a hot tava until brown spots appear on both sides."
    },
    {
        "name": "Plain Paratha",
        "serving_size": "1 piece (60g)",
        "ingredients_text": "45g Whole Wheat Flour (Atta), 5g Ghee, water as needed",
        "instructions": "1. Prepare a dough with whole wheat flour, water, and a pinch of salt. 2. Roll out a ball of dough, spread ghee, and fold it to create layers. 3. Roll it out again and cook on a hot tava until golden brown on both sides."
    },
    {
        "name": "Aloo Paratha",
        "serving_size": "1 piece (120g)",
        "ingredients_text": "45g Whole Wheat Flour (Atta), 50g Potato, 5g Ghee, 10g Onion, salt and spices to taste",
        "instructions": "1. Boil and mash potatoes, mix with spices and chopped onions. 2. Stuff the potato mixture into rolled-out dough balls and seal. 3. Roll out gently and cook on a hot tava with ghee until golden brown."
    },
    {
        "name": "Paneer Paratha",
        "serving_size": "1 piece (120g)",
        "ingredients_text": "45g Whole Wheat Flour (Atta), 40g Paneer, 5g Ghee, 10g Onion, salt and spices to taste",
        "instructions": "1. Crumble paneer and mix with spices and chopped onions. 2. Stuff the mixture into rolled-out dough balls and seal. 3. Roll out gently and cook on a hot tava with ghee until golden brown."
    },
    {
        "name": "Plain Basmati Rice",
        "serving_size": "1 bowl (150g)",
        "ingredients_text": "50g Raw Basmati Rice, water as needed",
        "instructions": "1. Rinse basmati rice under cold water. 2. Boil water in a pot, add rice and a pinch of salt. 3. Cook until rice is tender and water is absorbed, then fluff with a fork."
    },
    {
        "name": "Jeera Rice",
        "serving_size": "1 bowl (160g)",
        "ingredients_text": "50g Raw Basmati Rice, 5g Ghee, 3g Cumin Seeds, water as needed",
        "instructions": "1. Rinse basmati rice and soak for 30 minutes. 2. Heat ghee in a pan, add cumin seeds, and sauté until fragrant. 3. Add soaked rice and water, cook until rice is tender and water is absorbed."
    },
    {
        "name": "Vegetable Biryani",
        "serving_size": "1 plate (350g)",
        "ingredients_text": "80g Raw Basmati Rice, 100g mixed raw vegetables (potato, peas, carrot), 10g Sunflower Oil, 20g Onion, 20g Tomato, 20g Buffalo Curd (Dahi), salt and spices to taste",
        "instructions": "1. Sauté mixed vegetables and onions with spices in oil. 2. Layer partially cooked basmati rice over the vegetables in a pot. 3. Cover and cook on low heat until rice is fully cooked and vegetables are tender."
    },
    {
        "name": "Chicken Biryani",
        "serving_size": "1 plate (350g)",
        "ingredients_text": "80g Raw Basmati Rice, 120g Raw Chicken Breast, 10g Ghee, 30g Onion, 20g Buffalo Curd (Dahi), 5g ginger-garlic paste, salt and spices to taste",
        "instructions": "1. Marinate raw chicken with curd, ginger-garlic paste, and spices for 30 minutes. 2. Layer marinated chicken and partially cooked basmati rice in a pot. 3. Cover and cook on low heat until chicken is tender and rice is fully cooked."
    },
    {
        "name": "Dal Tadka",
        "serving_size": "1 bowl (200g)",
        "ingredients_text": "50g Toor Dal (Split Pigeon Peas), 10g Ghee, 20g Onion, 20g Tomato, 5g cumin seeds, 3g garlic, salt and turmeric to taste",
        "instructions": "1. Cook toor dal with water and turmeric until soft. 2. In a separate pan, heat ghee, add cumin seeds, chopped garlic, and onions; sauté until golden. 3. Add tomatoes, cook until soft, then pour the tempering over the dal and simmer."
    },
    {
        "name": "Dal Makhani",
        "serving_size": "1 bowl (200g)",
        "ingredients_text": "50g Black Urad Dal (Whole), 15g Rajma (Red Kidney Beans), 10g Butter, 10g cream, 20g Tomato, salt and spices to taste",
        "instructions": "1. Soak and cook black lentils and kidney beans until completely soft. 2. In a pan, heat butter, add tomato puree and spices, then mix with the cooked lentils. 3. Simmer for 15 minutes, stir in cream, and serve hot."
    },
    {
        "name": "Sambar",
        "serving_size": "1 bowl (200g)",
        "ingredients_text": "40g Toor Dal (Split Pigeon Peas), 60g mixed vegetables (drumstick, pumpkin, okra), 5g Sunflower Oil, 10g tamarind pulp, salt and sambar powder to taste",
        "instructions": "1. Cook toor dal until soft and mash. 2. In a pot, sauté vegetables with sambar powder and tamarind pulp. 3. Add the mashed dal and water, simmer until vegetables are tender."
    },
    {
        "name": "Rajma Masala",
        "serving_size": "1 bowl (200g)",
        "ingredients_text": "60g Rajma (Red Kidney Beans), 10g Sunflower Oil, 30g Onion, 30g Tomato, 5g ginger-garlic paste, salt and spices to taste",
        "instructions": "1. Soak and cook kidney beans until soft. 2. Sauté onions, ginger-garlic paste, tomatoes, and spices in a pan with oil. 3. Add cooked beans and simmer for 15 minutes for flavors to meld."
    },
    {
        "name": "Chole Masala",
        "serving_size": "1 bowl (200g)",
        "ingredients_text": "60g Kabuli Chana (White Chickpeas), 10g Sunflower Oil, 30g Onion, 30g Tomato, 5g ginger-garlic paste, salt and spices to taste",
        "instructions": "1. Soak and cook chickpeas until soft. 2. Sauté onions, ginger-garlic paste, tomatoes, and spices in a pan with oil. 3. Add cooked chickpeas and simmer on low heat for 15 minutes."
    },
    {
        "name": "Paneer Butter Masala",
        "serving_size": "1 bowl (200g)",
        "ingredients_text": "80g Paneer, 10g Butter, 10g cream, 30g Tomato, 20g Onion, 5g Cashew Nuts, salt and spices to taste",
        "instructions": "1. Sauté onions, cashews, and tomatoes, then blend into a smooth paste. 2. Heat butter in a pan, cook the paste, add cream and spices. 3. Mix in cubed paneer and simmer for 5 minutes."
    },
    {
        "name": "Palak Paneer",
        "serving_size": "1 bowl (200g)",
        "ingredients_text": "100g raw spinach, 80g Paneer, 10g Sunflower Oil, 20g Onion, 5g ginger-garlic paste, salt and spices to taste",
        "instructions": "1. Blanch spinach in hot water, then blend into a smooth puree. 2. In a pan, heat oil, sauté onions and ginger-garlic paste. 3. Add spinach puree and spices, mix in cubed paneer, and simmer for 5 minutes."
    },
    {
        "name": "Aloo Gobi",
        "serving_size": "1 bowl (200g)",
        "ingredients_text": "80g Potato, 100g cauliflower, 10g Sunflower Oil, 20g Onion, 20g Tomato, salt and spices to taste",
        "instructions": "1. Sauté potato and cauliflower cubes with spices in oil. 2. Add a splash of water, cover, and cook on low heat until tender. 3. Garnish with fresh coriander and serve."
    },
    {
        "name": "Chicken Curry (home style)",
        "serving_size": "1 bowl (250g)",
        "ingredients_text": "150g Raw Chicken Breast, 10g Sunflower Oil, 40g Onion, 30g Tomato, 5g ginger-garlic paste, salt and spices to taste",
        "instructions": "1. Sauté onions, ginger-garlic paste, and spices in oil until golden. 2. Add chicken pieces and cook until lightly browned. 3. Add chopped tomatoes and water, cover, and simmer until chicken is fully cooked."
    },
    {
        "name": "Butter Chicken",
        "serving_size": "1 bowl (250g)",
        "ingredients_text": "150g Raw Chicken Breast, 15g Butter, 10g cream, 40g Tomato, 20g Buffalo Curd (Dahi), 5g Cashew Nuts, salt and spices to taste",
        "instructions": "1. Marinate chicken in curd and spices, then sauté until cooked. 2. Prepare a rich gravy by cooking tomato puree, butter, cashew paste, and cream. 3. Combine the chicken with the gravy and simmer for 5 minutes."
    },
    {
        "name": "Egg Curry",
        "serving_size": "1 bowl (200g)",
        "ingredients_text": "2 Whole Egg, 10g Sunflower Oil, 30g Onion, 30g Tomato, 5g ginger-garlic paste, salt and spices to taste",
        "instructions": "1. Boil and peel eggs, prick them with a fork. 2. Sauté onions, ginger-garlic paste, and tomatoes with spices in oil until soft. 3. Add water, bring to a simmer, add eggs, and cook for 5 minutes."
    },
    {
        "name": "Plain Dosa",
        "serving_size": "1 piece (80g)",
        "ingredients_text": "60g raw rice, 15g raw urad dal, 5g Sunflower Oil",
        "instructions": "1. Soak rice and urad dal overnight, then grind to a smooth batter. 2. Ferment the batter for 8 hours or overnight. 3. Spread batter on a hot griddle, drizzle oil, and cook until crispy and golden."
    }
]

def get_embedding(text: str):
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=[text]
    )
    return response.data[0].embedding

def seed_staples():
    print("Ensuring database tables exist...")
    SQLModel.metadata.create_all(engine)
    
    print(f"Preparing {len(staple_recipes)} staple records...")
    db_records = []
    for item in staple_recipes:
        print(f"  Generating embedding for: '{item['name']}'...")
        embedding = get_embedding(item["name"])
        
        record = Staple(
            name=item["name"],
            serving_size=item["serving_size"],
            ingredients_text=item["ingredients_text"],
            instructions=item["instructions"],
            embedding=embedding
        )
        db_records.append(record)
        
    print("Seeding records into table 'staples'...")
    with Session(engine) as session:
        # Clear existing entries
        session.exec(delete(Staple))
        session.commit()
        
        # Add all and commit
        session.add_all(db_records)
        session.commit()
        
    print("Successfully seeded staples table!")

if __name__ == "__main__":
    seed_staples()
