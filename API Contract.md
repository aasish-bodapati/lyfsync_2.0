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
Analyzes natural language input, extracts individual food items, categorizes the meal, and computes itemized and total macronutrient estimates.

* **URL:** `/api/v1/meals/parse`
* **Method:** `POST`
* **Headers:** `Content-Type: application/json`
* **Auth Required:** Planned (Bearer Token)

#### Request Body Schema (`MealCreateRequest`)
```json
{
  "text": "I had 2 paneer parathas and a bowl of curd for breakfast"
}
```

#### Response: `200 OK` (`MealResponse`)
```json
{
  "meal_type": "breakfast",
  "items": [
    {
      "name": "paneer parathas",
      "calories": 480.0,
      "protein": 18.0,
      "carbs": 52.0,
      "fat": 22.0
    },
    {
      "name": "curd",
      "calories": 90.0,
      "protein": 6.0,
      "carbs": 7.0,
      "fat": 4.0
    }
  ],
  "total_calories": 570.0,
  "total_protein": 24.0,
  "total_carbs": 59.0,
  "total_fat": 26.0
}
```

#### Error Response: `500 Internal Server Error`
Occurs if AI structured output parsing fails or OpenAI API credentials are invalid.
```json
{
  "detail": "OpenAI parsing failed: Error message details here"
}
```
