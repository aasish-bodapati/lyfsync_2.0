# LyfSync 2.0 Coding Standards & Engineering Rules

To maintain high code quality, readability, and seamless collaboration between human engineers and AI pair programmers, all code contributed to LyfSync 2.0 must strictly adhere to the following standards.

---

## 🚨 Mandatory User Global Rule: Maximum File Length

> [!IMPORTANT]
> **Keep all code files under 400 lines of code.**
> Whenever a file approaches 350–400 lines, it must be refactored and split into logical sub-modules, helper utilities, or separate router components. Monolithic files are strictly prohibited.

---

## 🐍 Python & Backend Guidelines (FastAPI / SQLModel)

### 1. Type Hinting & Validation
* Always use explicit Python type hints (`str`, `float`, `List`, `Optional`) for function arguments and return values.
* Leverage **Pydantic** and **SQLModel** for all request body validation and database serialization. Avoid dictionary manipulation for structured data.

### 2. Async vs Sync Handlers
* For CPU-bound or blocking synchronous network operations (like standard OpenAI SDK calls if not using async client), define route handlers using `def`.
* For non-blocking I/O operations (like async DB drivers or `httpx`), define route handlers using `async def`.

### 3. Error Handling
* Never let raw exceptions bubble up to the client. Wrap external API calls in `try...except` blocks and raise standard `HTTPException` with meaningful status codes (`400`, `404`, `500`).

### 4. Docstrings & Comments
* Preserve all existing comments and docstrings when modifying code.
* Write concise docstrings for all endpoints summarizing parameters, behavior, and expected returns.

---

## 📁 Directory & File Naming Conventions

* **Python Files:** Lowercase with underscores (`snake_case.py`). Example: `meal_parser.py`, `database.py`.
* **Frontend Components:** PascalCase (`PascalCase.tsx` / `.jsx`). Example: `MealCard.tsx`, `NutritionSummary.tsx`.
* **Configuration Files:** Standard lowercase (`.env`, `requirements.txt`, `settings.json`).

---

## 🧪 Testing Standards

* Each feature ticket must include unit tests verifying core business logic (e.g., macro summation formulas, string cleaning).
* API endpoints must have integration tests verifying HTTP status codes and response schema matching.
* Test files should mirror the codebase structure inside a `/tests` directory (e.g., `tests/test_main.py`).
