# Progress Tracking Feature - Complete Documentation

## Overview
A comprehensive progress tracking system for therapists and patients with a professional, vintage aesthetic design aligned with the application's green color scheme.

## Design Philosophy
- **Professional Vintage Aesthetic**: Sage green palette with gold accents
- **Typography**: Georgia serif for elegance, uppercase labels with letter-spacing
- **Interactions**: Decorative corners on hover, smooth transitions, floating action buttons
- **Navigation**: Sidebar list → Detail view pattern for both therapist and patient interfaces

## Color Palette
```css
--sage-green: #8B9D83
--deep-sage: #6B7F63
--muted-green: #A8B5A0
--forest-dark: #3D4F3A
--cream-accent: #F4F1E8
--gold-accent: #C5A572
--text-dark: #2C3E50
--text-light: #5A6C7D
--background-main: #E8EDE6
```

---

## Backend Implementation

### Database Models (`backend/app/progress/models.py`)

#### PatientProgress
Stores patient progress reports (initial symptoms + weekly updates)
```python
class PatientProgress(Base):
    id: int (Primary Key)
    patient_id: int (Foreign Key → patients.id)
    initial_condition: str (Initial symptoms text)
    weekly_progress: dict (JSON) # {"week_1": "text", "week_2": "text", ...}
    created_at: datetime
    updated_at: datetime
```

#### TherapistNote
Stores therapist notes for each week + AI protocol instructions
```python
class TherapistNote(Base):
    id: int (Primary Key)
    patient_id: int (Foreign Key → patients.id)
    therapist_id: int (Foreign Key → therapists.id)
    week_notes: dict (JSON) # {"initial": "note", "week_1": "note", ...}
    ai_protocol_instruction: str (Global AI instructions for patient)
    created_at: datetime
    updated_at: datetime
```

### API Endpoints (`backend/app/progress/router.py`)

#### For Patients
- **POST `/progress/initial-condition`** - Submit initial symptoms
  - Body: `{"initial_condition": "text"}`
  - Creates new patient progress record
  
- **POST `/progress/weekly-progress`** - Add weekly progress report
  - Body: `{"week_number": 1, "progress_text": "text"}`
  - Adds to weekly_progress JSON field
  
- **PUT `/progress/update-progress`** - Edit existing progress (initial or weekly)
  - Body: `{"week_key": "initial" | "week_1", "progress_text": "text"}`
  - Allows patients to edit their reports
  
- **GET `/progress/my-progress`** - Get all own progress entries
  - Returns: Initial condition + all weekly progress

#### For Therapists
- **GET `/progress/patient/{patient_id}`** - Get patient's progress
  - Returns: Patient progress + therapist notes for that patient
  
- **POST `/progress/therapist-note`** - Add/update note for specific week
  - Body: `{"patient_id": int, "week_key": "initial" | "week_1", "note_text": "text"}`
  - Stores note in week_notes JSON under specified key
  
- **POST `/progress/ai-protocol`** - Update AI protocol instructions
  - Body: `{"patient_id": int, "ai_protocol_instruction": "text"}`
  - Global AI protocol for LangGraph pipeline (future integration)

### Authentication (`backend/app/auth/utils.py`)
Added `get_current_user()` function:
```python
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Returns: {"user_id": int, "email": str, "user_type": str, "name": str}
    # Supports patient, therapist, emergency_personnel roles
```

---

## Frontend Implementation

### Patient Side

#### Component: `ProgressTracker.jsx`
**Location**: Accessed from Patient Dashboard → Progress Section

**Features**:
1. **Sidebar Entry List** (left side)
   - Shows all progress entries (Initial Symptoms + Week 1, Week 2, etc.)
   - Click entry to view/edit in detail panel
   - Active entry highlighted with gradient background

2. **Detail View Panel** (right side)
   - Displays selected entry's content
   - **Edit Mode**: Click "Edit" button → textarea appears
   - **Save Changes**: Update existing progress report
   - Empty state when no entry selected

3. **Add Report FAB** (floating action button, bottom-right)
   - Appears when: Can add initial symptoms OR can add next week report
   - Opens modal to add new report
   - Modal shows appropriate title (Initial Symptoms / Week X Report)
   - Smooth rotation animation on hover

**Navigation Flow**:
```
Patient Dashboard
    └─→ Click "Progress" tile
        └─→ ProgressTracker Component
            ├─→ Sidebar: List of entries (Initial, Week 1, Week 2...)
            ├─→ Click entry → Detail view shows content
            ├─→ Click "Edit" → Textarea appears → Save changes
            └─→ Click FAB → Modal → Add initial or next week
```

