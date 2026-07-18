import os
import json
import openai
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()
client = openai.OpenAI()

class EvalExample(BaseModel):
    input: str
    slice: str = Field(description="Must be one of: INDIAN_MIXED, HINGLISH, VAGUE_PORTION, RECIPE, SNACK, RAW_INGREDIENT")
    expected_items: list[str]
    expected_quantities: list[float]
    expected_units: list[str]
    expected_raw_or_cooked: list[str] = Field(description="Each must be 'raw' or 'cooked'")
    expected_needs_clarification: bool

class EvalDataset(BaseModel):
    examples: list[EvalExample]

PROMPT = """
Generate 70 highly diverse, realistic, and occasionally vague user logs for a nutrition tracking app tailored to an Indian audience.
Include cases of:
- Hinglish (e.g. 'subah 2 ande khaye')
- Vague portions ('thoda sa chawal', 'one plate', 'a handful')
- Complex Indian Mixed Dishes (e.g., 'paneer butter masala', 'chicken biryani', 'masala dosa')
- Raw ingredients ('200g raw chicken breast', '1 scoop whey')
- Snacks ('namkeen', 'chai', 'samosa')
- Combinations (e.g. '1 bowl dal with 2 roti and some rice')
- Explicit gram overrides ('500g of biryani')
- ML volumes ('250ml milk', '1 glass juice')
- Prepared atomic foods ('grilled chicken', 'boiled eggs')

For each, provide the exact expected extraction outputs following these rules:
1. expected_items: The name of the item. Do NOT include dish names if ingredients are explicitly listed. Do NOT translate Indian names to English (e.g., keep 'paneer', do not use 'cheese').
2. expected_quantities: float
3. expected_units: normalized strings (e.g., 'piece', 'bowl', 'plate', 'grams', 'ml', 'roti', 'cup')
4. expected_raw_or_cooked: 'raw' or 'cooked'. Mixed dishes and prepared foods (like 'grilled chicken') are 'cooked'. Raw ingredients are 'raw'.
5. expected_needs_clarification: true if vague (e.g. 'a lot', 'some', 'alien food'), else false.
"""

def generate_examples():
    print("Requesting 70 synthetic examples from GPT-4o...")
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[{"role": "user", "content": PROMPT}],
        response_format=EvalDataset,
        temperature=0.7
    )
    
    new_examples = completion.choices[0].message.parsed.examples
    
    dataset_path = "backend/tests/eval_dataset.json"
    with open(dataset_path, "r") as f:
        existing = json.load(f)
        
    for ex in new_examples:
        existing.append(ex.model_dump())
        
    with open(dataset_path, "w") as f:
        json.dump(existing, f, indent=2)
        
    print(f"Successfully appended {len(new_examples)} examples. Total: {len(existing)}")

if __name__ == "__main__":
    generate_examples()
