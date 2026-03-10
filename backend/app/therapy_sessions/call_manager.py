from typing import Dict, Optional
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)

class CallConnectionManager:
    """Manages WebSocket connections for video call signaling."""
    
    def __init__(self):
        # Store active connections: user_id -> WebSocket
        self.active_connections: Dict[int, WebSocket] = {}
        # Store active calls: caller_id -> callee_id
        self.active_calls: Dict[int, int] = {}
    
    async def connect(self, user_id: int, websocket: WebSocket):
        """Accept and store a WebSocket connection."""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"User {user_id} connected to call signaling")
    
    def disconnect(self, user_id: int):
        """Remove a WebSocket connection."""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"User {user_id} disconnected from call signaling")
        
        # Clean up any active calls
        if user_id in self.active_calls:
            callee_id = self.active_calls[user_id]
            del self.active_calls[user_id]
            # Notify the other party that call ended
            if callee_id in self.active_connections:
                self._send_sync(callee_id, {
                    "type": "call_ended",
                    "reason": "peer_disconnected"
                })
        
        # Check if user was being called
        for caller_id, callee_id in list(self.active_calls.items()):
            if callee_id == user_id:
                del self.active_calls[caller_id]
                if caller_id in self.active_connections:
                    self._send_sync(caller_id, {
                        "type": "call_ended",
                        "reason": "peer_disconnected"
                    })
    
    async def send_message(self, user_id: int, message: dict):
        """Send a message to a specific user."""
        if user_id in self.active_connections:
            try:
                websocket = self.active_connections[user_id]
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
                self.disconnect(user_id)
    
    def _send_sync(self, user_id: int, message: dict):
        """Synchronous send for cleanup operations."""
        if user_id in self.active_connections:
            try:
                import asyncio
                websocket = self.active_connections[user_id]
                asyncio.create_task(websocket.send_json(message))
            except Exception as e:
                logger.error(f"Error in sync send to user {user_id}: {e}")
    
    async def initiate_call(
        self,
        caller_id: int,
        callee_id: int,
        caller_name: str,
        caller_type: str,
        session_id: int = None
    ) -> bool:
        """
        Initiate a call from caller to callee.
        Returns True if call notification was sent, False otherwise.
        """
        # Check if callee is online
        if callee_id not in self.active_connections:
            return False
        
        # Check if either party is already in a call
        if caller_id in self.active_calls or callee_id in self.active_calls:
            return False
        
        # Store the call
        self.active_calls[caller_id] = callee_id
        
        # Notify the callee
        message = {
            "type": "incoming_call",
            "caller_id": caller_id,
            "caller_name": caller_name,
            "caller_type": caller_type
        }
        
        # Include session_id if provided
        if session_id is not None:
            message["session_id"] = session_id
        
        await self.send_message(callee_id, message)
        
        logger.info(f"Call initiated: {caller_id} -> {callee_id}")
        return True
    
    async def accept_call(self, callee_id: int, caller_id: int) -> bool:
        """
        Accept an incoming call.
        Returns True if call was accepted, False if call not found.
        """
        # Verify the call exists
        if caller_id not in self.active_calls:
            return False
        
        if self.active_calls[caller_id] != callee_id:
            return False
        
        # Notify the caller
        await self.send_message(caller_id, {
            "type": "call_accepted",
            "callee_id": callee_id
        })
        
        # Send confirmation to callee
        await self.send_message(callee_id, {
            "type": "call_started",
            "caller_id": caller_id
        })
        
        logger.info(f"Call accepted: {caller_id} <-> {callee_id}")
        return True
    
    async def reject_call(self, callee_id: int, caller_id: int) -> bool:
        """
        Reject an incoming call.
        Returns True if call was rejected, False if call not found.
        """
        # Verify the call exists
        if caller_id not in self.active_calls:
            return False
        
        if self.active_calls[caller_id] != callee_id:
            return False
        
        # Remove the call
        del self.active_calls[caller_id]
        
        # Notify the caller
        await self.send_message(caller_id, {
            "type": "call_rejected",
            "callee_id": callee_id
        })
        
        logger.info(f"Call rejected: {caller_id} -> {callee_id}")
        return True
    
    async def end_call(self, user_id: int) -> bool:
        """
        End an active call.
        Returns True if call was ended, False if no active call.
        """
        other_user_id = None
        
        # Check if user is caller
        if user_id in self.active_calls:
            other_user_id = self.active_calls[user_id]
            del self.active_calls[user_id]
        else:
            # Check if user is callee
            for caller_id, callee_id in list(self.active_calls.items()):
                if callee_id == user_id:
                    other_user_id = caller_id
                    del self.active_calls[caller_id]
                    break
        
        if other_user_id is None:
            return False
        
        # Notify the other party
        await self.send_message(other_user_id, {
            "type": "call_ended",
            "reason": "peer_ended"
        })
        
        logger.info(f"Call ended by user {user_id}")
        return True
    
    def is_user_online(self, user_id: int) -> bool:
        """Check if a user is connected."""
        return user_id in self.active_connections
    
    def get_call_status(self, user_id: int) -> Optional[dict]:
        """Get the call status for a user."""
        if user_id in self.active_calls:
            return {
                "in_call": True,
                "role": "caller",
                "peer_id": self.active_calls[user_id]
            }
        
        for caller_id, callee_id in self.active_calls.items():
            if callee_id == user_id:
                return {
                    "in_call": True,
                    "role": "callee",
                    "peer_id": caller_id
                }
        
        return {"in_call": False}


