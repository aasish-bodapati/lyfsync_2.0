# Current Sprint: Nutrition Backend Persistence

**Objective:** Persist parsed natural language meal logs to a local SQLite database and enable clean retrieval endpoints.

---

## 🏃 Active Tasks

- [ ] **Define SQLModel tables**
  - Add database schema class definitions for `Meal` and `FoodItem` with relationship linking in `backend/main.py`.
- [ ] **Setup SQLite engine and session**
  - Initialize the engine for `lyfsync.db` and set up standard session dependencies/context managers.
- [ ] **Initialize database on startup**
  - Add a FastAPI startup handler to trigger table creation automatically when the server runs.
- [ ] **Persist parent Meal on parse**
  - Update `POST /api/v1/meals/parse` to write the parsed meal structure to SQLite first.
- [ ] **Persist child FoodItems on parse**
  - Save all individual items linked to the newly created parent meal ID in the transaction.
- [ ] **Handle session rollback on parse error**
  - Ensure any failure in database operations rolls back the current session to avoid partial inserts.
- [ ] **Create GET /meals endpoint**
  - Implement a simple GET route returning history of all logged meals and their food items.
