# AGENT.md – Mini Redis Project

> This file is the single source of truth for all AI agents working on this project.
> Read this entire file before writing any code.

---

## 🎯 Project Overview

Build a **Mini Redis** — an in-memory key-value store — exposed via a REST API using FastAPI.

- 1-day implementation sprint
- AI-assisted development is expected and encouraged
- Focus: working system over perfect architecture

---

## 🚫 Ground Rules

- **Do NOT modify `core/store.py`** — this is owned by the core maintainer
- **Do NOT create new files** outside your assigned scope
- **Do NOT install new packages** without confirming with the team
- Call store methods only — do not re-implement core logic yourself
- If something is unclear, ask before assuming

---

## 📁 Project Structure

```
app/
 ├── main.py
 ├── api/
 │    └── routes.py
 ├── core/
 │    └── store.py        ← DO NOT MODIFY
 └── models/
      └── schemas.py
tests/
 └── test_api.py
frontend/
 └── index.html
```

---

## 🧠 Core Logic (store.py — reference only)

Data is stored in two plain Python dicts:

```python
data = {}       # key → value
expire_at = {}  # key → expiration timestamp
```

### Expiration Strategy

Lazy expiration — checked on every read:

```python
if key in expire_at and time() > expire_at[key]:
    # delete and treat as missing
```

### Concurrency

All write operations (`set`, `delete`, `expire`) are protected by `threading.Lock`.

### Available Store Methods

```python
store.set(key: str, value: str, ttl: int | None = None)
store.get(key: str) -> str | None
store.delete(key: str) -> bool
store.exists(key: str) -> bool
store.expire(key: str, ttl: int) -> bool
store.ttl(key: str) -> int   # -1: no TTL, -2: expired or missing
store.keys() -> list[str]
store.flush()
```

---

## 🌐 API Design

### POST `/set`
```json
{ "key": "user:1", "value": "jiyong", "ttl": 60 }
```

### GET `/get/{key}`
```json
{ "value": "jiyong" }
```

### DELETE `/delete/{key}`

### GET `/exists/{key}`
```json
{ "exists": true }
```

### POST `/expire`
```json
{ "key": "user:1", "ttl": 60 }
```

### GET `/ttl/{key}`
```json
{ "ttl": 42 }
```

### GET `/keys`

### DELETE `/flush`

---

## 👥 Role Assignments

---

### 👤 A — CRUD API (`api/routes.py`)

Implement the following endpoints using FastAPI router:

- `POST /set`
- `GET /get/{key}`
- `DELETE /delete/{key}`
- `GET /exists/{key}`
- `GET /keys`
- `DELETE /flush`

**Rules:**
- Import and call `store` methods only
- Use request/response schemas from `models/schemas.py`
- Do not add business logic — just call the store

---

### 👤 B — TTL & Expiration (`api/routes.py` — TTL section)

Implement:

- `POST /expire`
- `GET /ttl/{key}`

**Edge cases to handle:**
- Key has no TTL → return `-1`
- Key is expired or missing → return `-2`

**Rules:**
- Same as above — call store methods only
- Do not touch expiration logic in `store.py`

---

### 👤 C — Demo + Benchmark + Tests

#### 1. Frontend (`frontend/index.html`)
Single HTML file with vanilla JS:
- Input fields: key, value
- Buttons: SET / GET / DELETE
- Display result on screen
- Calls the FastAPI endpoints directly via `fetch`

#### 2. Cache Demo (inside `index.html` or separate button)
Scenario:
1. Button: "Fetch without cache" → calls external API directly, records time
2. Button: "Fetch with cache" → first call stores in Redis, subsequent calls return cached value
3. Display both response times side by side

Suggested external API: `https://jsonplaceholder.typicode.com/posts/1`

#### 3. Benchmark (displayed in UI or console)
```
No Cache:   1200 ms
With Cache:  200 ms
```

#### 4. Tests (`tests/test_api.py`)

Write pytest tests covering:
- `set` → `get` returns correct value
- `delete` → `get` returns null
- `expire` → after TTL, `get` returns null
- `exists` before and after delete
- `ttl` edge cases (-1, -2)

---

## 🧪 How to Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Tests:
```bash
pytest tests/
```

---

## 📦 Tech Stack

| Component | Choice |
|-----------|--------|
| Backend | FastAPI |
| Server | Uvicorn |
| Testing | pytest |
| Frontend | HTML + Vanilla JS |
| Storage | In-memory dict |

---

## 🚫 Out of Scope

Do not implement:
- Redis wire protocol (RESP)
- Clustering or replication
- LRU eviction
- Pub/Sub
- Advanced persistence (AOF, RDB)

---

## ✅ Definition of Done

- [ ] All MVP endpoints return correct responses
- [ ] TTL expiration works (lazy deletion)
- [ ] Frontend demo runs in browser
- [ ] Benchmark shows measurable cache performance difference
- [ ] At least 5 passing pytest tests