class SessionSignalingManager:
    """Manages WebRTC signaling connections by session_id.
    
    Uses composite key '{user_type}_{user_id}' so that therapist #1
    and patient #1 (different DB tables, same integer ID) don't collide.
    """
    
    def __init__(self):
        # {session_id: {conn_key: websocket}}  where conn_key = 'therapist_1'
        self.sessions: Dict[str, Dict[str, WebSocket]] = {}
        # {(session_id, conn_key): {"userId": int, "userType": str}}
        self.user_info: Dict[tuple, dict] = {}
    
    @staticmethod
    def _key(user_type: str, user_id) -> str:
        return f"{user_type}_{user_id}"
    
    async def connect(self, session_id: str, websocket: WebSocket):
        """Accept a WebSocket connection for a session."""
        await websocket.accept()
        
        if session_id not in self.sessions:
            self.sessions[session_id] = {}
        
        logger.info(f"New connection to session {session_id}")
    
    async def register_user(
        self, 
        session_id: str, 
        user_id: int, 
        user_type: str, 
        websocket: WebSocket
    ):
        """Register a user in a session."""
        conn_key = self._key(user_type, user_id)
        
        if session_id not in self.sessions:
            self.sessions[session_id] = {}
        
        self.sessions[session_id][conn_key] = websocket
        self.user_info[(session_id, conn_key)] = {
            "userId": user_id,
            "userType": user_type
        }
        
        logger.info(f"{conn_key} registered in session {session_id} (total: {len(self.sessions[session_id])})")
        
        # Notify other users in the session
        await self.broadcast_to_session(
            session_id,
            {"type": "user-joined", "userId": user_id, "userType": user_type},
            exclude_key=conn_key
        )
    
    def disconnect(self, session_id: str, conn_key: str):
        """Remove a user from a session."""
        if session_id in self.sessions and conn_key in self.sessions[session_id]:
            del self.sessions[session_id][conn_key]
            logger.info(f"{conn_key} disconnected from session {session_id}")
            
            if not self.sessions[session_id]:
                del self.sessions[session_id]
                logger.info(f"Session {session_id} cleaned up (empty)")
        
        if (session_id, conn_key) in self.user_info:
            del self.user_info[(session_id, conn_key)]
    
    async def relay_to_peers(
        self, 
        session_id: str, 
        sender_key: str, 
        message: dict
    ):
        """Relay a signaling message to all other peers in the session."""
        if session_id not in self.sessions:
            return
        
        for key, websocket in list(self.sessions[session_id].items()):
            if key != sender_key:
                try:
                    await websocket.send_json(message)
                    logger.info(f"Relayed {message.get('type')} from {sender_key} to {key} in session {session_id}")
                except Exception as e:
                    logger.error(f"Error relaying message to {key}: {e}")
                    self.disconnect(session_id, key)
    
    async def broadcast_to_session(
        self, 
        session_id: str, 
        message: dict,
        exclude_key: str = None
    ):
        """Broadcast a message to all users in a session."""
        if session_id not in self.sessions:
            return
        
        for key, websocket in list(self.sessions[session_id].items()):
            if exclude_key is None or key != exclude_key:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {key}: {e}")
    
    def get_session_info(self, session_id: str) -> dict:
        """Get information about a session."""
        if session_id not in self.sessions:
            return {"exists": False}
        
        users = []
        for key in self.sessions[session_id].keys():
            user_data = self.user_info.get((session_id, key), {})
            users.append({
                "userId": user_data.get("userId"),
                "userType": user_data.get("userType", "unknown")
            })
        
        return {
            "exists": True,
            "session_id": session_id,
            "user_count": len(self.sessions[session_id]),
            "users": users
        }


# Global manager instances
call_manager = CallConnectionManager()
session_signaling_manager = SessionSignalingManager()