### Therapist Side

#### Component: `PatientHistoryList.jsx`
**Location**: Accessed from Therapist Dashboard → History Section

**Features**:
1. **Patient Grid Display**
   - Cards showing: Patient initial, name, conditions badge, progress badge
   - Decorative corners appear on hover
   - Gold accent borders on hover
   - Click card → Navigate to patient detail

**Navigation Flow**:
```
Therapist Dashboard
    └─→ Click "History" tile
        └─→ PatientHistoryList Component (Grid of patient cards)
            └─→ Click patient card
```

#### Component: `TherapistProgressDetail.jsx`
**Location**: `/therapist/history/:patientId`

**Features**:
1. **Sidebar Entry List** (left side)
   - Shows all patient entries (Initial Symptoms + weeks)
   - Click entry to view in detail panel
   - Active entry highlighted

2. **Detail View Panel** (right side)
   - **Top Section**: Patient's progress report (read-only)
   - **Middle Section**: Therapist note for this specific week
     - Textarea for therapist to add/edit notes
     - "Save Note" button
   - Gold separator between sections

3. **AI Protocol FAB** (floating action button, bottom-right)
   - Opens modal for global AI protocol instructions
   - Separate from per-week notes
   - For LangGraph pipeline integration (future)

**Navigation Flow**:
```
Therapist Dashboard
    └─→ Click "History" tile
        └─→ PatientHistoryList (Grid)
            └─→ Click patient card
                └─→ TherapistProgressDetail Component
                    ├─→ Sidebar: Select entry (Initial, Week 1, Week 2...)
                    ├─→ Detail: View patient report + add therapist note
                    └─→ FAB: Update AI protocol instructions
```

---

## Styling Details

### Design Elements

#### Decorative Corners
```css
/* Appear on hover for cards and entries */
content: '';
position: absolute;
background: var(--deep-sage);
width: 30px; height: 2px; /* Horizontal line */
width: 2px; height: 30px; /* Vertical line */
```

#### Floating Action Button (FAB)
```css
width: 70px; height: 70px;
border-radius: 50%;
background: gradient(forest-dark → deep-sage);
border: 4px solid var(--gold-accent);
transform: scale(1.15) rotate(90deg); /* on hover */
```

#### Modal Design
```css
/* Top decorative bar */
content: '';
height: 6px;
background: gradient(gold → deep-sage → gold);

/* Close button */
border-radius: 50%;
transform: rotate(90deg); /* on hover */
```

#### Sidebar Navigation
```css
/* Active entry */
background: gradient(deep-sage → sage-green);
color: white;
border-left: 4px solid var(--gold-accent);

/* Hover effect */
transform: translateX(5px);
border-color: var(--muted-green);
```

---

## Data Flow Examples

### Patient Adds Initial Symptoms
```
1. Patient clicks FAB → Modal opens
2. Types symptoms → Clicks "Add Report"
3. Frontend: POST /progress/initial-condition
4. Backend: Creates PatientProgress record
5. Frontend: Refreshes list, shows new "Initial Symptoms" entry
```

### Patient Adds Weekly Progress
```
1. Patient clicks FAB → Modal shows "Week 2 Report"
2. Types progress → Clicks "Add Report"
3. Frontend: POST /progress/weekly-progress {"week_number": 2, "progress_text": "..."}
4. Backend: Updates weekly_progress JSON: {"week_1": "...", "week_2": "..."}
5. Frontend: Refreshes list, shows new "Week 2" entry
```

### Patient Edits Existing Report
```
1. Patient clicks entry in sidebar → Detail view shows content
2. Clicks "Edit" button → Textarea appears
3. Modifies text → Clicks "Save Changes"
4. Frontend: PUT /progress/update-progress {"week_key": "week_1", "progress_text": "..."}
5. Backend: Updates specific key in weekly_progress JSON
6. Frontend: Exit edit mode, show updated content
```

### Therapist Views Patient History
```
1. Therapist clicks patient card in grid
2. Navigate to /therapist/history/:patientId
3. Frontend: GET /progress/patient/:patientId
4. Backend: Returns patient progress + therapist notes
5. Frontend: Builds sidebar list (Initial + Week 1, 2, 3...)
```

### Therapist Adds Note for Week
```
1. Therapist clicks "Week 2" in sidebar
2. Detail view shows patient's Week 2 report
3. Therapist types note in textarea → Clicks "Save Note"
4. Frontend: POST /progress/therapist-note {"patient_id": 5, "week_key": "week_2", "note_text": "..."}
5. Backend: Updates week_notes JSON: {"initial": "...", "week_1": "...", "week_2": "..."}
6. Frontend: Shows success message
```

