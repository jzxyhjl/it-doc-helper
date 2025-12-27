"""
WebSocket API - 实时进度推送
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from uuid import UUID
import structlog
import json
import redis
from app.core.config import settings

logger = structlog.get_logger()
router = APIRouter()


@router.websocket("/ws/progress/{task_id}")
async def websocket_progress(websocket: WebSocket, task_id: str):
    """
    WebSocket连接，实时接收处理进度更新
    
    Args:
        task_id: 处理任务ID
    """
    try:
        # 验证task_id格式
        UUID(task_id)
    except ValueError:
        await websocket.close(code=1008, reason="无效的任务ID格式")
        return
    
    await websocket.accept()
    logger.info("WebSocket连接建立", task_id=task_id)
    
    # 连接Redis
    r = redis.from_url(settings.REDIS_URL)
    pubsub = r.pubsub()
    channel = f"task_progress:{task_id}"
    pubsub.subscribe(channel)
    
    try:
        # 发送初始连接确认
        await websocket.send_json({
            "type": "connected",
            "task_id": task_id
        })
        
        # 监听Redis消息
        while True:
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            
            if message:
                try:
                    # 解析进度消息
                    progress_data = json.loads(message['data'].decode('utf-8'))
                    
                    # 检查是否是流式内容消息
                    if progress_data.get("type") == "stream":
                        # 直接转发流式内容
                        await websocket.send_json({
                            "type": "stream",
                            "task_id": task_id,
                            "stream": progress_data.get("stream", {})
                        })
                    else:
                        # 普通进度消息
                        await websocket.send_json({
                            "type": "progress",
                            "task_id": task_id,
                            **progress_data
                        })
                        
                        # 如果完成或失败，关闭连接
                        if progress_data.get("status") in ["completed", "failed"]:
                            await websocket.send_json({
                                "type": progress_data.get("status"),
                                "task_id": task_id,
                                **progress_data
                            })
                            break
                        
                except Exception as e:
                    logger.error("处理进度消息失败", task_id=task_id, error=str(e))
            
            # 检查WebSocket连接状态
            try:
                # 发送ping保持连接
                await websocket.receive_text()
            except:
                # 连接已断开
                break
                
    except WebSocketDisconnect:
        logger.info("WebSocket连接断开", task_id=task_id)
    except Exception as e:
        logger.error("WebSocket错误", task_id=task_id, error=str(e))
        try:
            await websocket.send_json({
                "type": "error",
                "task_id": task_id,
                "error": str(e)
            })
        except:
            pass
    finally:
        pubsub.unsubscribe(channel)
        pubsub.close()
        try:
            await websocket.close()
        except:
            pass

