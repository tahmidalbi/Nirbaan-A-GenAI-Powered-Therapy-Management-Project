# Video Session Testing Guide

## Prerequisites

### 1. Database Setup
Ensure the therapy_sessions table exists:
```bash
cd backend
python create_tables.py
```

### 2. Test Data
Create test therapist and patient in your database (if they don't exist):
```bash
# Option 1: Use existing IDs from your database
# Check your database for existing therapist and patient IDs

# Option 2: Create new ones via the API or directly in database
```

### 3. Environment Variables
Create `frontend/.env` file:
```env
VITE_OPENAI_API_KEY=sk-your-actual-openai-api-key-here
```

Get your OpenAI API key from: https://platform.openai.com/api-keys

### 4. Start Both Servers

**Terminal 1 (Backend):**
```bash
cd backend
uvicorn app.main:app --reload
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```

## Testing Steps

### Step 1: Access the Test Page
Open your browser and navigate to:
```
http://localhost:5173/test/video-session
```

### Step 2: Update Test IDs (if needed)
Edit `frontend/src/pages/VideoSessionTest.jsx` lines 12-13:
```javascript
const [therapistId] = useState(1); // Change to existing therapist ID
const [patientId] = useState(1);   // Change to existing patient ID
```

### Step 3: Grant Permissions
When prompted, allow:
- ✅ Camera access
- ✅ Microphone access

### Step 4: Create Session
Click "🚀 Create Session & Start" button

### Step 5: Test Recording
1. Click "🎙️ Start Recording"
2. Speak into your microphone
3. Watch the live transcript appear (with mock data)
4. Click "⏹️ Stop Recording" to stop

### Step 6: Verify Backend Storage
Check that transcript entries are saved in the database:
```bash
# Using psql or your database client
SELECT * FROM therapy_sessions;
SELECT id, transcript FROM therapy_sessions WHERE id = <session_id>;
```

## Testing with Real Speech-to-Text

The component currently uses **mock transcription**. To test with real speech-to-text:

### Option A: OpenAI Whisper API
Update `processAudioChunk()` in VideoSession.jsx:
```javascript
// Convert audio blob to base64 or FormData
const formData = new FormData();
formData.append('file', audioBlob, 'audio.webm');
formData.append('model', 'whisper-1');

const response = await fetch('https://api.openai.com/v1/audio/transcriptions', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${import.meta.env.VITE_OPENAI_API_KEY}`,
  },
  body: formData,
});

const data = await response.json();
const transcribedText = data.text;
```

### Option B: Create Backend Endpoint
Create a backend endpoint that handles audio processing:

**Backend: `app/therapy_sessions/router.py`**
```python
@router.post("/transcribe")
async def transcribe_audio(audio: UploadFile):
    # Use OpenAI Whisper or other STT service
    # Return transcribed text
    pass
```

## Troubleshooting

### Camera/Mic Not Working
- Check browser permissions (click lock icon in address bar)
- Try a different browser (Chrome/Edge recommended)
- Ensure no other app is using camera/mic

### "Session not found" Error
- Verify therapist_id and patient_id exist in database
- Check backend logs for errors

### Emotion Classification Not Working
- Verify VITE_OPENAI_API_KEY is set in .env
- Check browser console for API errors
- Verify OpenAI API key is valid and has credits

### CORS Errors
- Ensure backend is running on port 8000
- Check CORS settings in `backend/app/main.py`

## Expected Behavior

1. **Video stream** displays your webcam feed
2. **Recording button** turns red when active with pulse animation
3. **Processing indicator** appears when analyzing audio
4. **Transcript entries** appear in real-time on the right side
5. **Emotion badges** show classified emotions (happy, sad, anxious, angry, neutral)
6. **Backend database** stores all transcript entries

## API Endpoints Used

- `POST /sessions/` - Create new session
- `POST /sessions/{id}/append-transcript` - Add transcript entry
- `GET /sessions/{id}` - Retrieve session with full transcript

## Demo Without Backend

To test the UI without backend:
1. Comment out the `sessionId` prop in VideoSessionTest.jsx
2. The component will work in "local mode" without API calls
3. Transcript will only be stored in React state (not persisted)
