# LyfSync SOTA Benchmark Report v3.0

## 1. NLP & Pipeline Accuracy

| Metric | Score |
| --- | --- |
| Ingredient Extraction | 100.0% |
| Cooking State Resolution | N/A |
| Unit Recognition | N/A |
| Unit->Grams Accuracy | 52.8% |
| Canonical ID Mapping | N/A |

## 2. Latency (Percentiles)

| Stage | P50 (ms) | P95 (ms) | P99 (ms) |
| --- | --- | --- | --- |
| extraction | 926.8 | 1572.7 | 2826.2 |
| templates | 1079.4 | 2911.3 | 7148.9 |
| parse_portions | 1453.8 | 3798.3 | 14016.6 |
| conversion | 0.0 | 639.4 | 985.3 |
| db_lookup | 1000.2 | 6706.2 | 9637.6 |

## 3. Nutrition Engine Accuracy (Calorie Error Bands)

Total Cases: 55

| Error Band | Count | % |
| --- | --- | --- |
| Excellent (<5%) | 16 | 29.1% |
| Good (5-10%) | 0 | 0.0% |
| Acceptable (10-20%) | 1 | 1.8% |
| Poor (20-30%) | 3 | 5.5% |
| Fail (>30%) | 35 | 63.6% |
