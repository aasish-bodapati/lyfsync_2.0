# Architectural Analysis: RAG Meal Parser Failures & System-Level Solutions

This document outlines the root causes behind edge-case failures in the current RAG meal parsing engine and details the system-level solutions required to achieve state-of-the-art accuracy without brittle prompting.

---

## 1. The Cheesecake Bug: Retrieval Failure

### 🔍 Diagnosis
*   **The Log:** `"A bite of cheesecake."`
*   **The Behavior:** Resolved to `100g Cheese, cheddar` (totaling **408 kcal**).
*   **The Cause:** Cheesecake is a complex cooked dessert. Because it does not exist in the 178 `staples` table, the search fell back to the raw tables (`usda_raw`/`icmr_raw`). In the raw table, the closest semantic vector was `"Cheese, cheddar"` (matching on the word `"cheese"`). 
*   **Classification:** **Retrieval Failure**. The NLU engine parsed the request correctly, but the search database failed to supply a nutritionally matching template.

### 🛠️ Systemic Fixes
Rather than hardcoding LLM prompt overrides, we solve this by refining the taxonomy and fallback boundaries:
1.  **Decompose Cooked Desserts/Baked Goods:** Update the Stage 1 NLU instructions to classify and decompose *any* cooked preparation (including desserts, pastries, and baked goods) into raw ingredients (e.g., `"cheesecake"` $\rightarrow$ `cream cheese`, `sugar`, `graham crackers`, `butter`), instead of allowing them to fall back whole into raw tables.
2.  **Distance-Gated Fallback Rejection:** Implement a maximum cosine distance threshold for raw table matches (e.g., if distance > `0.40`). If the closest raw match is too distant, reject the match and force the NLU engine to decompose the item rather than mapping it to an unrelated raw commodity.

---

## 2. The Fries Bug: Missing Serving-Size Priors

### 🔍 Diagnosis
*   **The Log:** `"Shared fries with three people."`
*   **The Behavior:** Resolved to **364 kcal** (the calories of a full `100g` standard portion).
*   **The Cause:** The database raw table template for fries has a default `100g` baseline. The LLM has no prior knowledge of what a standard "medium portion of fries" or "a standard order" weighs. Without this serving-size prior, the LLM cannot divide the portion correctly by 4.
*   **Classification:** **Missing Serving-Size Priors**. The parser and scaling logic are correct, but they lack the reference metadata needed to perform the scaling.

### 🛠️ Systemic Fixes
We must enrich our raw database schema with portion metadata:
1.  **Serving-Size Metadata (Priors):** Extend the `USDARaw` and `ICMRRaw` schemas to store standard portion-to-weight conversions (e.g., `1 medium serving = 117g`, `1 cup = 85g`), sourced from USDA `food_portion.csv`.
2.  **Grounded Portion Context:** In Stage 2 (Retrieval), supply the portion metadata in the grounding templates context:
    > `Fries, raw (1 serving = 117g)`
3.  **Accurate Scaling:** With the serving-size prior present, the Stage 3 LLM can execute the division mathematically:
    $$\frac{117\text{g} \text{ (standard portion)}}{4 \text{ (people)}} = 29.25\text{g}$$

---

## 🎯 Strategic Summary
By resolving these errors at the **database metadata** and **retrieval taxonomy** layers rather than patching them with prompt heuristics, we maintain a clean codebase while building a highly scalable and robust conversational tracking system.
