-- Create generated_recipe_candidates table
CREATE TABLE IF NOT EXISTS generated_recipe_candidates (
    id SERIAL PRIMARY KEY,
    normalized_dish_name TEXT NOT NULL UNIQUE,
    ingredients_json TEXT NOT NULL,
    calories DOUBLE PRECISION NOT NULL,
    protein DOUBLE PRECISION NOT NULL,
    carbs DOUBLE PRECISION NOT NULL,
    fat DOUBLE PRECISION NOT NULL,
    typical_serving_grams DOUBLE PRECISION NOT NULL,
    model_version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_generated_recipe_candidates_normalized_dish_name 
ON generated_recipe_candidates (normalized_dish_name);

-- Create recipe_generation_logs table
CREATE TABLE IF NOT EXISTS recipe_generation_logs (
    id SERIAL PRIMARY KEY,
    normalized_dish_name TEXT NOT NULL,
    status TEXT NOT NULL,
    error_message TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_recipe_generation_logs_normalized_dish_name 
ON recipe_generation_logs (normalized_dish_name);

-- Table to lock concurrent requests
CREATE TABLE IF NOT EXISTS recipe_generation_locks (
    normalized_dish_name TEXT PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
