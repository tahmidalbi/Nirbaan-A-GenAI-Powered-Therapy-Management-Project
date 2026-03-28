# Video Call Component Documentation

## Overview

A complete WebRTC video calling system for therapy sessions with WebSocket signaling.

## Files Created

### Frontend Components

1. **VideoCall.jsx** - Main WebRTC video call component
   - Location: `frontend/src/components/VideoCall.jsx`
   - Handles video calling, WebSocket communication, and WebRTC peer connections

2. **VideoCall.css** - Component styling
   - Location: `frontend/src/components/VideoCall.css`
   - Responsive design with professional UI

3. **VideoSession.jsx** - Example integration page
   - Location: `frontend/src/pages/VideoSession.jsx`
   - Demonstrates how to use the VideoCall component

4. **VideoSession.css** - Page styling
   - Location: `frontend/src/pages/VideoSession.css`

5. **therapy-session.api.js** - API helper functions
   - Location: `frontend/src/api/therapy-session.api.js`
   - Functions for session management

## Component Usage

### Basic Usage

```jsx
import VideoCall from '../components/VideoCall';

<VideoCall
  userId={123}
  userType="therapist"
  targetUserId={456}
  onCallEnd={() => console.log('Call ended')}
/>
```

### Props

- **userId** (number, required) - Current user's ID
- **userType** (string, required) - "therapist" or "patient"
- **targetUserId** (number, optional) - For therapist to call specific patient
- **onCallEnd** (function, optional) - Callback when call ends

## Features

### ✅ Implemented

- **WebSocket Signaling**: Real-time call signaling via WebSocket
- **WebRTC Video**: Peer-to-peer video connection using RTCPeerConnection
- **Local Video**: Display user's own video feed
- **Remote Video**: Display peer's video feed
- **Call Initiation**: Therapists can start calls
- **Call Accept/Reject**: Patients can accept or reject incoming calls
- **Call Controls**:
  - Mute/Unmute microphone
  - Enable/Disable camera
  - End call
- **Call States**: idle, calling, incoming, connected, ended
- **Error Handling**: Connection errors, permission errors, etc.
- **Responsive Design**: Works on desktop and mobile devices

### 🎯 Call Flow

#### Therapist Initiates Call

1. Therapist clicks "Start Call"
2. WebSocket sends `initiate_call` message to backend
3. Backend checks if patient is online and available
4. Patient receives `incoming_call` notification
5. Patient sees incoming call modal with Accept/Reject options

#### Patient Accepts Call

1. Patient clicks "Accept"
2. WebSocket sends `accept_call` message
3. Backend notifies both parties
4. Both create WebRTC peer connections
5. Media streams are exchanged
6. Video call is active

#### Patient Rejects Call

1. Patient clicks "Reject"
2. WebSocket sends `reject_call` message
3. Backend notifies therapist
4. Call is cancelled

#### Either Party Ends Call

1. User clicks "End Call"
2. WebSocket sends `end_call` message
3. Both parties are notified
4. Connections are cleaned up
5. Media streams are stopped

## Integration Guide

### 1. Add Routes

```jsx
// In your router configuration
import VideoSession from './pages/VideoSession';

<Route 
  path="/video-session/:userType/:userId/:patientId?" 
  element={<VideoSession />} 
/>
```

### 2. Therapist Integration

```jsx
// In therapist dashboard
import { useNavigate } from 'react-router-dom';

const navigate = useNavigate();
const therapistId = 123;
const patientId = 456;

const startVideoCall = () => {
  navigate(`/video-session/therapist/${therapistId}/${patientId}`);
};

<button onClick={startVideoCall}>
  Start Video Call with Patient
</button>
```

### 3. Patient Integration

```jsx
// In patient dashboard
import { useNavigate } from 'react-router-dom';

const navigate = useNavigate();
const patientId = 456;

const joinVideoCall = () => {
  navigate(`/video-session/patient/${patientId}`);
};

<button onClick={joinVideoCall}>
  Join Video Call
</button>
```

## API Integration

### WebSocket Connection

```javascript
// Automatic connection in VideoCall component
const wsUrl = `ws://127.0.0.1:8000/ws/call/${userId}?user_type=${userType}`;
const ws = new WebSocket(wsUrl);
```

### Message Types

**From Client:**
- `initiate_call` - Start a call
- `accept_call` - Accept incoming call
- `reject_call` - Reject incoming call
- `end_call` - End active call
- `ping` - Keep-alive

**From Server:**
- `connected` - WebSocket connected
- `incoming_call` - Incoming call notification
- `call_initiated` - Call started
- `call_accepted` - Call was accepted
- `call_rejected` - Call was rejected
- `call_started` - Call is active
- `call_ended` - Call has ended
- `error` - Error occurred

## Configuration

### Update Backend URL

If your backend is not at `http://127.0.0.1:8000`, update the WebSocket URL in `VideoCall.jsx`:

```javascript
const wsUrl = `ws://YOUR_BACKEND_URL/ws/call/${userId}?user_type=${userType}`;
```

### STUN/TURN Servers

For production, configure TURN servers in `VideoCall.jsx`:

```javascript
const rtcConfig = {
  iceServers: [
    { urls: 'stun:stun.l.google.com:19302' },
    { 
      urls: 'turn:your-turn-server.com:3478',
      username: 'username',
      credential: 'password'
    }
  ]
};
```

## Browser Requirements

- **WebRTC Support**: Chrome 56+, Firefox 52+, Safari 11+, Edge 79+
- **Permissions**: Camera and microphone access required
- **HTTPS**: Required in production (WebRTC requires secure context)

## Troubleshooting

### Camera/Microphone Not Working

1. Check browser permissions
2. Ensure HTTPS in production
3. Check if device is in use by another app
4. Try different browser

### Connection Issues

1. Check WebSocket connection in browser console
2. Verify backend is running
3. Check firewall settings
4. Ensure STUN/TURN servers are accessible

### Video Not Displaying

1. Check video element refs are properly set
2. Verify media stream is attached
3. Check CSS for display/visibility issues
4. Inspect browser console for errors

## Security Considerations

1. **Authentication**: Integrate with existing auth system
2. **Authorization**: Verify user permissions before allowing calls
3. **HTTPS**: Use secure WebSocket (wss://) in production
4. **TURN Servers**: Use authenticated TURN servers
5. **Data Privacy**: All video/audio is peer-to-peer (not stored on server)

## Future Enhancements

- [ ] Screen sharing
- [ ] Recording functionality
- [ ] Chat during call
- [ ] Multiple participants
- [ ] Network quality indicator
- [ ] Call history and analytics
- [ ] Virtual backgrounds
- [ ] Noise cancellation

## Example Usage in Therapist Dashboard

```jsx
import { useState } from 'react';
import VideoCall from '../components/VideoCall';

const TherapistDashboard = () => {
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [showVideoCall, setShowVideoCall] = useState(false);
  const therapistId = 123; // Get from auth context

  const startCall = (patient) => {
    setSelectedPatient(patient);
    setShowVideoCall(true);
  };

  return (
    <div>
      {showVideoCall ? (
        <VideoCall
          userId={therapistId}
          userType="therapist"
          targetUserId={selectedPatient.id}
          onCallEnd={() => setShowVideoCall(false)}
        />
      ) : (
        <div>
          <h2>My Patients</h2>
          {patients.map(patient => (
            <button key={patient.id} onClick={() => startCall(patient)}>
              Call {patient.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
```

## Support

For issues or questions:
1. Check browser console for errors
2. Verify WebSocket connection
3. Test with different browsers
4. Check backend logs

## License

Part of the Nirbaan Therapy Management Platform.
