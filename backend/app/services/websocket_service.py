"""
WebSocket服务
用于实时推送警告消息到前端
"""
import json
from typing import Set, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
from app.utils.logger import logger


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """接受新的WebSocket连接"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket连接已建立，当前连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket连接已断开，当前连接数: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict[Any, Any]):
        """广播消息给所有连接的客户端"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"发送消息失败: {e}")
                disconnected.append(connection)
        
        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)
    
    def get_connection_count(self) -> int:
        """获取当前连接数"""
        return len(self.active_connections)


# 全局连接管理器实例
manager = ConnectionManager()


class WebSocketService:
    """WebSocket服务类"""
    
    def __init__(self):
        self.manager = manager
    
    async def broadcast_alert(self, alert_data: Dict[str, Any]):
        """
        广播新警告消息
        
        Args:
            alert_data: 警告数据
        """
        message = {
            "type": "alert",
            "data": alert_data
        }
        await self.manager.broadcast(message)
        logger.info(f"已广播警告消息: alert_id={alert_data.get('id')}")
    
    async def broadcast_alert_update(self, alert_id: int, status: str):
        """
        广播警告状态更新
        
        Args:
            alert_id: 警告ID
            status: 新状态
        """
        message = {
            "type": "alert_update",
            "data": {
                "id": alert_id,
                "status": status
            }
        }
        await self.manager.broadcast(message)
        logger.info(f"已广播警告状态更新: alert_id={alert_id}, status={status}")
    
    async def broadcast_stats(self, stats: Dict[str, Any]):
        """
        广播统计信息
        
        Args:
            stats: 统计数据
        """
        message = {
            "type": "stats",
            "data": stats
        }
        await self.manager.broadcast(message)
    
    def get_connection_count(self) -> int:
        """获取当前连接数"""
        return self.manager.get_connection_count()