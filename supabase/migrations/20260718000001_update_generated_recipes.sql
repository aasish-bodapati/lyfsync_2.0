-- 1. Add lease_expires_at to generated_recipe_candidates
ALTER TABLE generated_recipe_candidates 
ADD COLUMN IF NOT EXISTS lease_expires_at TEXT;

-- 2. Add cuisine to recipes
ALTER TABLE recipes 
ADD COLUMN IF NOT EXISTS cuisine TEXT;

-- 3. Drop the now-obsolete lock table
DROP TABLE IF EXISTS recipe_generation_locks;
