# Mini Redis

> 해시 테이블을 직접 구현하여 만든 인메모리 키-값 저장소 (REST API)

Redis의 핵심 원리(해시 테이블, TTL, 동시성 제어)를 Python dict 없이 밑바닥부터 구현하여,
자료구조의 동작 방식을 깊이 이해하기 위해 만든 프로젝트입니다.

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| Backend | FastAPI + Uvicorn |
| 저장소 | 직접 구현한 HashTable (Python dict 미사용) |
| 동시성 | threading.Lock |
| 테스트 | pytest |
| 프론트엔드 | HTML + Vanilla JS |
| 터널링 | Cloudflare Tunnel |

---

## 아키텍처

### HashTable 구조

```
버킷 배열 (크기: 256)
┌───────────┐
│ bucket[0] │ → [(key_a, val_a), (key_b, val_b)]  ← 체이닝으로 충돌 처리
│ bucket[1] │ → [(key_c, val_c)]
│ bucket[2] │ → []
│    ...    │
│bucket[255]│ → [(key_z, val_z)]
└───────────┘
```

- **해시 함수**: `hash(key) % bucket_size` → 키를 버킷 인덱스로 변환
- **충돌 해결**: Chaining — 같은 버킷에 리스트로 여러 쌍 저장

### 데이터 / TTL 분리

```python
hash_table = HashTable()   # key → value (실제 데이터)
expire_at  = HashTable()   # key → timestamp (만료 시간)
```

두 개의 독립된 HashTable 인스턴스로 관심사를 분리합니다.

### Lazy Deletion (게으른 삭제)

별도 타이머 없이, **조회 시점에 만료 여부를 확인**하고 만료되었으면 그때 삭제합니다.
실제 Redis에서도 사용하는 전략입니다.

### 동시성 제어

`threading.Lock`으로 모든 쓰기 연산(set, delete, expire, flush)을 보호합니다.
여러 요청이 동시에 들어와도 데이터가 꼬이지 않습니다.

---

## API 명세

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/set` | 키-값 저장 (TTL 선택) |
| GET | `/get/{key}` | 값 조회 |
| DELETE | `/delete/{key}` | 키 삭제 |
| GET | `/exists/{key}` | 키 존재 여부 |
| GET | `/keys` | 전체 키 목록 |
| DELETE | `/flush` | 전체 초기화 |
| POST | `/expire` | TTL 설정 |
| GET | `/ttl/{key}` | 남은 만료 시간 |
| GET | `/health` | 서버 상태 |

---

## 실행 방법

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

브라우저에서 `http://localhost:8000/docs` 접속 시 Swagger UI 확인 가능

---

## 테스트 실행

```bash
pytest tests/ -v
```

---

## 핵심 구현 포인트

- **해시 충돌 처리**: 체이닝(Chaining) 방식 — 같은 버킷에 리스트로 여러 키-값 쌍 보관
- **TTL 만료 처리**: Lazy Deletion — 조회 시점에 만료 확인 후 삭제
- **동시성 제어**: threading.Lock으로 쓰기 연산 보호
- **성능 비교**: 캐시 없을 때 vs Mini Redis 캐시 사용 응답 시간 비교

---

## 성능 비교 결과

```
외부 API 직접 호출 100회:   ___ ms
Mini Redis 캐시 사용:        ___ ms
실제 Redis 캐시 사용:        ___ ms
```

> 벤치마크 실행 후 실제 수치로 업데이트 예정
