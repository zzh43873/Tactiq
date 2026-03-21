"""
实体管理API路由
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException

from app.schemas import (
    Entity,
    EntityCreate,
    EntityUpdate,
    EntityList
)

router = APIRouter()


@router.post("/", response_model=Entity)
async def create_entity(entity: EntityCreate):
    """创建实体"""
    # TODO: 实现创建逻辑
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{entity_id}", response_model=Entity)
async def get_entity(entity_id: UUID):
    """获取实体详情"""
    # TODO: 实现查询逻辑
    raise HTTPException(status_code=404, detail="Entity not found")


@router.get("/", response_model=EntityList)
async def list_entities(
    page: int = 1,
    page_size: int = 20,
    entity_type: str = None
):
    """获取实体列表"""
    # TODO: 实现列表查询
    return EntityList(
        items=[],
        total=0,
        page=page,
        page_size=page_size
    )


@router.put("/{entity_id}", response_model=Entity)
async def update_entity(entity_id: UUID, entity: EntityUpdate):
    """更新实体"""
    # TODO: 实现更新逻辑
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete("/{entity_id}")
async def delete_entity(entity_id: UUID):
    """删除实体"""
    # TODO: 实现删除逻辑
    raise HTTPException(status_code=501, detail="Not implemented")
