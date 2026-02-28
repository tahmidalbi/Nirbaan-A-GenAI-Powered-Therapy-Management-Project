# Fear Ladder Education Testing Guide

This guide helps you test the Fear Ladder AI Education feature end-to-end.

## Prerequisites

1. Backend server running on `http://localhost:8000`
2. Frontend server running on `http://localhost:5174`
3. Database table created (run `setup_fear_ladder_education.bat`)
4. `react-markdown` package installed in frontend
5. Valid OPENAI_API_KEY in backend `.env`
6. At least one therapist and one patient in the database

## Test Scenarios

### Test 1: First-Time Education Generation

**Steps:**
1. Log in as a patient
2. Navigate to: Patient Dashboard → OCD Tools → Fear Ladder → Education
3. You should see an empty state with "Generate Education" button
4. Click "Generate Education"
5. Wait for generation (10-30 seconds depending on content)

**Expected Results:**
- ✓ Loading spinner displays during generation
- ✓ Content appears with sections, titles, and formatted text
- ✓ Key points are displayed as bulleted lists with checkmarks
- ✓ Sources section shows knowledge base or web sources
- ✓ Disclaimer appears at the bottom
- ✓ "Regenerate Education" button replaces "Generate Education"

**What to Check:**
- Content is properly formatted (not raw JSON or chat-like)
- Markdown is rendered (bold, lists, etc.)
- Sections have titles and content
- Sources have clickable links (if web sources)

---

### Test 2: Cached Content Retrieval

**Steps:**
1. After Test 1, click "Back" button
2. Navigate back to Education section

**Expected Results:**
- ✓ Content loads instantly (from cache)
- ✓ Same content as before is displayed
- ✓ No loading delay
- ✓ "Regenerate Education" button is visible

**Verification:**
- Check browser Network tab: `/education/fear-ladder/patient/my-education` returns cached data
- Content matches what was generated in Test 1

---

### Test 3: Content Regeneration

**Steps:**
1. From cached content view (Test 2)
2. Click "Regenerate Education" button
3. Wait for generation

**Expected Results:**
- ✓ "Regenerating..." text appears on button
- ✓ Loading state does NOT show (content stays visible)
- ✓ New content replaces old content
- ✓ Content structure is similar but text may differ
- ✓ Database is updated with new content

**Verification:**
- Content is different from Test 1 (check by reading a few lines)
- New timestamp in database (`updated_at` field)

---

### Test 4: Logout and Return

**Steps:**
1. After generating education (Tests 1-3)
2. Click "Logout"
3. Log in again as the same patient
4. Navigate to Education section

**Expected Results:**
- ✓ Education content loads immediately
- ✓ Shows the LAST generated content (from most recent generation)
- ✓ No need to regenerate
- ✓ Patient sees their previous education

---

### Test 5: Different Patients

**Steps:**
1. Log in as Patient A, generate education
2. Log out
3. Log in as Patient B from a different therapist
4. Navigate to Education section

**Expected Results:**
- ✓ Patient B sees empty state (no education yet)
- ✓ Patient B's generation uses THEIR therapist's knowledge base
- ✓ Content may differ from Patient A's content
- ✓ Each patient has independent cached education

---

### Test 6: Error Handling

**Scenario A: Backend Down**
1. Stop backend server
2. Try to generate education

**Expected Results:**
- ✓ Error message appears
- ✓ UI doesn't crash
- ✓ User can try again after backend restarts

**Scenario B: No Therapist Resources**
1. Use a patient whose therapist has NO uploaded resources
2. Generate education

**Expected Results:**
- ✓ Still generates content (uses web search fallback if enabled)
- ✓ Sources show "web" type instead of "kb" type
- ✓ OR shows error if web search is disabled

---

## Backend Testing (API)

### Test API Endpoints Directly

#### 1. Get Cached Education (should fail first time)
```bash
curl -H "Authorization: Bearer <patient_token>" \
  http://localhost:8000/education/fear-ladder/patient/my-education
```

**Expected:** 404 if no education, 200 with JSON if exists

#### 2. Generate Education
```bash
curl -X POST -H "Authorization: Bearer <patient_token>" \
  "http://localhost:8000/education/fear-ladder/patient/generate?regenerate=false"
```

**Expected:** 200 with education JSON

#### 3. Regenerate Education
```bash
curl -X POST -H "Authorization: Bearer <patient_token>" \
  "http://localhost:8000/education/fear-ladder/patient/generate?regenerate=true"
```

**Expected:** 200 with new education JSON

#### 4. Therapist Preview (therapist token)
```bash
curl -H "Authorization: Bearer <therapist_token>" \
  http://localhost:8000/education/fear-ladder/therapist/preview
```

**Expected:** 200 with education JSON (not cached)

---

## Database Verification

### Check if table exists
```sql
SELECT * FROM fear_ladder_education_cache;
```

### Check specific patient's education
```sql
SELECT 
  patient_id, 
  topic, 
  reading_level,
  created_at,
  updated_at,
  LENGTH(sections_json) as sections_size
FROM fear_ladder_education_cache 
WHERE patient_id = <patient_id>;
```

### View full content
```sql
SELECT 
  patient_id,
  sections_json,
  sources_json,
  disclaimer
FROM fear_ladder_education_cache 
WHERE patient_id = <patient_id>;
```

---

## Common Issues & Solutions

### Issue: "No education generated yet" persists after generation

**Causes:**
- Generation failed silently
- Database save failed
- Wrong patient_id

**Solutions:**
1. Check backend logs for errors
2. Query database to see if record exists
3. Verify patient is logged in correctly
4. Check database connection

---

### Issue: Content shows as raw JSON or chat-like

**Causes:**
- ReactMarkdown not rendering
- CSS not loaded
- Wrong data structure

**Solutions:**
1. Verify `react-markdown` is installed
2. Check browser console for errors
3. Inspect network response structure
4. Clear browser cache

---

### Issue: "Failed to generate education" error

**Causes:**
- OpenAI API key invalid/missing
- LangGraph workflow error
- No therapist resources (and web search disabled)

**Solutions:**
1. Check `.env` has valid `OPENAI_API_KEY`
2. Check backend logs for specific error
3. Verify therapist has uploaded resources
4. Enable web search fallback in config

---

### Issue: Slow generation (>60 seconds)

**Causes:**
- Large knowledge base
- Web search enabled and slow
- API rate limits

**Solutions:**
1. Check if web search is being used (slower)
2. Optimize knowledge base size (reduce to most relevant docs)
3. Check OpenAI API status
4. Consider caching more aggressively

---

## Performance Benchmarks

**Generation (First Time):**
- With KB only: 10-20 seconds
- With web search: 20-40 seconds

**Cached Retrieval:**
- <1 second (instant)

**Regeneration:**
- Same as first-time generation

---

## Success Criteria

✅ All tests pass without errors
✅ Content is properly formatted and readable
✅ Caching works correctly (instant load on return)
✅ Different patients have independent education
✅ Regeneration produces new content
✅ Sources are displayed with proper attribution
✅ Mobile responsive (test on small screen)

---

## Rollback Plan

If issues occur in production:

1. **Disable feature in frontend:**
   - Comment out route in `AppRoutes.jsx`
   - Hide navigation link to education page

2. **Disable backend endpoint:**
   - Comment out router inclusion in `main.py`

3. **Rollback database:**
   ```sql
   DROP TABLE fear_ladder_education_cache;
   ```

4. **Restore previous version:**
   - Git revert to previous commit
   - Redeploy backend and frontend
