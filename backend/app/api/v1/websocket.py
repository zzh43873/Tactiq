"""
WebSocket API
提供实时进度推送
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import asyncio
from loguru import logger

from app.core.redis_client import task_storage, redis_client

router = APIRouter()

# 存储活跃的WebSocket连接
# 结构: {task_type: {task_id: {websocket}}}
active_connections: Dict[str, Dict[str, Set[WebSocket]]] = {
    "simulation": {},
    "intelligence": {}
}


class ConnectionManager:
    """WebSocket连接管理器"""
    
    @staticmethod
    async def connect(websocket: WebSocket, task_type: str, task_id: str):
        """建立连接"""
        await websocket.accept()
        
        if task_type not in active_connections:
            active_connections[task_type] = {}
        if task_id not in active_connections[task_type]:
            active_connections[task_type][task_id] = set()
        
        active_connections[task_type][task_id].add(websocket)
        logger.info(f"WebSocket connected: {task_type}/{task_id}, total connections: {len(active_connections[task_type][task_id])}")
    
    @staticmethod
    async def disconnect(websocket: WebSocket, task_type: str, task_id: str):
        """断开连接"""
        if task_type in active_connections and task_id in active_connections[task_type]:
            active_connections[task_type][task_id].discard(websocket)
            if not active_connections[task_type][task_id]:
                del active_connections[task_type][task_id]
            logger.info(f"WebSocket disconnected: {task_type}/{task_id}")
    
    @staticmethod
    async def broadcast(task_type: str, task_id: str, message: dict):
        """广播消息给所有订阅该任务的连接"""
        if task_type not in active_connections:
            return
        if task_id not in active_connections[task_type]:
            return
        
        disconnected = set()
        for connection in active_connections[task_type][task_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send message to WebSocket: {e}")
                disconnected.add(connection)
        
        # 清理断开的连接
        for conn in disconnected:
            active_connections[task_type][task_id].discard(conn)


manager = ConnectionManager()


@router.websocket("/ws/{task_type}/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_type: str, task_id: str):
    """
    WebSocket端点
    
    连接URL: ws://localhost:8000/api/v1/ws/{task_type}/{task_id}
    
    task_type: simulation 或 intelligence
    task_id: 任务ID
    
    客户端会实时收到任务进度更新
    """
    await manager.connect(websocket, task_type, task_id)
    
    try:
        # 发送当前任务状态
        task_data = await task_storage.get_task(task_type, task_id)
        if task_data:
            await websocket.send_json({
                "type": "status",
                "data": task_data
            })
        else:
            await websocket.send_json({
                "type": "error",
                "message": "Task not found"
            })
        
        # 启动Redis订阅监听（用于接收后台任务进度更新）
        listen_task = asyncio.create_task(
            listen_redis_updates(websocket, task_type, task_id)
        )
        
        # 保持连接并处理客户端消息
        while True:
            try:
                # 接收客户端消息（心跳或命令）
                data = await websocket.receive_text()
                message = json.loads(data)
                
                msg_type = message.get("type")
                
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                elif msg_type == "get_status":
                    # 客户端请求最新状态
                    task_data = await task_storage.get_task(task_type, task_id)
                    if task_data:
                        await websocket.send_json({
                            "type": "status",
                            "data": task_data
                        })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}"
                    })
                    
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
            except Exception as e:
                logger.error(f"WebSocket message handling error: {e}")
                break
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {task_type}/{task_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        listen_task.cancel()
        await manager.disconnect(websocket, task_type, task_id)


async def listen_redis_updates(websocket: WebSocket, task_type: str, task_id: str):
    """
    监听Redis发布订阅，接收任务进度更新
    
    后台任务通过Redis发布进度更新，这里接收并推送给WebSocket客户端
    """
    try:
        r = await redis_client.connect()
        channel = f"tactiq:progress:{task_type}:{task_id}"
        pubsub = r.pubsub()
        await pubsub.subscribe(channel)
        
        logger.info(f"Started listening to Redis channel: {channel}")
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    await websocket.send_json({
                        "type": "progress",
                        "data": data
                    })
                except Exception as e:
                    logger.error(f"Failed to process Redis message: {e}")
                    
    except asyncio.CancelledError:
        logger.info(f"Stopped listening to Redis channel for {task_type}/{task_id}")
    except Exception as e:
        logger.error(f"Redis listener error: {e}")


# 辅助函数：从后台任务调用，发布进度更新
async def publish_progress(task_type: str, task_id: str, progress_data: dict):
    """
    发布进度更新
    
    由后台任务调用，将进度更新发布到Redis和WebSocket
    
    Args:
        task_type: 任务类型
        task_id: 任务ID
        progress_data: 进度数据
    """
    try:
        # 保存到Redis
        await task_storage.update_task(task_type, task_id, progress_data)
        
        # 发布到Redis频道（供WebSocket订阅）
        await task_storage.publish_progress(task_type, task_id, progress_data)
        
        # 直接推送给已连接的WebSocket客户端
        await manager.broadcast(task_type, task_id, {
            "type": "progress",
            "data": progress_data
        })
        
    except Exception as e:
        logger.error(f"Failed to publish progress: {e}")


# 节点执行事件发布函数
async def publish_node_event(
    task_type: str,
    task_id: str,
    event_type: str,  # 'node_started', 'node_completed', 'node_error'
    node_name: str,
    data: dict = None
):
    """
    发布节点执行事件
    
    用于可视化展示LangGraph节点执行流程
    
    Args:
        task_type: 任务类型
        task_id: 任务ID
        event_type: 事件类型
        node_name: 节点名称
        data: 附加数据
    """
    try:
        event_data = {
            "type": "node_event",
            "event_type": event_type,
            "node_name": node_name,
            "timestamp": asyncio.get_event_loop().time(),
            "data": data or {}
        }
        
        # 直接推送给已连接的WebSocket客户端
        await manager.broadcast(task_type, task_id, event_data)
        
        # 同时发布到Redis供其他消费者
        await task_storage.publish_progress(task_type, task_id, event_data)
        
    except Exception as e:
        logger.error(f"Failed to publish node event: {e}")


async def publish_round_event(
    task_type: str,
    task_id: str,
    round_number: int,
    event_type: str,  # 'round_started', 'debate_started', 'decision_made', 'round_completed'
    data: dict = None
):
    """
    发布推演轮次事件
    
    用于可视化展示鹰鸽辩论和决策过程
    
    Args:
        task_type: 任务类型
        task_id: 任务ID
        round_number: 轮次编号
        event_type: 事件类型
        data: 附加数据（包含debate结果、decision等）
    """
    try:
        event_data = {
            "type": "round_event",
            "event_type": event_type,
            "round_number": round_number,
            "timestamp": asyncio.get_event_loop().time(),
            "data": data or {}
        }
        
        await manager.broadcast(task_type, task_id, event_data)
        await task_storage.publish_progress(task_type, task_id, event_data)
        
    except Exception as e:
        logger.error(f"Failed to publish round event: {e}")
