# Audio Transcription System Documentation

## Overview

Real-time audio recording and transcription system using React's MediaRecorder API and OpenAI Whisper API. Designed for therapy session documentation.

## Architecture

### Backend
- **TranscriptionService**: Handles OpenAI Whisper API integration
- **API Endpoint**: `/sessions/transcribe-audio` - Receives audio and returns transcription
- **Auto-save**: Optionally saves transcripts to therapy sessions in database

### Frontend
- **AudioRecorder Component**: Captures microphone audio in chunks
- **MediaRecorder API**: Browser-native audio recording
- **Chunked Processing**: Records and transcribes audio in configurable intervals
- **Real-time Display**: Shows transcriptions as they're generated

## Files Created

### Backend

1. **transcription_service.py**
   - Location: `backend/app/therapy_sessions/transcription_service.py`
   - OpenAI Whisper API integration
   - Methods:
     - `transcribe_audio()` - Transcribe from file
     - `transcribe_audio_bytes()` - Transcribe from bytes with temp file

2. **router.py** (updated)
   - Location: `backend/app/therapy_sessions/router.py`
   - New endpoint: `POST /sessions/transcribe-audio`
   - Accepts: audio file (mp3, wav, webm, etc.)
   - Returns: transcribed text
   - Optional: saves to session database

### Frontend

3. **AudioRecorder.jsx**
   - Location: `frontend/src/components/AudioRecorder.jsx`
   - Full-featured audio recording component
   - Features:
     - Start/Pause/Resume/Stop recording
     - Automatic chunked transcription
     - Real-time transcription display
     - Transcript history
     - Error handling

4. **AudioRecorder.css**
   - Location: `frontend/src/components/AudioRecorder.css`
   - Professional UI with animations
   - Responsive design

5. **AudioTranscription.jsx**
   - Location: `frontend/src/pages/AudioTranscription.jsx`
   - Example integration page
   - Shows saved session transcripts
   - Demonstrates component usage

6. **AudioTranscription.css**
   - Location: `frontend/src/pages/AudioTranscription.css`
   - Page styling

7. **therapy-session.api.js** (updated)
   - Location: `frontend/src/api/therapy-session.api.js`
   - New function: `transcribeAudio()`

## Component Usage

### Basic Usage

```jsx
import AudioRecorder from '../components/AudioRecorder';

<AudioRecorder
  sessionId={123}
  speaker="therapist"
  language="en"
  onTranscription={(text, transcriptId) => console.log(text)}
  autoSave={true}
  chunkDuration={5000}
/>
```

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `sessionId` | number | null | Therapy session ID for auto-saving |
| `speaker` | string | 'therapist' | "therapist" or "patient" |
| `language` | string | 'en' | Language code (en, es, fr, etc.) |
| `onTranscription` | function | null | Callback when transcription completes |
| `autoSave` | boolean | false | Auto-save transcripts to session |
| `chunkDuration` | number | 5000 | Recording chunk duration in ms (0 = manual) |

## Features

### ✅ Audio Recording
- **Browser-native**: Uses MediaRecorder API
- **Format Detection**: Automatically uses best supported format (webm, ogg, mp4)
- **Audio Quality**: 128kbps, with echo cancellation and noise suppression
- **Controls**: Start, Pause, Resume, Stop
- **Timer**: Shows recording duration

### ✅ Chunked Transcription
- **Automatic Processing**: Transcribes audio at configurable intervals
- **Real-time Display**: Shows transcriptions as they arrive
- **Continuous Recording**: Seamlessly continues recording between chunks

### ✅ Transcription Display
- **Latest Transcription**: Shows most recent transcription prominently
- **History**: Displays all transcriptions with timestamps
- **Scrollable List**: Easy navigation through long sessions

### ✅ Database Integration
- **Auto-save**: Optionally saves to TherapyTranscript table
- **Session Linking**: Associates with therapy sessions
- **Speaker Tracking**: Records who spoke (therapist/patient)

## API Integration

### Backend Endpoint

**POST** `/sessions/transcribe-audio`

**Request:**
```
Content-Type: multipart/form-data

audio: [audio file]
language: "en" (optional)
session_id: 123 (optional)
speaker: "therapist" (optional)
```

**Response:**
```json
{
  "success": true,
  "text": "Transcribed text here",
  "transcript_id": 456
}
```

### Supported Audio Formats
- mp3, mp4, mpeg, mpga, m4a, wav, webm

### Authentication
Requires Bearer token in Authorization header.

## Configuration

### Environment Variables

Add to backend `.env`:
```env
OPENAI_API_KEY=your_api_key_here
```

### Backend URL

