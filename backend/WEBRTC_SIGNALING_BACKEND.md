# Backend WebSocket Handler Example for WebRTC Signaling

This is a reference implementation for handling WebRTC signaling on the backend.

## FastAPI WebSocket Endpoint

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import logging

app = FastAPI()
logger = logging.getLogger(__name__)

# Store active WebSocket connections by session_id
# Structure: {session_id: [websocket1, websocket2]}
active_sessions: Dict[str, List[WebSocket]] = {}

# Store user info for each connection
# Structure: {websocket_id: {"userId": int, "userType": str}}
connection_info: Dict[int, dict] = {}


@app.websocket("/ws/call/{session_id}")
async def video_call_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for WebRTC signaling
    
    Handles:
    - Offer/Answer exchange
    - ICE candidate relay
    - User identification
    - Connection cleanup
    """
    await websocket.accept()
    connection_id = id(websocket)
    
    # Initialize session if not exists
    if session_id not in active_sessions:
        active_sessions[session_id] = []
    
    # Add connection to session
    active_sessions[session_id].append(websocket)
    logger.info(f"New connection to session {session_id}")
    
    # Send connection confirmation
    await websocket.send_json({
        "type": "connected",
        "session_id": session_id,
        "message": "Connected to signaling server"
    })
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            message_type = message.get("type")
            
            logger.info(f"Received {message_type} from session {session_id}")
            
            # Handle different message types
            if message_type == "identify":
                # Store user information
                connection_info[connection_id] = {
                    "userId": message.get("userId"),
                    "userType": message.get("userType")
                }
                logger.info(f"User identified: {connection_info[connection_id]}")
                
                # Notify other users in session about new user
                await broadcast_to_session(
                    session_id, 
                    websocket,
                    {
                        "type": "user-joined",
                        "userId": message.get("userId"),
                        "userType": message.get("userType")
                    }
                )
            
            elif message_type in ["offer", "answer", "ice-candidate"]:
                # Relay WebRTC signaling messages to other peer
                await relay_to_peer(session_id, websocket, message)
            
            elif message_type == "end_call":
                # Notify other peer about call end
                await broadcast_to_session(
                    session_id,
                    websocket,
                    {
                        "type": "call_ended",
                        "reason": "User ended call"
                    }
                )
                break
            
            elif message_type == "reject_call":
                # Notify other peer about call rejection
                await broadcast_to_session(
                    session_id,
                    websocket,
                    {
                        "type": "call_rejected"
                    }
                )
            
            else:
                logger.warning(f"Unknown message type: {message_type}")
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected from session {session_id}")
    
    except Exception as e:
        logger.error(f"Error in WebSocket handler: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    
    finally:
        # Cleanup on disconnect
        if websocket in active_sessions.get(session_id, []):
            active_sessions[session_id].remove(websocket)
        
        if connection_id in connection_info:
            del connection_info[connection_id]
        
        # Notify remaining peers
        await broadcast_to_session(
            session_id,
            None,
            {
                "type": "user-left",
                "message": "Peer disconnected"
            }
        )
        
        # Clean up empty sessions
        if session_id in active_sessions and not active_sessions[session_id]:
            del active_sessions[session_id]
        
        logger.info(f"Cleaned up session {session_id}")


async def relay_to_peer(session_id: str, sender: WebSocket, message: dict):
    """
    Relay signaling message to the other peer in the session
    """
    if session_id not in active_sessions:
        return
    
    for websocket in active_sessions[session_id]:
        if websocket != sender:
            try:
                await websocket.send_json(message)
                logger.info(f"Relayed {message['type']} to peer")
            except Exception as e:
                logger.error(f"Failed to relay message: {e}")


async def broadcast_to_session(session_id: str, sender: WebSocket, message: dict):
    """
    Broadcast message to all peers in session except sender
    """
    if session_id not in active_sessions:
        return
    
    for websocket in active_sessions[session_id]:
        if websocket != sender:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to broadcast message: {e}")


# Optional: Add session statistics endpoint
@app.get("/api/sessions/active")
async def get_active_sessions():
    """Get statistics about active video sessions"""
    return {
        "total_sessions": len(active_sessions),
        "sessions": {
            session_id: len(connections)
            for session_id, connections in active_sessions.items()
        }
    }
```

## Message Flow Examples

### 1. User Identification
```json
Client → Server:
{
  "type": "identify",
  "userId": 123,
  "userType": "therapist"
}

Server → Other Clients:
{
  "type": "user-joined",
  "userId": 123,
  "userType": "therapist"
}
```

### 2. Offer Exchange
```json
Therapist → Server:
{
  "type": "offer",
  "offer": {
    "type": "offer",
    "sdp": "v=0..."
  }
}

Server → Patient:
{
  "type": "offer",
  "offer": {
    "type": "offer",
    "sdp": "v=0..."
  }
}
```

### 3. Answer Exchange
```json
Patient → Server:
{
  "type": "answer",
  "answer": {
    "type": "answer",
    "sdp": "v=0..."
  }
}

Server → Therapist:
{
  "type": "answer",
  "answer": {
    "type": "answer",
    "sdp": "v=0..."
  }
}
```

### 4. ICE Candidate Exchange
```json
Either Peer → Server:
{
  "type": "ice-candidate",
  "candidate": {
    "candidate": "candidate:...",
    "sdpMLineIndex": 0,
    "sdpMid": "0"
  }
}

Server → Other Peer:
{
  "type": "ice-candidate",
  "candidate": {
    "candidate": "candidate:...",
    "sdpMLineIndex": 0,
    "sdpMid": "0"
  }
}
```

## Integration with Existing Backend

If you already have a therapy session management system:

```python
from app.therapy_sessions.repo import get_session_by_id
from app.auth.dependencies import get_current_user

@app.websocket("/ws/call/{session_id}")
async def video_call_websocket(
    websocket: WebSocket, 
    session_id: int,
    token: str = None  # Pass token as query param
):
    # Validate session exists
    session = await get_session_by_id(session_id)
    if not session:
        await websocket.close(code=1008, reason="Session not found")
        return
    
    # Authenticate user (if needed)
    if token:
        user = await verify_jwt_token(token)
        if not user:
            await websocket.close(code=1008, reason="Invalid token")
            return
    
    # Rest of WebSocket handler...
    await websocket.accept()
    # ... continue with signaling
```

## Testing the WebSocket

### Using JavaScript
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/call/123');

ws.onopen = () => {
  console.log('Connected');
  ws.send(JSON.stringify({
    type: 'identify',
    userId: 1,
    userType: 'therapist'
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
};
```

### Using Python
```python
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws/call/123"
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({
            "type": "identify",
            "userId": 1,
            "userType": "therapist"
        }))
        
        response = await websocket.recv()
        print(f"Received: {response}")

asyncio.run(test_websocket())
```

## Deployment Considerations

### Production Settings

1. **Use WSS (Secure WebSocket)**
   ```python
   # Use with HTTPS/SSL
   wss://your-domain.com/ws/call/{session_id}
   ```

2. **Add Connection Limits**
   ```python
   # Limit connections per session
   MAX_CONNECTIONS_PER_SESSION = 2
   
   if len(active_sessions.get(session_id, [])) >= MAX_CONNECTIONS_PER_SESSION:
       await websocket.close(code=1008, reason="Session full")
       return
   ```

3. **Add Timeout Handling**
   ```python
   # Close inactive connections
   TIMEOUT_SECONDS = 300  # 5 minutes
   
   async def check_timeout():
       # Implementation to close stale connections
       pass
   ```

4. **Add Logging and Monitoring**
   ```python
   import logging
   
   logger = logging.getLogger(__name__)
   logger.setLevel(logging.INFO)
   
   # Log all signaling events
   logger.info(f"Session {session_id}: Offer sent")
   ```

## Troubleshooting

### Issue: Messages not being relayed
- Check if both peers are in the same session_id
- Verify WebSocket connections are established
- Check server logs for errors

### Issue: Connection drops frequently
- Check server timeout settings
- Verify network stability
- Implement reconnection logic

### Issue: High latency
- Check server resources
- Consider using a dedicated signaling server
- Optimize message processing

## Next Steps

1. Implement this WebSocket handler in your backend
2. Test with the frontend VideoCall component
3. Add authentication and authorization
4. Implement session management
5. Add monitoring and logging
6. Deploy with WSS in production
