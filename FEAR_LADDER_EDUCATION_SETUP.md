# Fear Ladder AI Education Setup Guide

This guide explains how to set up and use the AI-powered Fear Ladder Education feature for patients.

## Overview

The Fear Ladder Education feature provides AI-generated, personalized educational content about fear ladders (exposure hierarchies) in ERP therapy for OCD. The content is:
- **Generated once** per patient using their therapist's knowledge base
- **Cached** in the database so patients see the same content when they return
- **Regeneratable** if the patient wants fresh content

## Architecture

### Backend Components

1. **Database Model** (`backend/app/education/fear_ladder/models.py`)
   - `FearLadderEducationCache` table stores generated content per patient
   - Includes: topic, sections (JSON), sources (JSON), disclaimer

2. **Router** (`backend/app/education/fear_ladder/router.py`)
   - `GET /education/fear-ladder/patient/my-education` - Get cached education
   - `POST /education/fear-ladder/patient/generate?regenerate=false` - Generate/get education
   - `GET /education/fear-ladder/therapist/preview` - Therapist preview

3. **Service** (`backend/app/education/fear_ladder/service.py`)
   - Calls LangGraph workflow to generate content
   - Uses therapist's knowledge base and/or web search

4. **LangGraph Workflow** (`backend/app/education/fear_ladder/graph.py`)
   - Multi-agent system: KB retrieval → Judge → Web search (if needed) → LLM generation

### Frontend Components

1. **API Functions** (`frontend/src/api/fear-ladder-education.api.js`)
   - `getMyEducation()` - Fetch cached education
   - `generateEducation(regenerate)` - Generate or regenerate education

2. **Page Component** (`frontend/src/pages/PatientFearLadderEducation.jsx`)
   - Displays AI-generated content in proper educational format
   - Generate/Regenerate buttons
   - Markdown rendering for rich text
   - Sources display with links

3. **Styling** (`frontend/src/pages/PatientFearLadderEducation.css`)
   - Professional educational layout
   - Loading, empty, and error states
   - Responsive design

## Setup Instructions

### 1. Install Dependencies

#### Backend
The backend dependencies should already be in `requirements.txt`. If not, ensure these are included:
```bash
langchain
langchain-openai
langgraph
tavily-python
```

#### Frontend
Install the react-markdown package:
```bash
cd frontend
npm install react-markdown
```

### 2. Create Database Table

Run the migration script to create the education cache table:
```bash
cd backend
python create_fear_ladder_education_table.py
```

### 3. Environment Variables

Ensure these are set in your backend `.env` file:
```env
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key  # Optional, for web search
```

### 4. Start The Servers

#### Backend
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

#### Frontend
```bash
cd frontend
npm run dev
```

## User Flow

### Patient Experience

1. **First Visit**
   - Patient navigates to Fear Ladder Hub → Education
   - Sees empty state with "Generate Education" button
   - Clicks "Generate Education"
   - System generates personalized content using their therapist's knowledge base
   - Content is displayed in educational format with sections, key points, and sources

2. **Returning Visit**
   - Patient navigates to Education section
   - Automatically sees their previously generated content (cached)
   - Can click "Regenerate Education" to get fresh content if desired

3. **Content Structure**
   - **Topic**: Main title (e.g., "Fear ladder (exposure hierarchy) in ERP for OCD")
   - **Sections**: Multiple educational sections with:
     - Title
     - Markdown-formatted content
     - Key points (bulleted list)
   - **Sources**: List of knowledge base articles or web links used
   - **Disclaimer**: Important medical/therapeutic disclaimer

## API Endpoints

### Patient Endpoints

#### Get Cached Education
```http
GET /education/fear-ladder/patient/my-education
Authorization: Bearer <patient_token>
```

**Response:**
```json
{
  "module": "fear_ladder_education",
  "topic": "Fear ladder (exposure hierarchy) in ERP for OCD",
  "reading_level": "simple",
  "sections": [
    {
      "id": "intro",
      "title": "What is a Fear Ladder?",
      "content_markdown": "A fear ladder...",
      "key_points": ["Point 1", "Point 2"]
    }
  ],
  "sources": [
    {
      "type": "kb",
      "title": "Understanding ERP",
      "resource_id": 123
    }
  ],
  "disclaimer": "This content is for educational purposes..."
}
```

#### Generate/Regenerate Education
```http
POST /education/fear-ladder/patient/generate?regenerate=false
Authorization: Bearer <patient_token>
```

**Parameters:**
- `regenerate` (boolean): 
  - `false` (default): Returns cached if exists, generates if not
  - `true`: Always generates new content and updates cache

### Therapist Endpoint

#### Preview Education
```http
GET /education/fear-ladder/therapist/preview
Authorization: Bearer <therapist_token>
```

Generates education preview without caching (for testing).

## Caching Logic

The system implements intelligent caching:

1. **First Generation**: Content is generated and saved to database
2. **Subsequent Requests**: Cached content is returned instantly
3. **Manual Regeneration**: Patient can explicitly request new content
4. **One Cache Per Patient**: Only stores the latest generated education

## Technical Details

### Database Schema

```sql
CREATE TABLE fear_ladder_education_cache (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER UNIQUE NOT NULL,  -- One per patient
    topic VARCHAR NOT NULL,
    reading_level VARCHAR DEFAULT 'simple',
    sections_json JSON NOT NULL,  -- Array of sections
    sources_json JSON NOT NULL,   -- Array of sources
    disclaimer TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW() ON UPDATE NOW(),
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);
```

### LangGraph Workflow

1. **Input**: Patient's therapist_id and topic
2. **KB Retrieval**: Retrieve relevant content from therapist's knowledge base
3. **Judge**: LLM determines if KB content is sufficient
4. **Web Search** (optional): If KB insufficient and enabled, search web
5. **Generate**: LLM creates structured educational content
6. **Output**: JSON with sections, sources, disclaimer

## Troubleshooting

### "No education generated yet" Error
- First-time user: Click "Generate Education"
- Check backend logs for generation errors
- Verify therapist has knowledge base content

### Content Not Updating
- Make sure to click "Regenerate Education" (not just "Generate")
- Check `regenerate=true` parameter is being sent

### Styling Issues
- Clear browser cache
- Check PatientFearLadderEducation.css is loaded
- Verify react-markdown is installed

### Backend Errors
- Check OPENAI_API_KEY is valid
- Ensure database table exists (run migration)
- Check therapist has resources in knowledge base

## Future Enhancements

- [ ] Support for multiple languages (Bangla)
- [ ] Difficulty level selection (simple/advanced)
- [ ] Personalization based on patient's conditions
- [ ] Export to PDF functionality
- [ ] Progress tracking (sections read)
- [ ] Feedback mechanism (helpful/not helpful)

## Support

For issues or questions, check:
1. Backend logs: `uvicorn` console output
2. Frontend console: Browser DevTools
3. Database state: Query `fear_ladder_education_cache` table
4. API responses: Network tab in DevTools
