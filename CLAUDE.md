# CLAUDE.md – Core Developer Guide

> 이 파일은 코어 개발자(main 브랜치)를 위한 AI 에이전트 지침입니다.
> AGENT.md는 팀원 공유용이며, 코어 개발자는 이 파일을 따릅니다.

---

## Role

우리는 **코어 개발자**입니다. `core/store.py`를 포함한 모든 핵심 모듈을 직접 작성·수정합니다.
AGENT.md의 "do not modify" 제약은 팀원용이며, 우리에게는 적용되지 않습니다.

---

## Branch Strategy

| Branch | Owner | Scope |
|--------|-------|-------|
| `main` | 코어 개발자 (본인) | store.py, main.py, schemas.py, 전체 구조 |
| `feature/router` | 팀원 A | api/routes.py (CRUD endpoints) |
| `feature/ttl` | 팀원 B | api/routes.py (TTL endpoints) |
| `feature/benchmark-frontend` | 팀원 C | frontend/, tests/, benchmark |

---

## Project Structure

```
app/
 ├── main.py              ← FastAPI app entry point
 ├── api/
 │    └── routes.py        ← API endpoints (팀원 A, B 담당)
 ├── core/
 │    └── store.py         ← In-memory KV store (코어)
 └── models/
      └── schemas.py       ← Pydantic request/response models
tests/
 └── test_api.py           ← pytest tests (팀원 C 담당)
frontend/
 └── index.html            ← Demo UI (팀원 C 담당)
```

---

## Tech Stack

- **Backend**: FastAPI + Uvicorn
- **Storage**: Custom HashTable (`threading.Lock` for concurrency)
- **Testing**: pytest + httpx (async test client)
- **Frontend**: HTML + Vanilla JS

---

## Project Context

This is a Mini Redis project built with FastAPI for a 1-day implementation sprint.
The core maintainer is solely responsible for all files under `app/core/`.
All other contributors work only on their assigned files.

---

## Core Architecture Decision

### Why custom HashTable instead of Python dict

The project requirement explicitly demands:
- 해시 테이블을 활용하여 키-값 저장소를 직접 만들 것
- 해시 테이블의 설계 원리와 동작 방식을 설명할 수 있을 것

Using Python's built-in `dict` would make it impossible to explain
hash collision handling during QnA. Therefore we implement a custom HashTable.

### HashTable Design

```python
class HashTable:
    def __init__(self, size: int = 256):
        # 256개의 버킷을 가진 배열을 초기화한다.
        # 각 버킷은 (key, value) 쌍의 리스트로 충돌을 체이닝 방식으로 처리한다.
        self.size = size
        self.buckets = [[] for _ in range(self.size)]

    def _hash(self, key: str) -> int:
        # 문자열 키를 버킷 인덱스로 변환한다.
        # Python 내장 hash()를 사용하고 버킷 크기로 나눈 나머지를 인덱스로 사용한다.
        return hash(key) % self.size
```

Collision resolution: Chaining (각 버킷은 리스트로 여러 키-값 쌍을 보관)

### TTL Design

두 개의 HashTable 인스턴스로 데이터와 만료 시간을 분리:

```python
hash_table = HashTable()   # key → value
expire_at  = HashTable()   # key → expiration timestamp (float)
```

Expiration: Lazy Deletion (조회 시점에만 만료 여부 확인)

### Concurrency

threading.Lock 으로 모든 쓰기 연산 보호 (set, delete, expire, flush)

---

## Files Owned by Core Maintainer (Do Not Touch)

- app/core/store.py
- app/main.py
- app/models/schemas.py

---

## Code Comment Rule

모든 함수와 핵심 로직에 한글 주석 필수.
주석은 "무엇을 하는지 + 왜 이렇게 작성했는지" 수준으로 작성.

```python
# 좋은 예시
def get(self, key: str):
    # 키에 해당하는 값을 해시 테이블에서 조회한다.
    # 만료된 키는 삭제 후 None을 반환한다. (Lazy Deletion 전략)

# 나쁜 예시
def get(self, key: str):
    # get value
```

---

## How to Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
pytest tests/
```
