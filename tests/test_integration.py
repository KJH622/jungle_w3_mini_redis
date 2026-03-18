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
