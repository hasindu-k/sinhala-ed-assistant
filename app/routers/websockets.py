from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List, Any, Optional
import json
import logging
from uuid import UUID
from app.core.security import decode_token
from app.core.database import get_db
from app.shared.models.user import User
from app.repositories.user_repository import UserRepository
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Store active connections: user_id -> List[WebSocket]
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"User {user_id} connected via WebSocket")

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"User {user_id} disconnected")

    async def send_personal_message(self, message: Any, user_id: str):
        if user_id in self.active_connections:
            connections = self.active_connections[user_id]
            # Handle potential broken connections
            to_remove = []
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send message to user {user_id}: {e}")
                    to_remove.append(connection)
            
            for connection in to_remove:
                self.disconnect(connection, user_id)

manager = ConnectionManager()
router = APIRouter()

async def get_current_user_ws(
    websocket: WebSocket,
    token: str,
    db: Session = next(get_db())
):
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
             return None
        
        repo = UserRepository(db)
        user = repo.get_user(UUID(user_id))
        return user
    except Exception as e:
        logger.error(f"WebSocket auth error: {e}")
        return None

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    # Authenticate
    # We create a new DB session for auth check because `Depends(get_db)` is hard inside websocket unless handled carefully
    # But usually Depends works on websocket too. Let's try simpler valid check manually.
    
    # Manually get DB context or just rely on decode_token if we trust JWT alone (but better to check user exists)
    # Since Depends works with WebSocket, we can use it.
    
    # However, to keep it simple and robust:

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=1008)
            return
        
        # Connection accepted
        await manager.connect(websocket, user_id)
        
        try:
            while True:
                # Keep connection alive
                await websocket.receive_text() 
        except WebSocketDisconnect:
            manager.disconnect(websocket, user_id)
            
    except Exception as e:
        logger.error(f"WebSocket handler error: {e}")
        try:
            await websocket.close(code=1008)
        except:
            pass
