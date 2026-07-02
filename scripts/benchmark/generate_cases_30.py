import json
import os

cases = [
    # ---- TIER 1: EASY (Levels 1-2, Exact gram weights + basic NL) ----
    {
        "id": "L1_001", "level": 1, "level_name": "Basic",
        "input": "100g raw oats",
        "gold_standard": {"calories": 381.63, "protein": 13.5, "carbs": 68.7, "fat": 5.89},
        "tolerance": {"calorie_pct": 5, "protein_pct": 5, "carbs_pct": 5, "fat_pct": 5}
    },
    {
        "id": "L1_002", "level": 1, "level_name": "Basic",
        "input": "200g chicken breast",
        "gold_standard": {"calories": 332.0, "protein": 64.2, "carbs": 0.0, "fat": 6.48},
        "tolerance": {"calorie_pct": 5, "protein_pct": 5, "carbs_pct": 5, "fat_pct": 5}
    },
    {
        "id": "L2_001", "level": 2, "level_name": "Natural Language",
        "input": "A bowl of oats with 100ml milk.",
        "gold_standard": {"calories": 250.8, "protein": 10.0, "carbs": 38.9, "fat": 6.1},
        "tolerance": {"calorie_pct": 10, "protein_pct": 10, "carbs_pct": 10, "fat_pct": 10}
    },
    {
        "id": "L2_002", "level": 2, "level_name": "Natural Language",
        "input": "Two eggs.",
        "gold_standard": {"calories": 150.0, "protein": 12.3, "carbs": 0.9, "fat": 10.3},
        "tolerance": {"calorie_pct": 10, "protein_pct": 10, "carbs_pct": 10, "fat_pct": 10}
    },
    {
        "id": "L2_003", "level": 2, "level_name": "Natural Language",
        "input": "1 medium banana",
        "gold_standard": {"calories": 105.0, "protein": 1.3, "carbs": 27.0, "fat": 0.4},
        "tolerance": {"calorie_pct": 10, "protein_pct": 10, "carbs_pct": 10, "fat_pct": 10}
    },
    {
        "id": "L2_004", "level": 2, "level_name": "Natural Language",
        "input": "150g cooked white rice",
        "gold_standard": {"calories": 195.0, "protein": 4.0, "carbs": 42.0, "fat": 0.4},
        "tolerance": {"calorie_pct": 10, "protein_pct": 10, "carbs_pct": 10, "fat_pct": 10}
    },

    # ---- TIER 2: MODERATE (Levels 3-4, Cooking methods, multi-item) ----
    {
        "id": "L3_001", "level": 3, "level_name": "Cooking Methods",
        "input": "Chicken breast cooked in a tablespoon of olive oil. 200g chicken.",
        "gold_standard": {"calories": 455.7, "protein": 64.2, "carbs": 0.0, "fat": 20.4},
        "tolerance": {"calorie_pct": 10, "protein_pct": 10, "carbs_pct": 10, "fat_pct": 10}
    },
    {
        "id": "L3_002", "level": 3, "level_name": "Cooking Methods",
        "input": "Fried 2 eggs in 10g butter",
        "gold_standard": {"calories": 221.0, "protein": 12.4, "carbs": 0.9, "fat": 18.4},
        "tolerance": {"calorie_pct": 10, "protein_pct": 10, "carbs_pct": 10, "fat_pct": 10}
    },
    {
        "id": "L4_001", "level": 4, "level_name": "Multi-Item",
        "input": "150g rice, 100g dal tadka, and a small cucumber",
        "gold_standard": {"calories": 320.0, "protein": 10.0, "carbs": 58.0, "fat": 4.5},
        "tolerance": {"calorie_pct": 15, "protein_pct": 15, "carbs_pct": 15, "fat_pct": 15}
    },
    {
        "id": "L4_002", "level": 4, "level_name": "Multi-Item",
        "input": "2 plain rotis with 150g palak paneer",
        "gold_standard": {"calories": 450.0, "protein": 14.0, "carbs": 50.0, "fat": 22.0},
        "tolerance": {"calorie_pct": 15, "protein_pct": 15, "carbs_pct": 15, "fat_pct": 15}
    },
    {
        "id": "L4_003", "level": 4, "level_name": "Multi-Item",
        "input": "A bowl of greek yogurt (200g) mixed with 30g almonds",
        "gold_standard": {"calories": 300.0, "protein": 26.0, "carbs": 12.0, "fat": 15.0},
        "tolerance": {"calorie_pct": 15, "protein_pct": 15, "carbs_pct": 15, "fat_pct": 15}
    },
    {
        "id": "L4_004", "level": 4, "level_name": "Multi-Item",
        "input": "Omelette made with 3 eggs, 50g spinach, 20g cheese",
        "gold_standard": {"calories": 300.0, "protein": 24.0, "carbs": 3.0, "fat": 21.0},
        "tolerance": {"calorie_pct": 15, "protein_pct": 15, "carbs_pct": 15, "fat_pct": 15}
    },

    # ---- TIER 3: HARD (Levels 5-6, Fractions, vague portions) ----
    {
        "id": "L5_001", "level": 5, "level_name": "Ambiguous Language",
        "input": "A little oil on my 200g chicken breast.",
        "gold_standard": {"calories": 371.7, "protein": 64.2, "carbs": 0.0, "fat": 10.9},
        "tolerance": {"calorie_pct": 15, "protein_pct": 15, "carbs_pct": 15, "fat_pct": 20}
    },
    {
        "id": "L5_002", "level": 5, "level_name": "Fractions",
        "input": "I ate exactly half of a 300g ribeye steak",
        "gold_standard": {"calories": 435.0, "protein": 37.5, "carbs": 0.0, "fat": 31.5},
        "tolerance": {"calorie_pct": 15, "protein_pct": 15, "carbs_pct": 15, "fat_pct": 15}
    },
    {
        "id": "L5_003", "level": 5, "level_name": "Fractions",
        "input": "Ate 1/3 of a 12 inch cheese pizza",
        "gold_standard": {"calories": 380.0, "protein": 15.0, "carbs": 45.0, "fat": 14.0},
        "tolerance": {"calorie_pct": 25, "protein_pct": 25, "carbs_pct": 25, "fat_pct": 25}
    },
    {
        "id": "L6_001", "level": 6, "level_name": "Vague Portions",
        "input": "A huge plate of chicken biryani",
        "gold_standard": {"calories": 700.0, "protein": 30.0, "carbs": 90.0, "fat": 20.0},
        "tolerance": {"calorie_pct": 30, "protein_pct": 30, "carbs_pct": 30, "fat_pct": 30}
    },
    {
        "id": "L6_002", "level": 6, "level_name": "Vague Portions",
        "input": "A tiny sliver of chocolate cake",
        "gold_standard": {"calories": 150.0, "protein": 2.0, "carbs": 20.0, "fat": 7.0},
        "tolerance": {"calorie_pct": 30, "protein_pct": 30, "carbs_pct": 30, "fat_pct": 30}
    },
    {
        "id": "L6_003", "level": 6, "level_name": "Vague Portions",
        "input": "Two handfuls of roasted peanuts",
        "gold_standard": {"calories": 350.0, "protein": 14.0, "carbs": 10.0, "fat": 30.0},
        "tolerance": {"calorie_pct": 30, "protein_pct": 30, "carbs_pct": 30, "fat_pct": 30}
    },

    # ---- TIER 4: EXPERT (Levels 7-9, Modifiers, Complex Staples) ----
    {
        "id": "L7_001", "level": 7, "level_name": "Modifiers",
        "input": "A glass of milk but make it skim",
        "gold_standard": {"calories": 85.0, "protein": 8.5, "carbs": 12.0, "fat": 0.2},
        "tolerance": {"calorie_pct": 15, "protein_pct": 15, "carbs_pct": 15, "fat_pct": 50}
    },
    {
        "id": "L7_002", "level": 7, "level_name": "Modifiers",
        "input": "Plain dosa but with extra ghee",
        "gold_standard": {"calories": 250.0, "protein": 4.0, "carbs": 30.0, "fat": 12.0},
        "tolerance": {"calorie_pct": 25, "protein_pct": 25, "carbs_pct": 25, "fat_pct": 30}
    },
    {
        "id": "L8_001", "level": 8, "level_name": "Deconstructed",
        "input": "A cheeseburger but I threw away the buns",
        "gold_standard": {"calories": 350.0, "protein": 25.0, "carbs": 2.0, "fat": 25.0},
        "tolerance": {"calorie_pct": 25, "protein_pct": 25, "carbs_pct": 50, "fat_pct": 25}
    },
    {
        "id": "L8_002", "level": 8, "level_name": "Deconstructed",
        "input": "A plate of spaghetti bolognese, but I only ate the meat sauce",
        "gold_standard": {"calories": 250.0, "protein": 20.0, "carbs": 10.0, "fat": 15.0},
        "tolerance": {"calorie_pct": 30, "protein_pct": 30, "carbs_pct": 40, "fat_pct": 30}
    },
    {
        "id": "L9_001", "level": 9, "level_name": "Mixed Cuisine",
        "input": "150g dal makhani with a side of 100g french fries",
        "gold_standard": {"calories": 450.0, "protein": 12.0, "carbs": 55.0, "fat": 20.0},
        "tolerance": {"calorie_pct": 20, "protein_pct": 20, "carbs_pct": 20, "fat_pct": 20}
    },
    {
        "id": "L9_002", "level": 9, "level_name": "Mixed Cuisine",
        "input": "2 slices of pepperoni pizza and 2 samosas",
        "gold_standard": {"calories": 1000.0, "protein": 35.0, "carbs": 100.0, "fat": 50.0},
        "tolerance": {"calorie_pct": 20, "protein_pct": 20, "carbs_pct": 20, "fat_pct": 20}
    },

    # ---- TIER 5: EXTREME (Levels 11-14, Sarcasm, implicit, logic) ----
    {
        "id": "L11_001", "level": 11, "level_name": "Implicit",
        "input": "Finished about two thirds of my 300g chicken breast.",
        "gold_standard": {"calories": 332.0, "protein": 64.2, "carbs": 0.0, "fat": 6.48},
        "tolerance": {"calorie_pct": 10, "protein_pct": 10, "carbs_pct": 10, "fat_pct": 10}
    },
    {
        "id": "L12_001", "level": 12, "level_name": "Logic & Negation",
        "input": "I ordered 4 idlis and vada, but I didn't eat the vada.",
        "gold_standard": {"calories": 240.0, "protein": 8.0, "carbs": 48.0, "fat": 1.0},
        "tolerance": {"calorie_pct": 25, "protein_pct": 25, "carbs_pct": 25, "fat_pct": 40}
    },
    {
        "id": "L12_002", "level": 12, "level_name": "Logic & Negation",
        "input": "Made a tuna sandwich. Ate the tuna, threw the bread to the birds.",
        "gold_standard": {"calories": 150.0, "protein": 25.0, "carbs": 0.0, "fat": 5.0},
        "tolerance": {"calorie_pct": 30, "protein_pct": 30, "carbs_pct": 50, "fat_pct": 30}
    },
    {
        "id": "L13_001", "level": 13, "level_name": "Misspellings",
        "input": "Aet a big bowwl of whaet pasta wth chikin",
        "gold_standard": {"calories": 500.0, "protein": 35.0, "carbs": 70.0, "fat": 10.0},
        "tolerance": {"calorie_pct": 30, "protein_pct": 30, "carbs_pct": 30, "fat_pct": 30}
    },
    {
        "id": "L14_001", "level": 14, "level_name": "Sarcasm & Slang",
        "input": "Devoured a massive plate of biryani, absolutely zero regrets",
        "gold_standard": {"calories": 800.0, "protein": 30.0, "carbs": 100.0, "fat": 30.0},
        "tolerance": {"calorie_pct": 30, "protein_pct": 30, "carbs_pct": 30, "fat_pct": 30}
    },
    {
        "id": "L14_002", "level": 14, "level_name": "Sarcasm & Slang",
        "input": "Crushed 3 scoops of whey after hitting PRs, light weight baby",
        "gold_standard": {"calories": 360.0, "protein": 75.0, "carbs": 9.0, "fat": 3.0},
        "tolerance": {"calorie_pct": 25, "protein_pct": 25, "carbs_pct": 30, "fat_pct": 30}
    }
]

file_path = os.path.join(os.path.dirname(__file__), "cases.json")
with open(file_path, "w") as f:
    json.dump(cases, f, indent=2)

print(f"✅ Generated 30 benchmark cases at {file_path}")
