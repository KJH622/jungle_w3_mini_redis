"""
Mini Redis API 라우터

팀원들이 각자 맡은 엔드포인트를 이 파일에 구현한다.
SECTION A(CRUD)는 팀원 A가, SECTION B(TTL)는 팀원 B가 담당한다.
각 함수의 body는 비워두었으니, 주석 힌트를 참고해서 로직을 채워넣으면 돼.
"""

from fastapi import APIRouter, HTTPException
from app.core.store import store
from app.models.schemas import (
    SetRequest,
    ExpireRequest,
    ValueResponse,
    ExistsResponse,
    TTLResponse,
    KeysResponse,
    MessageResponse,
)

# API 엔드포인트들을 모아두는 라우터 객체야.
# 이걸 main.py에서 app.include_router(router)로 등록하면
# 여기에 정의한 경로들이 전부 서버에 연결돼.
router = APIRouter()


# ══════════════════════════════════════════════
# SECTION A: CRUD (팀원 A 작업 구역)
# ══════════════════════════════════════════════


@router.post("/set", response_model=MessageResponse)
async def set_value(request: SetRequest):
    # 키와 값을 Mini Redis에 저장하는 엔드포인트야.
    # 요청 body에서 key, value, ttl을 받아서 store.set()을 호출하면 돼.
    # ttl이 있으면 해당 시간(초) 후에 자동으로 만료돼.
    #
    # 힌트: store.set(request.key, request.value, request.ttl)
    #       return MessageResponse(message="OK")
    ...


@router.get("/get/{key}", response_model=ValueResponse)
async def get_value(key: str):
    # 키에 해당하는 값을 조회하는 엔드포인트야.
    # store.get(key)을 호출해서 값을 가져오면 돼.
    # 값이 None이면 HTTPException(status_code=404)를 발생시켜야 해.
    #
    # 힌트: value = store.get(key)
    #       if value is None: raise HTTPException(404, ...)
    #       return ValueResponse(value=value)
    ...


@router.delete("/delete/{key}", response_model=MessageResponse)
async def delete_key(key: str):
    # 키를 삭제하는 엔드포인트야.
    # store.delete(key)를 호출하면 돼.
    # 삭제 성공이면 "OK", 키가 없었으면 "키를 찾을 수 없습니다" 같은 메시지를 반환해.
    #
    # 힌트: result = store.delete(key)
    #       message = "OK" if result else "Key not found"
    #       return MessageResponse(message=message)
    ...


@router.get("/exists/{key}", response_model=ExistsResponse)
async def exists_key(key: str):
    # 키가 존재하는지 확인하는 엔드포인트야.
    # store.exists(key)를 호출해서 True/False를 반환하면 돼.
    #
    # 힌트: return ExistsResponse(exists=store.exists(key))
    ...


@router.get("/keys", response_model=KeysResponse)
async def get_keys():
    # 저장된 모든 키 목록을 반환하는 엔드포인트야.
    # store.keys()를 호출하면 만료되지 않은 키들의 리스트가 나와.
    #
    # 힌트: return KeysResponse(keys=store.keys())
    ...


@router.delete("/flush", response_model=MessageResponse)
async def flush_all():
    # 모든 데이터를 삭제하는 엔드포인트야.
    # store.flush()를 호출하면 전체 데이터가 초기화돼.
    # 주의: 되돌릴 수 없으니 신중하게 사용해야 해!
    #
    # 힌트: store.flush()
    #       return MessageResponse(message="OK")
    ...


# ══════════════════════════════════════════════
# SECTION B: TTL (팀원 B 작업 구역)
# ══════════════════════════════════════════════


@router.post("/expire", response_model=MessageResponse)
async def set_expire(request: ExpireRequest):
    # 이미 저장된 키에 만료 시간을 설정하는 엔드포인트야.
    # store.expire(key, ttl)을 호출하면 돼.
    # 키가 존재하지 않으면 HTTPException(status_code=404)를 발생시켜야 해.
    #
    # 힌트: result = store.expire(request.key, request.ttl)
    #       if not result: raise HTTPException(404, ...)
    #       return MessageResponse(message="OK")
    ...


@router.get("/ttl/{key}", response_model=TTLResponse)
async def get_ttl(key: str):
    # 키의 남은 수명(TTL)을 조회하는 엔드포인트야.
    # store.ttl(key)를 호출하면 남은 초가 나와.
    # 반환값: 양수(남은 초), -1(TTL 없음, 영구), -2(키 없음 또는 만료됨)
    #
    # 힌트: return TTLResponse(ttl=store.ttl(key))
    ...
