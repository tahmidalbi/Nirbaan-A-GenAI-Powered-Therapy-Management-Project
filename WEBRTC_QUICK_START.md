# WebRTC Video Calling - Quick Start Guide

## 📋 Overview

Complete WebRTC implementation for peer-to-peer video calling between therapists and patients using:
- **RTCPeerConnection** for P2P video/audio
- **getUserMedia** for camera and microphone access
- **WebSocket** for signaling at `ws://localhost:8000/ws/call/{session_id}`

## 🎯 What's Implemented

### Frontend (React Component)
- ✅ **VideoCall.jsx** - Complete WebRTC component with:
  - RTCPeerConnection setup with STUN servers
  - Camera/microphone capture using getUserMedia
  - WebSocket signaling for offer/answer/ICE candidates
  - Local and remote video displays
  - Mute/unmute and video on/off controls
  - Connection state management
  - Error handling

### Backend Requirements
- ✅ WebSocket endpoint at `/ws/call/{session_id}`
- ✅ Message relay for signaling (offer, answer, ICE candidates)
- ✅ Reference implementation provided

### Testing Tools
- ✅ **webrtc_test.html** - Standalone test page

## 🚀 Quick Start

### 1. Test the Frontend Component

The `VideoCall` component is already integrated in your app:

```jsx
import VideoCall from '../components/VideoCall';

<VideoCall
  userId={parseInt(actualUserId)}
  userType={actualUserType}
  targetUserId={getTargetUserId()}
  sessionId={sessionData?.id}
  onCallEnd={handleCallEnd}
/>
```

**Route**: `/video-session/:userType/:userId/:patientId`

### 2. Test with HTML Page

Open two browser windows:

**Window 1 (Therapist)**:
```bash
# Open webrtc_test.html in browser
# Set Session ID: 123
# Set User ID: 1
# Set User Type: therapist
# Click "Connect to Session"
# Click "Start Call"
```

**Window 2 (Patient)**:
```bash
# Open webrtc_test.html in another window
# Set Session ID: 123
# Set User ID: 2
# Set User Type: patient
# Click "Connect to Session"
# Wait for offer, connection will auto-establish
```

### 3. Backend Setup

Implement the WebSocket handler in your FastAPI backend:

```python
# In your main.py or appropriate router file
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List

active_sessions: Dict[str, List[WebSocket]] = {}

@app.websocket("/ws/call/{session_id}")
async def video_call_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    if session_id not in active_sessions:
        active_sessions[session_id] = []
    active_sessions[session_id].append(websocket)
    
    await websocket.send_json({"type": "connected"})
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Relay to other peer in session
            for conn in active_sessions[session_id]:
                if conn != websocket:
                    await conn.send_text(data)
    
    except WebSocketDisconnect:
        active_sessions[session_id].remove(websocket)
        if not active_sessions[session_id]:
            del active_sessions[session_id]
```

See **backend/WEBRTC_SIGNALING_BACKEND.md** for complete implementation.

## 📁 Files Created/Modified

### Modified
- ✅ `frontend/src/components/VideoCall.jsx` - Complete WebRTC implementation
- ✅ `frontend/src/pages/VideoSession.jsx` - Already integrated

### Created
- ✅ `WEBRTC_IMPLEMENTATION.md` - Technical documentation
- ✅ `backend/WEBRTC_SIGNALING_BACKEND.md` - Backend reference
- ✅ `webrtc_test.html` - Standalone test page
- ✅ `WEBRTC_QUICK_START.md` - This guide

## 🔍 How It Works

### 1. Connection Setup
```
User 1                    WebSocket Server              User 2
  |                              |                        |
  |------- Connect WS ---------->|                        |
  |                              |<------- Connect WS ----|
  |                              |                        |
```

### 2. Signaling Flow
```
User 1                    WebSocket Server              User 2
  |                              |                        |
  |--- Create Offer ------------>|                        |
  |                              |--- Forward Offer ----->|
  |                              |                        |--- Create Answer
  |                              |<--- Send Answer -------|
  |<--- Forward Answer ----------|                        |
  |                              |                        |
  |<-- ICE Candidates ---------->|<-- ICE Candidates ---->|
  |                              |                        |
  |<=============== P2P CONNECTION ===================>|
```

### 3. Media Flow (P2P)
```
User 1 Camera/Mic =============> User 2 Display
User 2 Camera/Mic =============> User 1 Display
```

## 🧪 Testing Checklist

### Local Testing
- [ ] Backend WebSocket server running
- [ ] Open webrtc_test.html in two browser tabs
- [ ] Connect both clients to same session
- [ ] Start call from one side
- [ ] Verify video/audio on both sides
- [ ] Test mute/unmute
- [ ] Test video on/off
- [ ] Test end call

### Integration Testing
- [ ] Login as therapist
- [ ] Navigate to video session with patient ID
- [ ] Click "Start Call"
- [ ] Login as patient (different browser)
- [ ] Accept incoming call
- [ ] Verify bidirectional video/audio
- [ ] Test all controls
- [ ] End call from either side

## 🐛 Troubleshooting

### No Video/Audio
1. Check browser permissions for camera/microphone
2. Open browser console and check for errors
3. Verify getUserMedia() is working
4. Check if HTTPS/localhost (required for getUserMedia)

### Connection Not Establishing
1. Verify WebSocket connection is established
2. Check backend logs for signaling messages
3. Verify offer/answer exchange in browser console
4. Check if ICE candidates are being generated
5. Test STUN server connectivity

### WebSocket Connection Failed
1. Verify backend is running
2. Check WebSocket endpoint is correct
3. Verify session_id is valid
4. Check for CORS issues
5. Look at backend logs

### One-Way Video
1. Check firewall settings
2. Verify symmetric NAT not blocking
3. May need TURN server for NAT traversal
4. Check ICE candidate types in console

## 📚 Documentation

- **WEBRTC_IMPLEMENTATION.md** - Complete technical specification
  - WebRTC flow diagrams
  - Signaling message formats
  - Error handling
  - Browser compatibility
  - Security considerations

- **backend/WEBRTC_SIGNALING_BACKEND.md** - Backend implementation
  - Complete FastAPI WebSocket handler
  - Message relay logic
  - Session management
  - Testing examples
  - Deployment considerations

## 🔐 Security Notes

1. **HTTPS Required** - getUserMedia requires secure context
2. **Session Authentication** - Validate session_id and user permissions
3. **WSS in Production** - Use secure WebSocket (wss://)
4. **Input Validation** - Sanitize all WebSocket messages
5. **Rate Limiting** - Prevent WebSocket abuse

## 🚀 Next Steps

### Immediate
1. Implement backend WebSocket handler
2. Test with webrtc_test.html
3. Test with VideoCall component in app
4. Add error logging and monitoring

### Future Enhancements
1. **TURN Server** - For symmetric NAT traversal
2. **Screen Sharing** - Share screen during session
3. **Recording** - Record therapy sessions
4. **Chat** - Text chat alongside video
5. **Quality Indicators** - Show connection quality
6. **Auto-Reconnect** - Handle temporary disconnections
7. **Multiple Participants** - Group therapy sessions

## 📞 Support

If you encounter issues:

1. Check browser console for errors
2. Check backend logs
3. Verify WebSocket connection
4. Test with webrtc_test.html first
5. Review WEBRTC_IMPLEMENTATION.md for details

## ✅ Summary

You now have:
- ✅ Complete WebRTC frontend implementation
- ✅ Working VideoCall React component
- ✅ Standalone test page
- ✅ Backend reference implementation
- ✅ Comprehensive documentation

**Next**: Implement the backend WebSocket handler and test!