### Therapist Updates AI Protocol
```
1. Therapist clicks AI Protocol FAB (bottom-right)
2. Modal opens with previous instructions (if any)
3. Therapist edits/adds instructions → Clicks "Update Protocol"
4. Frontend: POST /progress/ai-protocol {"patient_id": 5, "ai_protocol_instruction": "..."}
5. Backend: Updates ai_protocol_instruction field
6. Frontend: Modal closes, shows success message
```

---

## Database Migration

### Running the Migration
```bash
cd backend
python migrate_week_notes.py
```

### What It Does
1. Checks if `week_notes` column already exists
2. Backs up existing `last_week_note` data
3. Adds `week_notes` JSON column
4. Migrates old notes to `{"initial": "old_note"}` format
5. Drops `last_week_note` column
6. Verifies migration success

### Migration Output
```
Starting migration of therapist_notes table...
1. Backing up existing notes data...
   Backed up 5 records
2. Adding week_notes JSON column...
   ✓ week_notes column added
3. Migrating existing notes to new format...
   ✓ Migrated 5 records
4. Dropping old last_week_note column...
   ✓ last_week_note column dropped

✅ Migration completed successfully!
```

---

## Routes Configuration

### Added Routes (`frontend/src/routes/AppRoutes.jsx`)
```jsx
// Therapist Progress History
<Route
  path="/therapist/history/:patientId"
  element={
    <ProtectedRoute allowedRoles={['therapist']}>
      <TherapistProgressDetail />
    </ProtectedRoute>
  }
/>
```

---

## API Client Functions (`frontend/src/api/progress.api.js`)

### Patient APIs
```javascript
// Get patient's own progress
export const getMyProgress = async () => {...}

// Submit initial symptoms
export const createInitialCondition = async (initialCondition) => {...}

// Add weekly progress
export const addWeeklyProgress = async (weekNumber, progressText) => {...}

// Update existing progress
export const updateProgress = async (weekKey, progressText) => {...}
```

### Therapist APIs
```javascript
// Get specific patient's progress
export const getPatientProgress = async (patientId) => {...}

// Add/update therapist note for specific week
export const createOrUpdateTherapistNote = async (patientId, weekKey, noteText) => {...}

// Update AI protocol instructions
export const updateAIProtocol = async (patientId, aiProtocolInstruction) => {...}
```

---

## Future Integrations

### AI Protocol + LangGraph Pipeline
The `ai_protocol_instruction` field is prepared for integration with:
- Intelligent therapy session planning
- Personalized treatment recommendations
- Progress analysis and insights
- Adaptive therapy protocols based on patient progress

---

## Testing Checklist

### Patient Side
- [ ] Add initial symptoms
- [ ] Add Week 1, Week 2, Week 3 reports
- [ ] Click entries in sidebar to view details
- [ ] Edit existing initial symptoms
- [ ] Edit existing weekly report
- [ ] FAB button appears/disappears correctly
- [ ] Modal opens/closes properly
- [ ] Responsive design on mobile

### Therapist Side
- [ ] View patient grid in History section
- [ ] Click patient card → navigate to detail page
- [ ] View all patient entries in sidebar
- [ ] Click entry → view patient report
- [ ] Add therapist note for initial symptoms
- [ ] Add therapist note for Week 1, 2, 3
- [ ] Edit existing therapist notes
- [ ] Click AI Protocol FAB → modal opens
- [ ] Add/update AI protocol instructions
- [ ] Responsive design on mobile

---

## Styling Files

1. **PatientHistoryList.css** - Patient card grid styling
2. **TherapistProgressDetail.css** - Therapist detail page styling
3. **ProgressTracker.css** - Patient progress tracking styling

All follow the same design system:
- Vintage aesthetic with serif typography
- Sage green color palette
- Gold accent decorations
- Smooth transitions and hover effects
- Professional, non-cliche design

---

## Summary

✅ **Backend**: Complete with models, API endpoints, authentication
✅ **Frontend**: Both patient and therapist interfaces fully designed
✅ **Styling**: Professional vintage aesthetic aligned with app design
✅ **Database**: Migration script ready for schema update
✅ **Routes**: Navigation properly configured
✅ **Future-Ready**: AI protocol field prepared for LangGraph integration

The progress tracking feature is now complete and ready for testing and integration!
