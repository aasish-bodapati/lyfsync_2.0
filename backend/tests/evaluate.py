import json
import os
import sys

# Add backend to path so we can import from main
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from main import safe_parse_text

def run_evals():
    dataset_path = os.path.join(os.path.dirname(__file__), "eval_dataset.json")
    with open(dataset_path, "r") as f:
        dataset = json.load(f)
        
    total_examples = len(dataset)
    correct_extractions = 0
    
    print(f"Starting Evaluation on {total_examples} examples...\n")
    
    for i, example in enumerate(dataset):
        input_text = example["input"]
        expected_items = [item.lower() for item in example["expected_items"]]
        
        try:
            parsed = safe_parse_text(input_text)
            extracted_items = [item.name.lower() for item in parsed.items]
            
            # Simple scoring: check if all expected items were found (subset)
            # or exact match. We'll check if extracted contains expected.
            success = True
            for expected in expected_items:
                if not any(expected in ext or ext in expected for ext in extracted_items):
                    success = False
                    break
                    
            if success:
                correct_extractions += 1
                print(f"[{i+1}/{total_examples}] PASS: '{input_text}' -> {extracted_items}")
            else:
                print(f"[{i+1}/{total_examples}] FAIL: '{input_text}'")
                print(f"   Expected: {expected_items}")
                print(f"   Got:      {extracted_items}")
                
        except Exception as e:
            print(f"[{i+1}/{total_examples}] ERROR on '{input_text}': {e}")
            
    accuracy = (correct_extractions / total_examples) * 100
    print(f"\nEvaluation Complete: {accuracy:.1f}% Accuracy ({correct_extractions}/{total_examples})")

if __name__ == "__main__":
    run_evals()
