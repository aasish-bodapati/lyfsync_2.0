# LyfSync Bug & Resolution Log

This document serves as a centralized log of all major systemic problems, data anomalies, and architectural failures encountered during the development of LyfSync, along with how they were resolved.

---

## 1. The "Cheesecake" Bug (Retrieval Failure)

*   **Symptom:** Logging `"A bite of cheesecake."` resolved to `100g Cheese, cheddar` (totaling 408 kcal).
*   **Root Cause:** Cheesecake is a complex cooked dessert not present in the small 178-item `staples` database. The vector search fell back to the raw tables, where the closest semantic match was `"Cheese, cheddar"`.
*   **Resolution:** 
    1. Implemented a **distance-gated fallback rejection** (`best_db_dist > 0.35` / `0.75` for dev). If a raw match is too semantically distant, the system rejects it and forces the LLM to decompose the dish into raw ingredients.
    2. Updated NLU instructions to explicitly decompose baked goods and desserts into constituent raw ingredients (flour, sugar, butter, etc.) if they lack a database match.

## 2. The "Fries" Bug & "Egg" Problem (Missing Serving-Size Priors)

*   **Symptom:** 
    * Logging `"Shared fries with three people."` resolved to a full 100g standard portion (failed to divide by 4).
    * Logging `"Two eggs"` resolved to 296 kcal (assumed 1 egg = 100g).
*   **Root Cause:** The database raw templates default to a 100g baseline. The LLM has no prior knowledge of what a standard "medium order of fries" or "one large egg" weighs, causing it to fall back to generic or mathematically flawed scaling heuristics.
*   **Resolution:** 
    1. Extracted 311 unique portion metadata priors (e.g., `1 egg = 53g`, `1 cup milk = 244g`) directly from the USDA `food_portion.csv` dataset.
    2. Seeded these into a new `portion_priors` Supabase table.
    3. Injected these priors directly into the RAG context, mathematically anchoring the LLM's natural language understanding to real-world serving weights.

## 3. The Supabase IPv6 Connection Refusal

*   **Symptom:** Connecting to `db.[ref].supabase.co:5432` from local scripts resulted in connection timeouts/refusals.
*   **Root Cause:** The Supabase Free Plan deprecates IPv4 direct connections in favor of IPv6-only. The local development network lacked IPv6 routing.
*   **Resolution:** Switched all database URLs to use the Supabase Connection Pooler (`aws-0-[region].pooler.supabase.com:6543`), which safely resolves to IPv4 and supports local execution.

## 4. IndianFoodDatasetCSV Data Anomalies

*   **Symptom:** Naive CSV parsing of the recipe dataset caused row fragmentation, missing ingredients, and UI rendering bugs.
*   **Root Cause:** 
    1. Recipes contained embedded newlines inside double quotes.
    2. Exactly 6 recipes had entirely empty ingredient fields.
    3. Over 6,400 rows contained the HTML non-breaking space character (`\xa0`).
*   **Resolution:** Used Python's robust `csv` parser (or `pandas`) to handle embedded newlines, dropped rows with missing ingredients, and explicitly replaced `\xa0` with standard spaces during the EDA and database ingestion pipelines.

## 5. ICMR vs USDA Geopolitical Macro Gap

*   **Symptom:** When benchmarking `"200g chicken breast"`, the system predicted 215 kcal instead of the USDA gold standard 332 kcal.
*   **Root Cause:** The vector search hit the Indian `ICMRRaw` database first. Indian livestock is structurally leaner than American factory-farmed livestock, meaning the baseline calories for 100g of chicken differ drastically between regions.
*   **Resolution:** This is considered an intended feature, not a bug. LyfSync respects regional dietary baselines. However, for benchmarking purposes, tests must be explicitly calibrated to either US or IN standards.
