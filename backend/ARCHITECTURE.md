# LyfSync Backend — Architecture Reference

**Last updated: July 18, 2026**

---

## Module Map

| File | Responsibility |
|---|---|
| `main.py` | FastAPI app, routing, DB engine setup, startup events |
| `schemas.py` | Pydantic models for API I/O and LLM structured output |
| `models.py` | SQLModel DB table definitions (single source of truth) |
| `nutrition_service.py` | LLM extraction, weight estimation, resolution, persistence |
| `embeddings.py` | Vector embedding calls, food/recipe name normalisation, pgvector search |
| `fallback.py` | LLM-generated recipe fallback, lease-based concurrency, rate limiting |
| `prompts.py` | LLM system prompts (meal extraction + recipe generation) |

---

## Request Flow

```
POST /api/v1/meals/parse
    │
    ▼
main.parse_meal()
    │
    ├── nutrition_service.safe_parse_text()
    │       └── LLM (gpt-4o-mini, structured output → ParsedMeal)
    │
    ├── nutrition_service.resolve_nutrition()
    │       Per item:
    │       ├── _estimate_weight()            ← conversions.json + PORTION_PRIORS
    │       ├── looks_like_mixed_dish()?
    │       │     ├── YES → embeddings.find_closest_recipe()   threshold 0.70
    │       │     │          └── miss → fallback.generate_recipe_fallback()
    │       │     └── NO  → embeddings.find_closest_food()     threshold 0.70
    │       └── returns MealItem list with source + confidence
    │
    └── nutrition_service.persist_meal()      ← single DB transaction
```

---

## Configuration & Constants

Configuration is split between external JSON files and Python constants in `nutrition_service.py`.

### External Files (Tracked in `config/`)
| File | Contents |
|---|---|
| `config/conversions.json` | Item-specific unit→gram conversions (e.g. `egg + piece = 50g`) |
| `config/aliases.json` | Indian food name → USDA search term aliases (e.g. `curd → yogurt`) |

Update these files and restart to change portion priors or aliases — no code change required.

### Internal Python Constants (`nutrition_service.py`)
While file-based overrides exist, the following base assumptions remain as Python constants:
- **Global Priors**: Default weights for units (e.g., `PORTION_PRIORS` defining `piece=80.0`, `cup=150.0`) when no item-specific match is found.
- **Atomic Food Rules**: Logic mapping parsed items to atomic foods (e.g., `is_atomic_food()`).
- **Thresholds**: Retrieval thresholds (`FOOD_SIMILARITY_THRESHOLD = 0.70`, `RECIPE_SIMILARITY_THRESHOLD = 0.70`, `HIGH_CONFIDENCE_THRESHOLD = 0.80`).

---

## Database Schema

**Production**: Supabase (PostgreSQL + pgvector).  
Schema is managed exclusively by Supabase migrations in `supabase/migrations/`.  
`SQLModel.metadata.create_all()` runs **only** in local SQLite environments (tests, dev).

### Tables

| Table | Purpose |
|---|---|
| `food_nutrition` | Atomic food reference (USDA + curated). Macros per 100g. |
| `recipes` | Curated Indian dish baselines. Macros per `typical_serving_grams`. |
| `generated_recipe_candidates` | LLM-generated recipes pending review. `lease_expires_at` controls concurrency. |
| `recipe_generation_logs` | Append-only audit log of all generation attempts. |
| `meals` | Persisted user meal logs. |
| `meal_items` | Individual food items within a meal, with provenance fields. |

---

## Retrieval Thresholds

All threshold constants live in `nutrition_service.py`:

| Constant | Value | Purpose |
|---|---|---|
| `FOOD_SIMILARITY_THRESHOLD` | 0.70 | Min cosine similarity for `food_nutrition` matches |
| `RECIPE_SIMILARITY_THRESHOLD` | 0.70 | Min cosine similarity for `recipes` matches |
| `HIGH_CONFIDENCE_THRESHOLD` | 0.80 | Score ≥ this → `_high` band; below → `_low` |

---

## Source Labels

Each resolved item carries a `source` field:

| Source | Meaning |
|---|---|
| `food_match_high` | USDA/curated food match, similarity ≥ 0.80 |
| `food_match_low` | Food match, 0.70 ≤ similarity < 0.80 |
| `recipe_match_high` | Curated recipe match, similarity ≥ 0.80 |
| `recipe_match_low` | Recipe match, 0.70 ≤ similarity < 0.80 |
| `generated_recipe` | LLM-generated recipe (always provisional, needs_clarification=True) |
| `unresolved` | No match found; macros are 0.0 |

---

## Evaluation

Evaluation and dataset scripts live in `backend/evals/` and are **never imported by the application**.  
Run them manually against a local or staging DB; never against production.
