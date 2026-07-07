# Knowledge Audit Report

> Generated automatically by `audit_failures.py`. Each row is an engineering task.

## Failure Summary by Category

| Category | Count |
| --- | --- |
| macro_error | 31 |
| missing_serving | 4 |
| **Total Failures** | **35** |

## Actionable Tickets

| Case | Input | Category | Description | Error % | Expected | Predicted |
| --- | --- | --- | --- | --- | --- | --- |
| L3_002 | `Fried 2 eggs in 10g butter` | **macro_error** | Converter succeeded but calorie error is 1484% — check density value or DB retrieval | 1483.7% | 221.0 kcal | 3500 kcal |
| L4_004 | `Omelette made with 3 eggs, 50g spinach, 20g cheese` | **macro_error** | Converter succeeded but calorie error is 1067% — check density value or DB retrieval | 1066.7% | 300.0 kcal | 3500 kcal |
| L5_003 | `Ate 1/3 of a 12 inch cheese pizza` | **macro_error** | Converter succeeded but calorie error is 821% — check density value or DB retrieval | 821.1% | 380.0 kcal | 3500 kcal |
| L4_002 | `2 plain rotis with 150g palak paneer` | **macro_error** | Converter succeeded but calorie error is 678% — check density value or DB retrieval | 677.8% | 450.0 kcal | 3500 kcal |
| L1_118 | `half a banana` | **macro_error** | Converter succeeded but calorie error is 548% — check density value or DB retrieval | 547.6% | 52.5 kcal | 340 kcal |
| L1_119 | `sliced banana` | **macro_error** | Converter succeeded but calorie error is 548% — check density value or DB retrieval | 547.6% | 105.0 kcal | 680 kcal |
| L2_002 | `Two eggs.` | **macro_error** | Converter succeeded but calorie error is 487% — check density value or DB retrieval | 486.7% | 150.0 kcal | 880 kcal |
| L1_117 | `2 large bananas` | **macro_error** | Converter succeeded but calorie error is 462% — check density value or DB retrieval | 461.8% | 242.1 kcal | 1360 kcal |
| L7_002 | `Plain dosa but with extra ghee` | **macro_error** | Converter succeeded but calorie error is 449% — check density value or DB retrieval | 448.9% | 250.0 kcal | 1372 kcal |
| L1_120 | `100g cooked white rice` | **macro_error** | Converter succeeded but calorie error is 317% — check density value or DB retrieval | 316.5% | 130.0 kcal | 541 kcal |
| L1_122 | `1 cup cooked white rice` | **macro_error** | Converter succeeded but calorie error is 274% — check density value or DB retrieval | 273.7% | 205.4 kcal | 768 kcal |
| L1_123 | `half cup cooked rice` | **macro_error** | Converter succeeded but calorie error is 261% — check density value or DB retrieval | 261.4% | 102.7 kcal | 371 kcal |
| L1_121 | `200g cooked rice` | **macro_error** | Converter succeeded but calorie error is 246% — check density value or DB retrieval | 246.2% | 260.0 kcal | 900 kcal |
| L4_001 | `150g rice, 100g dal tadka, and a small cucumber` | **macro_error** | Converter succeeded but calorie error is 236% — check density value or DB retrieval | 235.5% | 320.0 kcal | 1074 kcal |
| L6_002 | `A tiny sliver of chocolate cake` | **macro_error** | Converter succeeded but calorie error is 156% — check density value or DB retrieval | 156.4% | 150.0 kcal | 385 kcal |
| L1_106 | `rolled oats` | **macro_error** | Converter succeeded but calorie error is 150% — check density value or DB retrieval | 150.1% | 152.6 kcal | 382 kcal |
| L1_107 | `raw oats` | **macro_error** | Converter succeeded but calorie error is 150% — check density value or DB retrieval | 150.1% | 152.6 kcal | 382 kcal |
| L1_108 | `steel cut oats` | **macro_error** | Converter succeeded but calorie error is 150% — check density value or DB retrieval | 149.8% | 152.6 kcal | 381 kcal |
| L6_003 | `Two handfuls of roasted peanuts` | **macro_error** | Converter succeeded but calorie error is 113% — check density value or DB retrieval | 112.6% | 350.0 kcal | 744 kcal |
| L12_001 | `I ordered 4 idlis and vada, but I didn't eat the vada.` | **macro_error** | Converter succeeded but calorie error is 100% — check density value or DB retrieval | 100.0% | 240.0 kcal | 0 kcal |
| L9_002 | `2 slices of pepperoni pizza and 2 samosas` | **macro_error** | Converter succeeded but calorie error is 90% — check density value or DB retrieval | 89.8% | 1000.0 kcal | 1898 kcal |
| L14_002 | `Crushed 3 scoops of whey after hitting PRs, light weight baby` | **macro_error** | Converter succeeded but calorie error is 80% — check density value or DB retrieval | 79.9% | 360.0 kcal | 72 kcal |
| L7_001 | `A glass of milk but make it skim` | **macro_error** | Converter succeeded but calorie error is 69% — check density value or DB retrieval | 69.4% | 85.0 kcal | 144 kcal |
| L14_001 | `Devoured a massive plate of biryani, absolutely zero regrets` | **macro_error** | Converter succeeded but calorie error is 63% — check density value or DB retrieval | 63.5% | 800.0 kcal | 292 kcal |
| L6_001 | `A huge plate of chicken biryani` | **macro_error** | Converter succeeded but calorie error is 58% — check density value or DB retrieval | 58.3% | 700.0 kcal | 292 kcal |
| L9_001 | `150g dal makhani with a side of 100g french fries` | **macro_error** | Converter succeeded but calorie error is 46% — check density value or DB retrieval | 45.8% | 450.0 kcal | 656 kcal |
| L11_001 | `Finished about two thirds of my 300g chicken breast.` | **macro_error** | Converter succeeded but calorie error is 35% — check density value or DB retrieval | 35.2% | 332.0 kcal | 215 kcal |
| L1_111 | `100g cooked chicken breast` | **macro_error** | Converter succeeded but calorie error is 35% — check density value or DB retrieval | 34.8% | 165.0 kcal | 108 kcal |
| L1_112 | `50g cooked chicken` | **macro_error** | Converter succeeded but calorie error is 35% — check density value or DB retrieval | 34.8% | 82.5 kcal | 54 kcal |
| L1_114 | `half a pound cooked chicken` | **macro_error** | Converter succeeded but calorie error is 35% — check density value or DB retrieval | 34.6% | 372.9 kcal | 244 kcal |
| L12_002 | `Made a tuna sandwich. Ate the tuna, threw the bread to the birds.` | **macro_error** | Converter succeeded but calorie error is 32% — check density value or DB retrieval | 32.1% | 150.0 kcal | 102 kcal |
| L8_001 | `A cheeseburger but I threw away the buns` | **missing_serving** | Non-standard unit 'leaf' for 'lettuce' — add to ReferenceServing or whole_object_weights.json | 482.1% | 350.0 kcal | 2037 kcal |
| L2_003 | `1 medium banana` | **missing_serving** | Non-standard unit 'medium' for 'Banana' — add to ReferenceServing or whole_object_weights.json | 100.0% | 105.0 kcal | 0 kcal |
| L8_002 | `A plate of spaghetti bolognese, but I only ate the meat sauce` | **missing_serving** | Non-standard unit 'portion' for 'ground beef' — add to ReferenceServing or whole_object_weights.json | 100.0% | 250.0 kcal | 0 kcal |
| L1_116 | `1 medium banana` | **missing_serving** | Non-standard unit 'medium' for 'Banana' — add to ReferenceServing or whole_object_weights.json | 100.0% | 105.0 kcal | 0 kcal |

## Next Steps

- **missing_density**: Add the food to `backend/data/food_density.json`
- **missing_serving**: Add a row to the `reference_servings` DB table via `scripts/seed_reference_servings.py`
- **missing_whole**: Add the object to `backend/data/whole_object_weights.json`
- **macro_error**: Verify density value is correct, or check the embedding retrieval for this ingredient
- **retrieval_mismatch**: Verify the food is in the USDA/ICMR database or add it
