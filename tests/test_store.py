"""
Mini Redis 코어(store.py) 유닛 테스트

HashTable과 MiniRedis 클래스가 올바르게 동작하는지 검증한다.
각 테스트는 독립적으로 실행 가능하도록 fresh한 MiniRedis 인스턴스를 사용한다.
"""

import time
import pytest
from app.core.store import HashTable, MiniRedis


@pytest.fixture
def redis():
    """매 테스트마다 새로운 MiniRedis 인스턴스를 생성한다."""
    return MiniRedis()


# ──────────────────────────────────────────────
# 1. set → get 정상 동작
# ──────────────────────────────────────────────
def test_set_and_get(redis):
    # 키에 값을 저장한 뒤 조회하면 같은 값이 나와야 한다.
    redis.set("name", "jiyong")
    assert redis.get("name") == "jiyong"


# ──────────────────────────────────────────────
# 2. get: 존재하지 않는 키 → None 반환
# ──────────────────────────────────────────────
def test_get_nonexistent_key(redis):
    # 저장한 적 없는 키를 조회하면 None이 반환되어야 한다.
    assert redis.get("no_such_key") is None


# ──────────────────────────────────────────────
# 3. delete → 이후 get → None 반환
# ──────────────────────────────────────────────
def test_delete_then_get(redis):
    # 키를 저장하고 삭제한 뒤 조회하면 None이어야 한다.
    redis.set("temp", "value")
    result = redis.delete("temp")
    assert result is True
    assert redis.get("temp") is None


# ──────────────────────────────────────────────
# 4. exists: 저장 후 True, 삭제 후 False
# ──────────────────────────────────────────────
def test_exists_before_and_after_delete(redis):
    redis.set("key1", "val1")
    assert redis.exists("key1") is True

    redis.delete("key1")
    assert redis.exists("key1") is False


# ──────────────────────────────────────────────
# 5. TTL 설정 후 만료 전 get → 정상값 반환
# ──────────────────────────────────────────────
def test_ttl_before_expiration(redis):
    # TTL을 10초로 설정하면 만료 전에는 정상적으로 값이 조회되어야 한다.
    redis.set("alive", "yes", ttl=10)
    assert redis.get("alive") == "yes"


# ──────────────────────────────────────────────
# 6. TTL 만료 후 get → None 반환
# ──────────────────────────────────────────────
def test_ttl_after_expiration(redis):
    # TTL을 1초로 설정하고 2초 기다리면 만료되어 None이 반환되어야 한다.
    redis.set("short_lived", "bye", ttl=1)
    time.sleep(2)
    assert redis.get("short_lived") is None


# ──────────────────────────────────────────────
# 7. ttl(): TTL 없는 키 → -1
# ──────────────────────────────────────────────
def test_ttl_no_expiration(redis):
    # TTL 없이 저장한 키는 영구 저장이므로 ttl()이 -1을 반환해야 한다.
    redis.set("permanent", "data")
    assert redis.ttl("permanent") == -1


# ──────────────────────────────────────────────
# 8. ttl(): 존재하지 않는 키 → -2
# ──────────────────────────────────────────────
def test_ttl_nonexistent_key(redis):
    # 존재하지 않는 키의 TTL을 물으면 -2가 반환되어야 한다.
    assert redis.ttl("ghost") == -2


# ──────────────────────────────────────────────
# 9. expire() 후 ttl() → 양수 반환
# ──────────────────────────────────────────────
def test_expire_then_ttl(redis):
    # 키를 저장한 뒤 expire()로 TTL을 설정하면 ttl()이 양수를 반환해야 한다.
    redis.set("user:1", "park")
    result = redis.expire("user:1", 30)
    assert result is True
    remaining = redis.ttl("user:1")
    assert 0 < remaining <= 30


# ──────────────────────────────────────────────
# 10. flush() 후 모든 키 사라짐
# ──────────────────────────────────────────────
def test_flush(redis):
    # 여러 키를 저장한 뒤 flush()하면 모든 키가 사라져야 한다.
    redis.set("a", "1")
    redis.set("b", "2")
    redis.set("c", "3")
    redis.flush()
    assert redis.keys() == []
    assert redis.get("a") is None
    assert redis.get("b") is None


# ──────────────────────────────────────────────
# 11. 해시 충돌 처리 확인
# ──────────────────────────────────────────────
def test_hash_collision():
    """
    같은 버킷에 여러 키가 저장되어도 정상 동작하는지 확인한다.
    버킷 크기를 1로 설정하면 모든 키가 같은 버킷에 들어가므로
    체이닝이 제대로 작동하는지 검증할 수 있다.
    """
    # 버킷을 1개로 만들면 모든 키가 0번 버킷에 들어간다 → 100% 충돌
    ht = HashTable(size=1)

    ht.set("key_a", "value_a")
    ht.set("key_b", "value_b")
    ht.set("key_c", "value_c")

    # 충돌이 일어나도 각 키의 값이 정확히 조회되어야 한다.
    assert ht.get("key_a") == "value_a"
    assert ht.get("key_b") == "value_b"
    assert ht.get("key_c") == "value_c"

    # 중간 키를 삭제해도 나머지에 영향이 없어야 한다.
    assert ht.delete("key_b") is True
    assert ht.get("key_b") is None
    assert ht.get("key_a") == "value_a"
    assert ht.get("key_c") == "value_c"

    # 키 목록에 삭제된 키가 없어야 한다.
    assert sorted(ht.keys()) == ["key_a", "key_c"]