Update in `AudioRecorder.jsx` if needed:
```javascript
const response = await fetch('http://YOUR_BACKEND_URL/sessions/transcribe-audio', {
  // ...
});
```

### Recording Settings

Adjust in component:
```javascript
<AudioRecorder
  chunkDuration={10000}  // 10 seconds
  language="en"          // Language code
  autoSave={true}        // Auto-save to DB
/>
```

## Integration Examples

### In Therapist Dashboard

```jsx
import AudioRecorder from '../components/AudioRecorder';

const TherapistSession = ({ sessionId }) => {
  const handleTranscript = (text, transcriptId) => {
    console.log('New transcript:', text);
    // Update UI, send notifications, etc.
  };

  return (
    <div>
      <h2>Session Notes</h2>
      <AudioRecorder
        sessionId={sessionId}
        speaker="therapist"
        language="en"
        onTranscription={handleTranscript}
        autoSave={true}
        chunkDuration={10000}
      />
    </div>
  );
};
```

### In Video Call Component

```jsx
import VideoCall from '../components/VideoCall';
import AudioRecorder from '../components/AudioRecorder';

const VideoSession = ({ sessionId, userId, userType }) => {
  return (
    <div className="video-session">
      <VideoCall 
        userId={userId} 
        userType={userType} 
      />
      
      <AudioRecorder
        sessionId={sessionId}
        speaker={userType}
        autoSave={true}
        chunkDuration={15000}
      />
    </div>
  );
};
```

## Browser Compatibility

### MediaRecorder API Support
- ✅ Chrome 47+
- ✅ Firefox 25+
- ✅ Safari 14+
- ✅ Edge 79+

### Required Permissions
- Microphone access
- HTTPS in production (required for getUserMedia)

## Error Handling

### Common Issues

1. **Microphone Access Denied**
   - Check browser permissions
   - Ensure HTTPS in production
   - Verify no other apps using microphone

2. **Transcription Failed**
   - Check OPENAI_API_KEY is set
   - Verify API key is valid
   - Check audio format is supported
   - Ensure audio is not silent/corrupted

3. **Auto-save Failed**
   - Verify session exists
   - Check speaker is valid ("therapist" or "patient")
   - Ensure user is authenticated

### Error Display

Component shows error messages:
```jsx
{error && (
  <div className="error-message">
    {error}
  </div>
)}
```

## Cost Considerations

### OpenAI Whisper API Pricing
- Charged per minute of audio
- Current rate: $0.006/minute (as of 2024)
- 10-minute session ≈ $0.06

### Optimization Tips
1. **Longer Chunks**: Reduce API calls by increasing `chunkDuration`
2. **On-Demand**: Set `chunkDuration={0}` for manual transcription
3. **Conditional Recording**: Only record when needed
4. **Local Storage**: Cache transcriptions to avoid re-processing

## Performance

### Audio Processing
- Chunks processed asynchronously
- Non-blocking UI
- Minimal memory footprint

### Network
- FormData used for efficient upload
- Auth token cached from localStorage
- Compression handled by browser

## Security

### Authentication
- Bearer token required for API calls
- Token stored in localStorage
- Session validation on backend

### Data Privacy
- Audio not stored on backend (only transcription)
- Temporary files deleted immediately
- Transcriptions associated with sessions for audit trail

## Testing

### Manual Testing

1. **Start Recording** → Should see recording indicator
2. **Speak** → Wait for chunk duration
3. **Check Transcription** → Should appear below
4. **Pause/Resume** → Should work seamlessly
5. **Stop** → Should process final chunk

### Backend Testing

```bash
# Test transcription endpoint
curl -X POST http://localhost:8000/sessions/transcribe-audio \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "audio=@test_audio.wav" \
  -F "language=en"
```

## Future Enhancements

- [ ] Real-time streaming transcription
- [ ] Offline recording with batch upload
- [ ] Multiple language detection
- [ ] Speaker diarization (automatic speaker identification)
- [ ] Export transcripts to PDF/DOCX
- [ ] Keyword highlighting
- [ ] Sentiment analysis
- [ ] Summary generation
- [ ] Search within transcripts

## Troubleshooting

### Audio Not Recording
1. Check browser console for errors
2. Verify microphone permissions
3. Test with different browser
4. Check system audio settings

### Transcription Quality Issues
1. Ensure clear audio (reduce background noise)
2. Speak clearly and at moderate pace
3. Check microphone quality
4. Adjust recording settings

### Performance Issues
1. Increase `chunkDuration` to reduce frequency
2. Check network connection
3. Monitor backend logs for API errors
4. Consider limiting history display

## Support

For issues:
1. Check browser console
2. Review backend logs
3. Verify OpenAI API status
4. Test with simple audio file

## License

Part of the Nirbaan Therapy Management Platform.
