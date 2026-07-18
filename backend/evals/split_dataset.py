import json
import os

def split_dataset():
    base_dir = os.path.dirname(__file__)
    dataset_path = os.path.join(base_dir, "tests", "macro_eval_dataset.json")
    
    with open(dataset_path, "r") as f:
        data = json.load(f)
        
    tuning_indices = [1, 2, 3, 5, 9, 12, 13, 14, 15, 18, 0, 4, 6, 7, 8]  # 0-indexed (the seeded ones + 5 others)
    heldout_indices = [i for i in range(25) if i not in tuning_indices]
    
    tuning_set = [data[i] for i in tuning_indices]
    heldout_set = [data[i] for i in heldout_indices]
    
    with open(os.path.join(base_dir, "tests", "macro_eval_tuning.json"), "w") as f:
        json.dump(tuning_set, f, indent=2)
        
    with open(os.path.join(base_dir, "tests", "macro_eval_heldout.json"), "w") as f:
        json.dump(heldout_set, f, indent=2)
        
    print(f"Split completed: {len(tuning_set)} tuning, {len(heldout_set)} held-out.")

if __name__ == "__main__":
    split_dataset()
