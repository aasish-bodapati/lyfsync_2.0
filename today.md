# Daily Focus: Backend Persistence & History API (June 29, 2026)

Our single goal today is to connect a local SQLite database so that meals parsed by our AI endpoint are saved and can be retrieved.

## Tasks
- [x] **Task 1:** Define the SQLModel database schemas (`Meal` and `FoodItem`) in the backend.
- [x] **Task 2:** Set up database engine initialization on backend startup.
- [x] **Task 3:** Update `/api/v1/meals/parse` to save the parsed meal and its items to SQLite.
- [x] **Task 4:** Create `/api/v1/meals` endpoint to return historical logged meals and verify it works.

---

*Keep it simple, test as we go, and keep all files under 400 lines of code.*
