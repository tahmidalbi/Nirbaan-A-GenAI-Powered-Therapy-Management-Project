from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from app.database.deps import get_db
from app.live_sessions.call_manager import call_manager, session_signaling_manager
from app.therapists.models import Therapist
from app.patients.models import Patient

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Video Call Signaling"])

@router.websocket("/ws/call/{user_id}")
async def websocket_call_endpoint(
    websocket: WebSocket,
    user_id: int,
    user_type: str,  # Query param: "therapist" or "patient"
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for video call signaling.
    
    Message types from client:
    - initiate_call: {"type": "initiate_call", "callee_id": int, "session_id": int (optional)}
    - accept_call: {"type": "accept_call", "caller_id": int}
    - reject_call: {"type": "reject_call", "caller_id": int}
    - end_call: {"type": "end_call"}
    - ping: {"type": "ping"}
    
    Message types to client:
    - incoming_call: {"type": "incoming_call", "caller_id": int, "caller_name": str, "caller_type": str, "session_id": int (optional)}
    - call_accepted: {"type": "call_accepted", "callee_id": int}
    - call_rejected: {"type": "call_rejected", "callee_id": int}
    - call_started: {"type": "call_started", "caller_id": int}
    - call_ended: {"type": "call_ended", "reason": str}
    - error: {"type": "error", "message": str}
    - pong: {"type": "pong"}
    """
    # Verify user exists
    user_name = None
    if user_type == "therapist":
        user = db.query(Therapist).filter(Therapist.id == user_id).first()
        if user:
            user_name = user.name
    elif user_type == "patient":
        user = db.query(Patient).filter(Patient.id == user_id).first()
        if user:
            user_name = user.name
    else:
        await websocket.close(code=1008, reason="Invalid user_type")
        return
    
    if not user:
        await websocket.close(code=1008, reason="User not found")
        return
    
    # Connect the user
    await call_manager.connect(user_id, websocket)
    
    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "user_id": user_id,
            "user_type": user_type
        })
        
        # Listen for messages
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "initiate_call":
                # Only therapists can initiate calls (business logic)
                if user_type != "therapist":
                    await websocket.send_json({
                        "type": "error",
                        "message": "Only therapists can initiate calls"
                    })
                    continue
                
                callee_id = data.get("callee_id")
                if not callee_id:
                    await websocket.send_json({
                        "type": "error",
                        "message": "callee_id is required"
                    })
                    continue
                
                # Get optional session_id
                session_id = data.get("session_id")
                
                # Verify callee is a patient of this therapist
                patient = db.query(Patient).filter(
                    Patient.id == callee_id,
                    Patient.therapist_id == user_id
                ).first()
                
                if not patient:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Patient not found or not assigned to you"
                    })
                    continue
                
                # Initiate the call
                success = await call_manager.initiate_call(
                    caller_id=user_id,
                    callee_id=callee_id,
                    caller_name=user_name,
                    caller_type=user_type,
                    session_id=session_id
                )
                
                if success:
                    await websocket.send_json({
                        "type": "call_initiated",
                        "callee_id": callee_id
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Cannot initiate call. User may be offline or in another call."
                    })
            
            elif message_type == "accept_call":
                caller_id = data.get("caller_id")
                if not caller_id:
                    await websocket.send_json({
                        "type": "error",
                        "message": "caller_id is required"
                    })
                    continue
                
                success = await call_manager.accept_call(
                    callee_id=user_id,
                    caller_id=caller_id
                )
                
                if not success:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Call not found or already ended"
                    })
            
            elif message_type == "reject_call":
                caller_id = data.get("caller_id")
                if not caller_id:
                    await websocket.send_json({
                        "type": "error",
                        "message": "caller_id is required"
                    })
                    continue
                
                success = await call_manager.reject_call(
                    callee_id=user_id,
                    caller_id=caller_id
                )
                
                if success:
                    await websocket.send_json({
                        "type": "call_rejected_confirmation"
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Call not found"
                    })
            
            elif message_type == "end_call":
                success = await call_manager.end_call(user_id)
                
                if success:
                    await websocket.send_json({
                        "type": "call_ended",
                        "reason": "user_ended"
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": "No active call to end"
                    })
            
            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})
            
            elif message_type == "get_status":
                status_info = call_manager.get_call_status(user_id)
                await websocket.send_json({
                    "type": "status",
                    **status_info
                })
            
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                })
    
    except WebSocketDisconnect:
        logger.info(f"User {user_id} disconnected from call signaling")
    except Exception as e:
        logger.error(f"Error in WebSocket for user {user_id}: {e}")
    finally:
        call_manager.disconnect(user_id)


@router.get("/call/status/{user_id}")
async def get_user_call_status(user_id: int):
    """
    Get the call status for a user.
    Returns whether user is online and in a call.
    """
    return {
        "user_id": user_id,
        "online": call_manager.is_user_online(user_id),
        **call_manager.get_call_status(user_id)
    }


@router.websocket("/ws/signaling/{session_id}")
async def websocket_webrtc_signaling(
    websocket: WebSocket,
    session_id: str
):
    """
    WebSocket endpoint for WebRTC signaling by session_id.
    
    This endpoint handles WebRTC peer-to-peer signaling for video calls.
    Multiple users can connect to the same session_id to establish WebRTC connections.
    
    Message types from client:
    - identify: {"type": "identify", "userId": int, "userType": str}
    - offer: {"type": "offer", "offer": {...}}
    - answer: {"type": "answer", "answer": {...}}
    - ice-candidate: {"type": "ice-candidate", "candidate": {...}}
    - end_call: {"type": "end_call"}
    
    Message types to client:
    - connected: {"type": "connected", "session_id": str}
    - user-joined: {"type": "user-joined", "userId": int, "userType": str}
    - offer: {"type": "offer", "offer": {...}}
    - answer: {"type": "answer", "answer": {...}}
    - ice-candidate: {"type": "ice-candidate", "candidate": {...}}
    - call_ended: {"type": "call_ended"}
    - error: {"type": "error", "message": str}
    """
    await session_signaling_manager.connect(session_id, websocket)
    
    conn_key = None  # composite key: '{userType}_{userId}'
    user_id = None
    
    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "message": "Connected to WebRTC signaling server"
        })
        
        # Listen for messages
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            logger.info(f"Session {session_id}: Received {message_type} from {conn_key}")
            
            if message_type == "identify":
                # Register user in session
                user_id = data.get("userId")
                user_type = data.get("userType")
                
                if not user_id or not user_type:
                    await websocket.send_json({
                        "type": "error",
                        "message": "userId and userType are required for identify"
                    })
                    continue
                
                conn_key = session_signaling_manager._key(user_type, user_id)
                
                await session_signaling_manager.register_user(
                    session_id, user_id, user_type, websocket
                )
                
                logger.info(f"{conn_key} identified in session {session_id}")
            
            elif message_type in ["offer", "answer", "ice-candidate"]:
                # Relay WebRTC signaling messages to peers
                if conn_key is None:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Must identify before sending signaling messages"
                    })
                    continue
                
                await session_signaling_manager.relay_to_peers(
                    session_id, conn_key, data
                )
            
            elif message_type == "end_call":
                # Notify other peers that call ended
                if conn_key:
                    await session_signaling_manager.broadcast_to_session(
                        session_id,
                        {"type": "call_ended", "userId": user_id},
                        exclude_key=conn_key
                    )
                break
            
            elif message_type == "get_session_info":
                # Send session information
                info = session_signaling_manager.get_session_info(session_id)
                await websocket.send_json({
                    "type": "session_info",
                    **info
                })
            
            else:
                logger.warning(f"Unknown message type in session {session_id}: {message_type}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected from session {session_id}: {conn_key}")
    except Exception as e:
        logger.error(f"Error in WebRTC signaling for session {session_id}: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        # Cleanup
        if conn_key:
            session_signaling_manager.disconnect(session_id, conn_key)
            
            # Notify remaining users
            await session_signaling_manager.broadcast_to_session(
                session_id,
                {"type": "user-left", "userId": user_id}
            )
        
        logger.info(f"Cleaned up user {user_id} from session {session_id}")


@router.get("/signaling/{session_id}/info")
async def get_session_info(session_id: str):
    """
    Get information about an active WebRTC signaling session.
    Returns user count and connected users.
    """
    return session_signaling_manager.get_session_info(session_id)
