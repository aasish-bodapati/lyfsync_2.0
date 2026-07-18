# LyfSync 2.0 API Contract

This document defines the REST API specifications, request payloads, response schemas, and error formats for the LyfSync backend service.

---

## Base URL
* **Local Development:** `http://localhost:8000`
* **API Documentation:** `http://localhost:8000/docs` (Interactive Swagger UI)

---

## Endpoints

### 1. Health Check
Checks if the backend server is operational.

* **URL:** `/health`
* **Method:** `GET`
* **Auth Required:** No

#### Response: `200 OK`
```json
{
  "status": "Server is running successfully",
  "status_code": 200
}
```

---

### 2. Parse Natural Language Meal
Analyzes natural language input, extracts individual food items, categorizes the meal, and computes itemized and total macronutrient estimates using vector search against a USDA database.

* **URL:** `/api/v1/meals/parse`
* **Method:** `POST`
* **Headers:** `Content-Type: application/json`
* **Auth Required:** Planned (Bearer Token)

#### Request Body Schema (`UserInput`)
```json
{
  "text": "I had 2 paneer parathas and a bowl of curd for breakfast"
}
```

#### Response: `200 OK` (`Meal`)
```json
{
  "meal_type": "breakfast",
  "items": [
    {
      "name": "paneer paratha",
      "weight_grams": 250.0,
      "calories": 480.0,
      "protein": 18.0,
      "carbs": 52.0,
      "fat": 22.0,
      "source": "db_match_high",
      "confidence": 0.85
    },
    {
      "name": "curd",
      "weight_grams": 150.0,
      "calories": 90.0,
      "protein": 6.0,
      "carbs": 7.0,
      "fat": 4.0,
      "source": "llm_fallback",
      "confidence": null
    }
  ],
  "total_calories": 570.0,
  "total_protein": 24.0,
  "total_carbs": 59.0,
  "total_fat": 26.0
}
```

#### Error Responses

* **`400 Bad Request`**: Could not parse the text into food items (e.g., gibberish input).
  ```json
  { "detail": "Failed to parse meal description" }
  ```
* **`422 Unprocessable Entity`**: Invalid JSON payload.
* **`500 Internal Server Error`**: Database error during persistence.
  ```json
  { "detail": "Failed to save meal" }
  ```
* **`502 Bad Gateway`**: OpenAI API failure/timeout.
  ```json
  { "detail": "AI service unavailable" }
  ```

---

### 3. List Past Meals
Retrieves all previously logged meals from the database. *(Note: Currently returns un-nested Meal rows; to be updated in Phase 3 to match the parse response shape)*.

* **URL:** `/api/v1/meals`
* **Method:** `GET`
* **Auth Required:** Planned (Bearer Token)

#### Response: `200 OK` (`List[MealTable]`)
```json
[
  {
    "id": 1,
    "raw_text": "I had 2 paneer parathas and a bowl of curd for breakfast",
    "meal_type": "breakfast",
    "calories": 570.0,
    "protein": 24.0,
    "carbs": 59.0,
    "fat": 26.0,
    "created_at": "2026-07-16T12:00:00Z"
  }
]
```
