from typing import List

EXTRACT_DISHES_SYSTEM_PROMPT = (
    "You are a precise food diary parser. Extract the distinct cooked dishes or raw food items "
    "mentioned in the user's log, along with their portion size/quantity.\n\n"
    "NEGATION RULE (apply FIRST):\n"
    "- If the user explicitly states they did NOT eat, threw away, skipped, or avoided a specific item, "
    "DO NOT include that item in the output at all. Only include items that were actually consumed.\n"
    "- Examples: 'I had a sandwich but threw the bread to the birds' -> only extract the filling. "
    "'I ordered idlis and vada but didn't eat the vada' -> only extract the idlis.\n\n"
    "CLASSIFICATION RULE:\n"
    "- Set `is_cooked_dish` to True if the item is a cooked preparation, recipe, or staple made from multiple ingredients "
    "(e.g., roti, dal tadka, chicken curry, pasta, lasagna, paratha, omelette, dosa).\n"
    "- Set `is_cooked_dish` to False if the item is a single raw agricultural commodity, fruit, vegetable, or simple ingredient "
    "(e.g., banana, raw almonds, avocado, milk, raw spinach, jaggery).\n\n"
    "DECOMPOSITION RULES:\n"
    "1. If a logged item contains multiple distinct components cooked or served together "
    "(e.g., 'rice and chicken curry', 'roti with paneer'), decompose them into separate items "
    "(e.g., split 'roti with paneer' into 'roti' and 'paneer').\n"
    "2. If a logged cooked dish is a complex multi-ingredient meal (such as lasagna, pizza, tacos, burritos, pasta with sauce, sandwiches) "
    "and is not a standard simple staple, decompose it into its primary constituent raw ingredients "
    "(e.g., decompose 'beef lasagna' into 'ground beef', 'pasta sheets', 'tomato sauce', and 'mozzarella cheese')."
)

PARSE_PORTIONS_SYSTEM_PROMPT = (
    "You are a precise nutrition NLP parser. Extract the structured portion data (quantity, unit, state) for all consumed foods. "
    "Decompose complex cooked dishes into raw ingredients. DO NOT GUESS GRAM WEIGHTS unless explicitly stated by the user."
)

GENERATE_RECIPE_SYSTEM_PROMPT = "You are a precise, research-backed global nutrition and recipe database generator."

JUDGE_RECIPE_SYSTEM_PROMPT = "You are the head judge of a nutrition AI jury. Synthesize the drafts into one perfect golden baseline recipe."


def build_portion_prompt(text: str, nodes: List[any], grounding_context: dict) -> str:
    """Formats the grounding context and user input into the LLM portion parsing prompt."""
    context_lines = []
    for i, node in enumerate(nodes):
        temp = grounding_context.get(node.original_name)
        if not temp: continue
        is_fallback = temp["template_type"] in ("raw", "unmatched_cooked")
        context_lines.append(
            f"Source Index {i} - '{node.original_name}':\n"
            f"  Portion baseline: {temp['serving_size']}\n"
            f"  Raw Ingredients: {temp['ingredients_text']}\n"
            f"  Cooking Steps: {temp['instructions']}\n"
            f"  Metadata: is_cooked_dish={node.is_cooked_dish}, is_fallback={is_fallback}, template_type={temp['template_type']}"
        )
    templates_context = "\n\n".join(context_lines)
    return (
        f"User logged: \"{text}\"\n\n"
        f"REFERENCE DATABASE TEMPLATES:\n"
        f"{templates_context}\n\n"
        "INSTRUCTIONS:\n"
        "1. Categorize the meal (breakfast, lunch, dinner, or snack).\n"
        "2. For each food item the user consumed, extract the structured portion details: food_name, quantity, unit, state, and quantifier_type.\n"
        "   - You MUST link each component back to its original item via `source_index`.\n"
        "3. RULES FOR DECOMPOSITION:\n"
        "   - If a dish matches a staple template (e.g. 'masala oats', 'palak paneer'), decompose it into its raw ingredients based on the template.\n"
        "   - If a food item is 'unmatched_cooked', you MUST decompose it into its standard raw ingredients.\n"
        "   - Output a ParsedComponent object for EACH component raw ingredient, all sharing the same `source_index` as the parent dish.\n"
        "   - Do NOT include water or salt.\n"
        "4. RULES FOR QUANTITY AND UNIT:\n"
        "   - DO NOT CONVERT TO GRAMS unless the user explicitly stated grams.\n"
        "   - Extract the exact numeric quantity and the standard unit string (e.g., 'g', 'ml', 'cup', 'tbsp', 'tsp', 'piece', 'slice', 'handful', 'scoop', 'plate', 'bowl', 'pizza_whole', 'cake_whole').\n"
        "   - If the user specifies a fraction of a whole object (e.g., '1/3 of a 12 inch pizza'), use quantity = 0.333 and unit = 'pizza_whole'.\n"
        "   - If decomposing a dish based on a user's fraction (e.g. '1/3 of a pizza' -> dough, cheese), the quantity for EACH raw ingredient should reflect that fraction (e.g. quantity=0.333, unit='pizza_whole').\n"
        "5. RULES FOR STATE AND QUANTIFIER_TYPE:\n"
        "   - state MUST be one of: 'raw', 'cooked', 'unknown'. If not explicitly mentioned, use 'unknown'.\n"
        "   - quantifier_type MUST be 'explicit' if the user gave an exact number (e.g. '200g', '2 eggs', 'half a cup').\n"
        "   - quantifier_type MUST be 'vague' if the user was imprecise (e.g. 'some', 'a bit of', 'a plate of').\n"
    )

JURY_GENERATION_PROMPT_TEMPLATE = (
    "Generate standard recipe and raw ingredient list for the following dish:\n"
    "{dish_name}\n\n"
    "CRITICAL STAPLE & BASE RULES:\n\n"
    "1. THE GOLDEN BASELINE RULE:\n"
    "   - Make the recipe as standard, simple, and generic as possible so that it represents the GOLDEN BASELINE / GOLDEN AVERAGE of the dish.\n"
    "   - Avoid local variations, specialty recipes, or fancy restaurant-style versions.\n"
    "   - Focus exclusively on the core, staple ingredients that dictate the baseline caloric and macronutrient structure of the dish.\n\n"
    "2. AVERAGE KITCHEN INGREDIENTS:\n"
    "   - Use only raw, fundamental ingredients that you would find in an average home kitchen (e.g., raw meats, basic dairy like milk/cheese/cream/butter/sour cream, raw vegetables, standard grains, and common oils/fats).\n"
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

def build_jury_judge_prompt(dish_name: str, drafts_text: str) -> str:
    return (
        f"We need the ultimate golden baseline recipe for '{dish_name}'.\n\n"
        f"Here are 3 independent drafts generated by our baseline recipe AI:\n\n"
        f"{drafts_text}\n\n"
        "INSTRUCTIONS:\n"
        "1. Analyze the 3 drafts. Identify the most statistically sound, common-sense golden baseline values.\n"
        "2. If one draft hallucinates a weird ingredient (e.g., cashews in basic dal), ignore it.\n"
        "3. Average or pick the most credible ingredient weights and portion sizes.\n"
        "4. Output the final, synthesized golden baseline recipe."
    )
