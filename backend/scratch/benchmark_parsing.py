import urllib.request
import json
import time

API_URL = "http://127.0.0.1:8000/api/v1/meals/parse"

TESTS = [
    # Chicken Biryani
    {"dish": "Chicken Biryani", "level": "L1", "text": "I had a plate of chicken biryani for lunch"},
    {"dish": "Chicken Biryani", "level": "L2", "text": "I had chicken biryani for lunch, used 500g raw chicken and 200g basmati rice"},
    {"dish": "Chicken Biryani", "level": "L3", "text": "Chicken biryani: 500g chicken, 200g basmati rice, 60ml oil, 100g yogurt, 2 onions (150g), whole spices"},
    
    # Dal Makhani
    {"dish": "Dal Makhani", "level": "L1", "text": "Had a bowl of dal makhani for dinner"},
    {"dish": "Dal Makhani", "level": "L2", "text": "Dal makhani with 200g black lentils, 50g butter, and 100ml cream"},
    {"dish": "Dal Makhani", "level": "L3", "text": "Dal makhani: 200g whole urad dal, 50g rajma, 50g butter, 100ml cream, 2 tomatoes, 1 tbsp oil, spices"},
    
    # Aloo Paratha
    {"dish": "Aloo Paratha", "level": "L1", "text": "Had 2 aloo parathas for breakfast with pickle"},
    {"dish": "Aloo Paratha", "level": "L2", "text": "2 aloo parathas, each made with 60g whole wheat flour and 80g potato filling, cooked with 2 tsp ghee"},
    {"dish": "Aloo Paratha", "level": "L3", "text": "2 parathas: 120g atta, 160g boiled potato, 2 tsp cumin, 1 green chili, 20g ghee for cooking"},
    
    # Palak Paneer
    {"dish": "Palak Paneer", "level": "L1", "text": "Had palak paneer with 2 rotis for dinner"},
    {"dish": "Palak Paneer", "level": "L2", "text": "Palak paneer with 150g spinach, 100g paneer, and 2 tbsp oil"},
    {"dish": "Palak Paneer", "level": "L3", "text": "Palak paneer: 200g fresh spinach, 150g paneer, 1 onion (80g), 1 tomato (70g), 2 tbsp oil, cream, spices"},
    
    # Rajma Chawal
    {"dish": "Rajma Chawal", "level": "L1", "text": "Had a bowl of rajma chawal for lunch"},
    {"dish": "Rajma Chawal", "level": "L2", "text": "Rajma chawal: 150g dry rajma soaked overnight and 150g raw basmati rice"},
    {"dish": "Rajma Chawal", "level": "L3", "text": "Rajma chawal: 150g dry kidney beans, 150g raw rice, 1 onion (80g), 2 tomatoes (140g), 2 tbsp oil, spices"}
]

def run_tests():
    print("Running Benchmark Tests against /api/v1/meals/parse")
    print(f"{'Dish':<15} | {'Level':<5} | {'Cals':<6} | {'Prot(g)':<7} | {'Carb(g)':<7} | {'Fat(g)':<6} | {'Status'}")
    print("-" * 80)
    
    for t in TESTS:
        dish = t["dish"]
        level = t["level"]
        text = t["text"]
        
        try:
            req = urllib.request.Request(
                API_URL, 
                data=json.dumps({"text": text}).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    cal = data.get("calories", 0.0)
                    prot = data.get("protein", 0.0)
                    carb = data.get("carbs", 0.0)
                    fat = data.get("fat", 0.0)
                    print(f"{dish:<15} | {level:<5} | {cal:<6.1f} | {prot:<7.1f} | {carb:<7.1f} | {fat:<6.1f} | Success")
                else:
                    print(f"{dish:<15} | {level:<5} | {'-':<6} | {'-':<7} | {'-':<7} | {'-':<6} | Error {resp.status}")
        except Exception as e:
            print(f"{dish:<15} | {level:<5} | {'-':<6} | {'-':<7} | {'-':<7} | {'-':<6} | Failed: {str(e)[:20]}")
            
        time.sleep(1)  # brief pause to avoid hitting rate limits too fast

if __name__ == "__main__":
    run_tests()
