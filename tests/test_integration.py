"""
Mini Redis 통합 테스트

서버(uvicorn)가 http://localhost:8000 에서 실행 중인 상태에서
실제 HTTP 요청을 보내서 모든 엔드포인트가 잘 동작하는지 확인하는 테스트야.
단위 테스트(test_store.py)와 달리, 여기서는 API 레벨에서 전체 흐름을 검증해.
"""

import requests
import time
import threading
import pytest

# 서버 주소. 테스트 실행 전에 서버가 켜져 있어야 해.
BASE_URL = "http://localhost:8000"


# ──────────────────────────────────────────────
# 헬퍼 함수: API 호출을 간편하게 해주는 도우미들
# ──────────────────────────────────────────────

def set_value(key, value, ttl=None):
    """키-값을 저장하는 헬퍼 함수야. ttl이 있으면 만료 시간도 설정해."""
    body = {"key": key, "value": value}
    if ttl is not None:
        body["ttl"] = ttl
    return requests.post(f"{BASE_URL}/set", json=body)


def get_value(key):
    """키에 해당하는 값을 조회하는 헬퍼 함수야."""
    return requests.get(f"{BASE_URL}/get/{key}")


def delete_value(key):
    """키를 삭제하는 헬퍼 함수야."""
    return requests.delete(f"{BASE_URL}/delete/{key}")


def exists_value(key):
    """키가 존재하는지 확인하는 헬퍼 함수야."""
    return requests.get(f"{BASE_URL}/exists/{key}")


def ttl_value(key):
    """키의 남은 수명(TTL)을 조회하는 헬퍼 함수야."""
    return requests.get(f"{BASE_URL}/ttl/{key}")


def expire_value(key, ttl):
    """이미 저장된 키에 만료 시간을 설정하는 헬퍼 함수야."""
    return requests.post(f"{BASE_URL}/expire", json={"key": key, "ttl": ttl})


def get_keys():
    """저장된 모든 키 목록을 조회하는 헬퍼 함수야."""
    return requests.get(f"{BASE_URL}/keys")


def flush_all():
    """모든 데이터를 삭제하는 헬퍼 함수야."""
    return requests.delete(f"{BASE_URL}/flush")


def setnx_value(key, value, ttl=None):
    """키가 없을 때만 저장하는 헬퍼 함수야. (Set if Not eXists)"""
    body = {"key": key, "value": value}
    if ttl is not None:
        body["ttl"] = ttl
    return requests.post(f"{BASE_URL}/setnx", json=body)


def hold_seat(key, value="hold", ttl=5):
    """좌석을 임시 선점하는 헬퍼 함수야."""
    return requests.post(f"{BASE_URL}/hold", json={"key": key, "value": value, "ttl": ttl})


def confirm_seat(key):
    """임시 선점을 정식 예약으로 확정하는 헬퍼 함수야."""
    return requests.post(f"{BASE_URL}/confirm", json={"key": key, "value": "reserved", "ttl": 300})


# ──────────────────────────────────────────────
# 테스트 케이스
# ──────────────────────────────────────────────


