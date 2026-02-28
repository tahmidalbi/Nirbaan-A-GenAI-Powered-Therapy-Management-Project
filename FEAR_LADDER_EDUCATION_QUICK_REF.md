# Fear Ladder AI Education - Quick Reference

## 🚀 Quick Start

### Installation
```bash
# Run setup script
setup_fear_ladder_education.bat

# Or manually:
cd frontend && npm install react-markdown
cd ../backend && python create_fear_ladder_education_table.py
```

### Environment Variables
```env
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...  # Optional
```

---

## 📚 API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/education/fear-ladder/patient/my-education` | Patient | Get cached education |
| POST | `/education/fear-ladder/patient/generate?regenerate=false` | Patient | Generate/get education |
| GET | `/education/fear-ladder/therapist/preview` | Therapist | Preview (no cache) |

---

## 🎯 Key Features

✅ **AI-Generated Content**: Uses LangGraph + OpenAI to create personalized education
✅ **Caching**: Stores generated content so patients see it again on return  
✅ **Regeneration**: Patients can request fresh content anytime
✅ **Markdown Support**: Rich text formatting for better readability
✅ **Sources Attribution**: Shows which KB articles or web sources were used
✅ **Mobile Responsive**: Works on all screen sizes

---

## 🔄 User Flow

1. Patient clicks "Generate Education" (first visit)
2. System generates content using therapist's KB
3. Content is cached in database
4. Patient logs out and returns later
5. Content loads instantly from cache
6. Patient can click "Regenerate" for new content

---

## 🗄️ Database

**Table:** `fear_ladder_education_cache`

Key fields:
- `patient_id` (UNIQUE) - One education per patient
- `sections_json` - Array of content sections
- `sources_json` - Attribution sources
- `created_at` / `updated_at` - Timestamps

---

## 🎨 Frontend Components

**Main File:** `frontend/src/pages/PatientFearLadderEducation.jsx`

**Key States:**
- `education` - The content data
- `loading` - Initial fetch
- `generating` - During generation/regeneration
- `error` - Error messages

**Key Functions:**
- `fetchEducation()` - Get cached content
- `handleGenerate(regenerate)` - Generate or regenerate

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| "No education generated yet" | Click "Generate Education" button |
| Content not updating | Use `regenerate=true` parameter |
| Generation fails | Check OPENAI_API_KEY in .env |
| Table doesn't exist | Run `create_fear_ladder_education_table.py` |
| Frontend errors | Install `react-markdown` package |

---

## 📂 File Structure

```
backend/
  app/
    education/
      __init__.py
      fear_ladder/
        __init__.py
        models.py         # Database model
        router.py         # API endpoints
        service.py        # Business logic
        graph.py          # LangGraph workflow
        schemas.py        # Pydantic models
        config.py         # Configuration
        llm.py            # LLM client
        kb.py             # Knowledge base retrieval
        web.py            # Web search
        prompts.py        # LLM prompts
        state.py          # Graph state
  create_fear_ladder_education_table.py

frontend/
  src/
    pages/
      PatientFearLadderEducation.jsx
      PatientFearLadderEducation.css
    api/
      fear-ladder-education.api.js
```

---

## ⚙️ Configuration

**Backend** (`backend/app/education/fear_ladder/config.py`):
- `LLM_MODEL` - OpenAI model to use
- `KB_TOP_K` - Number of KB chunks to retrieve
- `USE_WEB_FALLBACK` - Enable web search if KB insufficient

---

## 🧪 Testing Checklist

- [ ] Generate education for first time
- [ ] Verify content is properly formatted
- [ ] Log out and log back in
- [ ] Verify content loads from cache
- [ ] Regenerate education
- [ ] Verify new content is different
- [ ] Test with different patients
- [ ] Verify each patient has independent cache

---

## 📊 Performance

| Operation | Time |
|-----------|------|
| First generation | 10-30s |
| Cached retrieval | <1s |
| Regeneration | 10-30s |

---

## 🔐 Security

- ✅ Patient can only access their own education
- ✅ Authentication required for all endpoints
- ✅ Therapist preview doesn't affect patient cache
- ✅ SQL injection protected by SQLAlchemy ORM

---

## 📞 Support Files

- `FEAR_LADDER_EDUCATION_SETUP.md` - Full setup guide
- `FEAR_LADDER_EDUCATION_TESTING.md` - Testing guide
- `setup_fear_ladder_education.bat` - Automated setup script

---

## 🚨 Emergency Actions

**Disable feature:**
```python
# In backend/app/main.py - comment out:
# app.include_router(education_fear_ladder_router)
```

**Reset cache:**
```sql
TRUNCATE TABLE fear_ladder_education_cache;
```

**Remove table:**
```sql
DROP TABLE fear_ladder_education_cache;
```

---

## 📝 Notes

- Education is patient-specific but uses therapist's knowledge base
- Content quality depends on therapist's uploaded resources
- Web search fallback can be enabled for better coverage
- Markdown rendering requires `react-markdown` package
- Table must exist before first use (run migration)
