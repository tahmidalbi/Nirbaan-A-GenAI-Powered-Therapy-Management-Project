"""
Test WebRTC signaling WebSocket endpoint

This script tests the session-based WebRTC signaling endpoint.
It simulates two users connecting to the same session and exchanging messages.

Usage:
    python test_webrtc_signaling.py
"""

import asyncio
import websockets
import json
import sys

async def recv_message_of_type(websocket, target_type, timeout=5.0):
    """Receive messages until we get one of the target type(s)."""
    target_types = target_type if isinstance(target_type, list) else [target_type]
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            raise TimeoutError(f"Timed out waiting for {target_types}")
        response = await asyncio.wait_for(websocket.recv(), timeout=remaining)
        data = json.loads(response)
        if data.get("type") in target_types:
            return data
        # Log and discard non-target messages
        print(f"  (skipped message: {data.get('type')})")


async def test_user(session_id: str, user_id: int, user_type: str, is_caller: bool):
    """Simulate a user connecting to the WebRTC signaling endpoint."""
    uri = f"ws://127.0.0.1:8000/api/therapy-sessions/ws/signaling/{session_id}"
    
    print(f"\n[User {user_id}] Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            # Receive connection confirmation
            data = json.loads(await websocket.recv())
            print(f"[User {user_id}] {data}")
            
            # Send identify message
            identify_msg = {
                "type": "identify",
                "userId": user_id,
                "userType": user_type
            }
            await websocket.send(json.dumps(identify_msg))
            print(f"[User {user_id}] Sent identify")
            
            if is_caller:
                # Wait for peer to join before sending offer
                await asyncio.sleep(2)
                
                # Send offer
                offer_msg = {
                    "type": "offer",
                    "offer": {
                        "type": "offer",
                        "sdp": "v=0\r\no=- 123456789 2 IN IP4 127.0.0.1\r\ns=WebRTC Test\r\n..."
                    }
                }
                await websocket.send(json.dumps(offer_msg))
                print(f"[User {user_id}] Sent offer")
                
                # Wait for answer
                data = await recv_message_of_type(websocket, "answer")
                print(f"[User {user_id}] Received answer: sdp={data['answer']['sdp'][:40]}...")
                
                # Send ICE candidate
                ice_msg = {
                    "type": "ice-candidate",
                    "candidate": {
                        "candidate": "candidate:842163049 1 udp 2113937151 192.168.1.100 54321 typ host",
                        "sdpMLineIndex": 0,
                        "sdpMid": "0"
                    }
                }
                await websocket.send(json.dumps(ice_msg))
                print(f"[User {user_id}] Sent ICE candidate")
                
                # Wait for ICE candidate from peer
                data = await recv_message_of_type(websocket, "ice-candidate")
                print(f"[User {user_id}] Received ICE candidate")
                
            else:
                # Wait for offer from caller
                print(f"[User {user_id}] Waiting for offer...")
                data = await recv_message_of_type(websocket, "offer", timeout=10.0)
                print(f"[User {user_id}] Received offer: sdp={data['offer']['sdp'][:40]}...")
                
                # Send answer
                answer_msg = {
                    "type": "answer",
                    "answer": {
                        "type": "answer",
                        "sdp": "v=0\r\no=- 987654321 2 IN IP4 127.0.0.1\r\ns=WebRTC Test\r\n..."
                    }
                }
                await websocket.send(json.dumps(answer_msg))
                print(f"[User {user_id}] Sent answer")
                
                # Send ICE candidate
                ice_msg = {
                    "type": "ice-candidate",
                    "candidate": {
                        "candidate": "candidate:123456789 1 udp 2113937151 192.168.1.101 54322 typ host",
                        "sdpMLineIndex": 0,
                        "sdpMid": "0"
                    }
                }
                await websocket.send(json.dumps(ice_msg))
                print(f"[User {user_id}] Sent ICE candidate")
                
                # Wait for ICE candidate from caller
                data = await recv_message_of_type(websocket, "ice-candidate")
                print(f"[User {user_id}] Received ICE candidate")
            
            # End call
            await websocket.send(json.dumps({"type": "end_call"}))
            print(f"[User {user_id}] Sent end_call")
            
            print(f"[User {user_id}] *** Test completed successfully! ***")
            
    except Exception as e:
        print(f"[User {user_id}] Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run the test with two simulated users."""
    session_id = "test_session_123"
    
    print("=" * 60)
    print("WebRTC Signaling WebSocket Test")
    print("=" * 60)
    print(f"Testing session: {session_id}")
    print(f"Endpoint: ws://127.0.0.1:8000/api/therapy-sessions/ws/signaling/{session_id}")
    print("\nMake sure the backend server is running!")
    print("=" * 60)
    
    # Create two users
    user1_task = asyncio.create_task(
        test_user(session_id, user_id=1, user_type="therapist", is_caller=True)
    )
    
    # Wait a bit before starting second user
    await asyncio.sleep(1)
    
    user2_task = asyncio.create_task(
        test_user(session_id, user_id=2, user_type="patient", is_caller=False)
    )
    
    # Wait for both to complete
    await asyncio.gather(user1_task, user2_task)
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(0)
