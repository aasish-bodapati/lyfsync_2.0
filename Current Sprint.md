# Current Sprint Backlog & Status

## 🏃 Sprint Focus: Foundation & NLP Meal Logging API
**Goal:** Establish the core AI parsing pipeline using structured output, implement persistent SQLModel database tables, and verify robust end-to-end itemized macro calculation.

---

## 🎟️ Active Tickets (Phase 3 Task Breakdown)

### Status Legend
* `[x]` Completed
* `[/]` In Progress
* `[ ]` To Do

---

### Backend & API
- [x] **TICKET-001:** Setup FastAPI project structure and environment variable loading (`backend/main.py`).
- [x] **TICKET-002:** Implement OpenAI structured parsing (`gpt-4o-mini`) using Pydantic models for itemized nutrition estimation (`/api/v1/meals/parse`).
- [ ] **TICKET-003:** Connect SQLModel engine to SQLite/PostgreSQL database to persist parsed meal histories.
- [ ] **TICKET-004:** Implement user authentication endpoints and tie logged meals to unique user IDs.
- [ ] **TICKET-005:** Refactor backend code if it approaches the 400-line limit to maintain modular clean architecture.

### Mobile / Client
- [ ] **TICKET-101:** Initialize React Native / Expo app inside the `/mobile` workspace.
- [ ] **TICKET-102:** Build conversational text input screen with voice-to-text option for rapid meal logging.
- [ ] **TICKET-103:** Create UI card components to display item-by-item macro breakdowns (Calories, Protein, Carbs, Fat).
- [ ] **TICKET-104:** Implement local offline storage queue for logs submitted during network disconnection.

---

## 🛡️ Quality & Gate Checks
* Ensure all files adhere strictly to the **< 400 lines of code** user rule.
* Perform automated unit testing on parsing utilities prior to merging future PRs.