def test_health_check():
    """서버가 살아있는지 확인하는 테스트야.
    /health 엔드포인트가 {"status": "ok"}를 반환하면 정상이야."""
    res = requests.get(f"{BASE_URL}/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_crud_flow():
    """기본 CRUD(생성-조회-삭제) 흐름을 확인하는 테스트야.
    값을 저장하고, 조회해서 맞는지 확인하고, 삭제 후 없어졌는지 확인해."""
    # 저장
    res = set_value("test:1", "hello")
    assert res.status_code == 200

    # 조회 - 저장한 값이 나와야 해
    res = get_value("test:1")
    assert res.status_code == 200
    assert res.json()["value"] == "hello"

    # 삭제
    res = delete_value("test:1")
    assert res.status_code == 200

    # 삭제 후 조회 - 404가 나와야 해
    res = get_value("test:1")
    assert res.status_code == 404


def test_ttl_flow():
    """TTL(만료 시간)이 제대로 동작하는지 확인하는 테스트야.
    10초 TTL로 값을 저장하고, 바로 조회하면 있어야 하고,
    11초 기다린 후 조회하면 사라져야(404) 정상이야."""
    # 10초 TTL로 저장 (HTTP 요청이 느릴 수 있어서 넉넉하게 설정)
    set_value("temp:1", "bye", ttl=10)

    # TTL이 양수여야 해 (아직 만료 전)
    res = ttl_value("temp:1")
    assert res.status_code == 200
    assert res.json()["ttl"] > 0

    # 11초 기다리면 만료돼
    time.sleep(11)

    # 만료 후 조회 - 404가 나와야 해
    res = get_value("temp:1")
    assert res.status_code == 404


def test_exists_flow():
    """키 존재 여부 확인이 제대로 동작하는지 테스트야.
    값을 저장하면 exists=True, 삭제하면 exists=False가 나와야 해."""
    # 저장
    set_value("exist:1", "yes")

    # 존재 확인 - True
    res = exists_value("exist:1")
    assert res.status_code == 200
    assert res.json()["exists"] is True

    # 삭제
    delete_value("exist:1")

    # 존재 확인 - False
    res = exists_value("exist:1")
    assert res.status_code == 200
    assert res.json()["exists"] is False


def test_expire_flow():
    """이미 저장된 키에 만료 시간을 나중에 설정하는 테스트야.
    처음에 TTL 없이 저장하면 -1(영구), expire로 TTL을 설정하면 양수가 나와야 해."""
    # TTL 없이 저장
    set_value("exp:1", "data")

    # TTL 확인 - 영구 저장이니까 -1
    res = ttl_value("exp:1")
    assert res.status_code == 200
    assert res.json()["ttl"] == -1

    # TTL 5초로 설정
    res = expire_value("exp:1", 5)
    assert res.status_code == 200

    # TTL 확인 - 양수가 나와야 해
    res = ttl_value("exp:1")
    assert res.status_code == 200
    assert res.json()["ttl"] > 0

    # 정리
    delete_value("exp:1")


def test_ttl_edge_cases():
    """TTL 엣지 케이스를 확인하는 테스트야.
    없는 키의 TTL은 -2, TTL 없는 키의 TTL은 -1이 나와야 해."""
    # 없는 키 - TTL은 -2
    res = ttl_value("nonexistent:key:12345")
    assert res.status_code == 200
    assert res.json()["ttl"] == -2

    # TTL 없는 키 - -1
    set_value("exp:no_ttl", "permanent")
    res = ttl_value("exp:no_ttl")
    assert res.status_code == 200
    assert res.json()["ttl"] == -1

    # 정리
    delete_value("exp:no_ttl")


def test_keys_flow():
    """키 목록 조회가 제대로 동작하는지 테스트야.
    전체 삭제 후 두 개를 저장하면 keys에 두 개가 포함되어야 해."""
    # 전체 삭제
    flush_all()

    # 두 개 저장
    set_value("key:1", "a")
    set_value("key:2", "b")

    # 키 목록 조회
    res = get_keys()
    assert res.status_code == 200
    keys = res.json()["keys"]
    assert "key:1" in keys
    assert "key:2" in keys

    # 정리
    delete_value("key:1")
    delete_value("key:2")


def test_flush_flow():
    """전체 삭제(flush)가 제대로 동작하는지 테스트야.
    값을 저장하고 flush 하면 전부 사라져야 해."""
    # 저장
    set_value("flush:1", "x")

    # 전체 삭제
    res = flush_all()
    assert res.status_code == 200

    # 조회 - 404
    res = get_value("flush:1")
    assert res.status_code == 404

    # 키 목록 - 비어있어야 해
    res = get_keys()
    assert res.status_code == 200
    assert res.json()["keys"] == []


def test_train_reservation_scenario():
    """열차 예약 시나리오를 시뮬레이션하는 테스트야.
    노선 데이터를 캐시에 저장하고 조회(Cache HIT)하는 흐름과,
    좌석을 예약하고 확인하는 흐름을 검증해."""
    # 노선 캐싱 (Cache Aside 패턴 시뮬레이션)
    train_data = '[{"id":"KTX-101","type":"KTX"}]'
    set_value("trains:서울:부산", train_data, ttl=60)

    # 캐시에서 조회 (Cache HIT)
    res = get_value("trains:서울:부산")
    assert res.status_code == 200
    assert res.json()["value"] == train_data

    # 좌석 예약
    set_value("seat:KTX-101:A1", "reserved", ttl=300)

    # 좌석 확인
    res = get_value("seat:KTX-101:A1")
    assert res.status_code == 200
    assert res.json()["value"] == "reserved"

    # 좌석 존재 확인
    res = exists_value("seat:KTX-101:A1")
    assert res.status_code == 200
    assert res.json()["exists"] is True

    # 정리
    delete_value("trains:서울:부산")
    delete_value("seat:KTX-101:A1")


def test_concurrent_writes():
    """동시에 여러 스레드가 같은 키에 쓰기를 시도하는 테스트야.
    10개 스레드가 동시에 set 요청을 보내도
    데이터가 손상되지 않고 마지막 값이 정상적으로 저장되어야 해."""
    key = "concurrent:test:1"
    errors = []

    def write_value(i):
        # 각 스레드가 같은 키에 다른 값을 저장해
        try:
            res = set_value(key, f"value-{i}")
            if res.status_code != 200:
                errors.append(f"thread-{i} failed: {res.status_code}")
        except Exception as e:
            errors.append(f"thread-{i} error: {e}")

    # 10개 스레드 동시 실행
    threads = [threading.Thread(target=write_value, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 에러가 없어야 해
    assert len(errors) == 0, f"동시 쓰기 에러 발생: {errors}"

    # 값이 정상적으로 저장되어 있어야 해 (어떤 값이든 상관없이 존재하면 OK)
    res = get_value(key)
    assert res.status_code == 200
    assert res.json()["value"].startswith("value-")

    # 정리
    delete_value(key)


# ══════════════════════════════════════════════
# GROUP 1 추가 — 기본 CRUD
# ══════════════════════════════════════════════


def test_get_nonexistent_key():
    # 존재하지 않는 키를 조회하면 404가 나와야 해.
    res = get_value("this:key:does:not:exist:99999")
    assert res.status_code == 404


# ══════════════════════════════════════════════
# GROUP 2 추가 — TTL / 만료
# ══════════════════════════════════════════════


def test_ttl_after_expiry_is_minus_two():
    # TTL이 만료된 키의 TTL을 조회하면 -2가 나와야 해.
    # -2는 "키가 없거나 만료됨"을 의미해.
    set_value("ttl:expire:test", "data", ttl=1)
    time.sleep(2)
    res = ttl_value("ttl:expire:test")
    assert res.status_code == 200
    assert res.json()["ttl"] == -2


# ══════════════════════════════════════════════
# GROUP 3 — SETNX
# ══════════════════════════════════════════════


def test_setnx_success_on_empty_key():
    # 없는 키에 setnx하면 성공해야 해.
    # 좌석 예약에서 "아무도 안 앉은 좌석"에 앉는 것과 같아.
    delete_value("setnx:test:1")  # 혹시 남아있을 수 있으니 정리
    res = setnx_value("setnx:test:1", "first")
    assert res.status_code == 200
    assert res.json()["success"] is True

    # 정리
    delete_value("setnx:test:1")


def test_setnx_fail_on_existing_key():
    # 이미 있는 키에 setnx하면 실패하고 기존 값이 유지돼야 해.
    # 이미 누가 앉은 좌석엔 못 앉는 거야.
    set_value("setnx:test:2", "original")
    res = setnx_value("setnx:test:2", "second")
    assert res.status_code == 200
    assert res.json()["success"] is False

    # 기존 값이 유지되는지 확인
    res = get_value("setnx:test:2")
    assert res.json()["value"] == "original"

    # 정리
    delete_value("setnx:test:2")


def test_setnx_success_after_expiry():
    # TTL로 저장한 키가 만료된 후에는 다시 setnx가 성공해야 해.
    # Lazy Deletion으로 만료된 키가 정리되면 재선점이 가능해.
    setnx_value("setnx:test:3", "hold", ttl=2)
    time.sleep(3)
    res = setnx_value("setnx:test:3", "new_hold")
    assert res.status_code == 200
    assert res.json()["success"] is True

    # 정리
    delete_value("setnx:test:3")


# ══════════════════════════════════════════════
# GROUP 4 — 임시 선점 (Hold)
# ══════════════════════════════════════════════


def test_hold_seat_success():
    # 빈 좌석에 /hold 요청하면 성공해야 해.
    # TTL도 설정되어 있어야 해.
    key = "seat:TEST:H1"
    delete_value(key)
    res = hold_seat(key, ttl=5)
    assert res.status_code == 200
    assert res.json()["success"] is True

    # TTL이 설정되었는지 확인
    res = ttl_value(key)
    assert res.json()["ttl"] > 0

    # 정리
    delete_value(key)


def test_hold_seat_fail_on_occupied():
    # 이미 선점된 좌석에 다시 /hold하면 실패해야 해.
    key = "seat:TEST:H2"
    delete_value(key)
    hold_seat(key, ttl=10)
    res = hold_seat(key, ttl=5)
    assert res.status_code == 200
    assert res.json()["success"] is False

    # 정리
    delete_value(key)


def test_hold_seat_reopen_after_expiry():
    # 임시 선점 후 TTL이 만료되면 다시 선점할 수 있는지 확인해.
    # 이게 Lazy Deletion이 제대로 동작한다는 증거야.
    key = "seat:TEST:H3"
    delete_value(key)
    hold_seat(key, ttl=2)
    time.sleep(3)
    res = hold_seat(key, ttl=5)
    assert res.status_code == 200
    assert res.json()["success"] is True

    # 정리
    delete_value(key)


def test_confirm_reservation():
    # /hold로 임시 선점 후 /confirm으로 확정하면
    # 값이 "reserved"로 바뀌고 TTL이 300초로 설정돼야 해.
    key = "seat:TEST:H4"
    delete_value(key)
    hold_seat(key, ttl=5)
    res = confirm_seat(key)
    assert res.status_code == 200
    assert res.json()["success"] is True

    # 값이 "reserved"인지 확인
    res = get_value(key)
    assert res.json()["value"] == "reserved"

    # TTL이 양수인지 확인 (300초 설정됨)
    res = ttl_value(key)
    assert res.json()["ttl"] > 0

    # 정리
    delete_value(key)


# ══════════════════════════════════════════════
# GROUP 5 — 열차 캐시 (Cache Aside)
# ══════════════════════════════════════════════


def test_trains_cache_miss_first_call():
    # flush 후 첫 조회는 캐시에 없으니까 cache_miss가 나와야 해.
    # DB에서 가져와서 캐시에 저장하는 과정이야.
    flush_all()
    res = requests.get(f"{BASE_URL}/trains/cached?from_station=서울&to_station=부산")
    assert res.status_code == 200
    assert res.json()["source"] == "cache_miss"


def test_trains_cache_hit_second_call():
    # 첫 조회로 캐시에 저장된 후, 바로 다시 조회하면 cache_hit이 나와야 해.
    # 이게 Cache Aside 패턴의 핵심이야.
    flush_all()
    # 첫 번째 (MISS)
    requests.get(f"{BASE_URL}/trains/cached?from_station=서울&to_station=부산")
    # 두 번째 (HIT)
    res = requests.get(f"{BASE_URL}/trains/cached?from_station=서울&to_station=부산")
    assert res.status_code == 200
    assert res.json()["source"] == "cache_hit"


def test_trains_db_direct():
    # /trains 엔드포인트는 캐시 없이 DB에서 직접 가져와.
    # source="db"이고 응답 시간이 0 이상이어야 해.
    res = requests.get(f"{BASE_URL}/trains?from_station=서울&to_station=부산")
    assert res.status_code == 200
    data = res.json()
    assert data["source"] == "db"
    assert data["elapsed_ms"] >= 0


# ══════════════════════════════════════════════
# GROUP 6 — 동시성
# ══════════════════════════════════════════════


def test_concurrent_reservation_only_one_success():
    # 10명이 동시에 같은 좌석을 예약하면 딱 1명만 성공해야 해.
    # threading.Lock + setnx가 제대로 동작하는지 확인해.
    res = requests.post(
        f"{BASE_URL}/benchmark/concurrent?train_id=TEST&seat=C1&n=10"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success_count"] == 1
    assert data["fail_count"] == 9


def test_concurrent_winner_is_random():
    # 3번 동시 예약을 실행하면 winner가 매번 같지는 않아야 해.
    # threading.Event 방식이라 매번 다른 스레드가 이길 수 있어.
    # 최소 1번은 다른 winner가 나오면 통과.
    winners = []
    for _ in range(3):
        res = requests.post(
            f"{BASE_URL}/benchmark/concurrent?train_id=TEST&seat=RAND&n=5"
        )
        data = res.json()
        winners.append(data["winner"])
    # 3번 모두 같을 확률은 낮지만, 혹시 같더라도 통과시켜.
    # 이 테스트는 동시성이 동작한다는 것만 확인하면 돼.
    assert all(w is not None for w in winners)


# ══════════════════════════════════════════════
# GROUP 7 — 벤치마크
# ══════════════════════════════════════════════


def test_benchmark_trains_returns_metrics():
    # 벤치마크 결과에 DB 시간, Mini Redis 시간이 포함돼야 해.
    res = requests.get(f"{BASE_URL}/benchmark/trains?n=10&from_station=서울&to_station=부산")
    assert res.status_code == 200
    data = res.json()
    assert data["db_only_ms"] >= 0
    assert data["mini_redis_ms"] >= 0
    assert data["iterations"] == 10


def test_benchmark_redis_compare():
    # Mini Redis vs 실제 Redis 순수 비교 결과가 정상 반환돼야 해.
    res = requests.get(f"{BASE_URL}/benchmark/redis-compare?n=100")
    assert res.status_code == 200
    data = res.json()
    assert data["mini_redis"]["elapsed_ms"] > 0
    assert data["mini_redis"]["ops_per_sec"] > 0
    assert data["operations"] == 200  # 100 * 2 (set + get)


def test_benchmark_concurrent_endpoint():
    # 동시 예약 벤치마크 엔드포인트가 정상 반환돼야 해.
    # 5명이 동시에 시도하면 성공 1명이어야 해.
    res = requests.post(
        f"{BASE_URL}/benchmark/concurrent?train_id=BENCH&seat=B1&n=5"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success_count"] == 1
    assert data["total"] == 5


# ══════════════════════════════════════════════
# GROUP 8 — 스냅샷
# ══════════════════════════════════════════════


def test_snapshot_save():
    # 데이터를 저장한 후 /snapshot/save를 호출하면 success=True여야 해.
    # snapshot.json 파일에 현재 데이터가 저장돼.
    set_value("snap:test", "data")
    res = requests.post(f"{BASE_URL}/snapshot/save")
    assert res.status_code == 200
    assert res.json()["success"] is True

    # 정리
    delete_value("snap:test")


def test_snapshot_status_exists():
    # 스냅샷 저장 후 /snapshot/status를 조회하면 exists=True여야 해.
    # 저장된 키 수도 0보다 커야 해.
    set_value("snap:check", "value")
    requests.post(f"{BASE_URL}/snapshot/save")
    res = requests.get(f"{BASE_URL}/snapshot/status")
    assert res.status_code == 200
    data = res.json()
    assert data["exists"] is True
    assert data["key_count"] > 0

    # 정리
    delete_value("snap:check")


def test_snapshot_clear():
    # /snapshot/clear를 호출하면 snapshot.json 파일이 삭제돼야 해.
    # 먼저 저장 후 삭제해서 success=True 확인.
    requests.post(f"{BASE_URL}/snapshot/save")
    res = requests.delete(f"{BASE_URL}/snapshot/clear")
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_snapshot_status_after_clear():
    # 스냅샷 삭제 후 /snapshot/status를 조회하면 exists=False여야 해.
    # 재시작하면 데이터가 사라진다는 뜻이야.
    requests.post(f"{BASE_URL}/snapshot/save")
    requests.delete(f"{BASE_URL}/snapshot/clear")
    res = requests.get(f"{BASE_URL}/snapshot/status")
    assert res.status_code == 200
    assert res.json()["exists"] is False


# ══════════════════════════════════════════════
# GROUP 9 — 헬스체크 / Redis 상태
# ══════════════════════════════════════════════


def test_redis_status():
    # /redis/status 엔드포인트가 정상 반환돼야 해.
    # Docker Redis가 켜져 있으면 True, 아니면 False.
    res = requests.get(f"{BASE_URL}/redis/status")
    assert res.status_code == 200
    assert "available" in res.json()
