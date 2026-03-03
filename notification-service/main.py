from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from datetime import datetime
import os
import time
import logging
import json
import asyncio
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Notification Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://notification-db:27017/notificationdb")


def get_db():
    client = MongoClient(MONGO_URI)
    return client.notificationdb


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket, user_id: str = None):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if user_id and user_id in self.user_connections:
            if websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)

    async def send_to_user(self, user_id: str, message: dict):
        if user_id in self.user_connections:
            disconnected = []
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)
            for conn in disconnected:
                self.user_connections[user_id].remove(conn)


manager = ConnectionManager()


class NotificationCreate(BaseModel):
    user_id: int
    ride_id: str = None
    type: str
    message: str
    transaction_id: str = None


@app.on_event("startup")
async def startup():
    time.sleep(5)
    logger.info("Notification service started successfully")


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "notification-service",
        "websocket_connections": len(manager.active_connections)
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connection",
            "message": "Connected to RideBook notification service",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
                elif msg.get("type") == "subscribe":
                    user_id = str(msg.get("user_id", ""))
                    if user_id:
                        await manager.connect(websocket, user_id)
                        await websocket.send_json({
                            "type": "subscribed",
                            "user_id": user_id,
                            "message": f"Subscribed to notifications for user {user_id}"
                        })
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.websocket("/ws/{user_id}")
async def websocket_user_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        await websocket.send_json({
            "type": "connection",
            "message": f"Connected to notifications for user {user_id}",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


@app.post("/notify")
async def send_notification(notification: NotificationCreate):
    db = get_db()
    
    doc = {
        "user_id": notification.user_id,
        "ride_id": notification.ride_id,
        "type": notification.type,
        "message": notification.message,
        "transaction_id": notification.transaction_id,
        "read": False,
        "created_at": datetime.utcnow().isoformat()
    }
    
    result = db.notifications.insert_one(doc)
    
    ws_message = {
        "type": "notification",
        "notification_type": notification.type,
        "message": notification.message,
        "ride_id": notification.ride_id,
        "user_id": notification.user_id,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Broadcast to all connected clients
    await manager.broadcast(ws_message)
    # Also try to send to specific user
    await manager.send_to_user(str(notification.user_id), ws_message)
    
    logger.info(f"Notification sent: {notification.type} for user {notification.user_id}")
    
    return {
        "notification_id": str(result.inserted_id),
        "status": "sent",
        "ws_clients": len(manager.active_connections)
    }


@app.get("/notifications")
def get_notifications():
    db = get_db()
    notifications = list(db.notifications.find().sort("created_at", -1).limit(50))
    for n in notifications:
        n["_id"] = str(n["_id"])
    return {"notifications": notifications}


@app.get("/notifications/user/{user_id}")
def get_user_notifications(user_id: int):
    db = get_db()
    notifications = list(db.notifications.find({"user_id": user_id}).sort("created_at", -1))
    for n in notifications:
        n["_id"] = str(n["_id"])
    return {"notifications": notifications}
