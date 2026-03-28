# Patient Registration & Login Workflow Documentation

## Complete Flow: Therapist Registers Patient → Patient Logs In

---

## 👥 WORKFLOW 1: THERAPIST REGISTERS A PATIENT

### Step 1: Therapist Accesses Dashboard
*File:* frontend/src/dashboards/TherapistDashboard.jsx
- *Line 11:* Therapist data loaded from Zustand store: useAuthStore((state) => state.user)
- *Line 16:* Dashboard shows welcome screen by default (showPatients = false)
- *Line 65:* Therapist clicks "Patients" button in navbar
- *Action:* onClick={() => setShowPatients(!showPatients)}
- *Flow:* showPatients state changes to true, patient list view appears

### Step 2: Open Add Patient Form
*File:* frontend/src/dashboards/TherapistDashboard.jsx
- *Lines 137-141:* Floating Add Patient button rendered when showPatients === true
- *Line 139:* <AddPatient onPatientAdded={handlePatientAdded} /> component renders

*File:* frontend/src/components/AddPatient.jsx
- *Line 19:* Initially showForm = false, button displays
- *Lines 77-81:* Therapist clicks "+ Add New Patient" button
- *Line 79:* onClick={() => setShowForm(true)}
- *Flow:* Modal form opens with 7 input fields

### Step 3: Fill Patient Information
*File:* frontend/src/components/AddPatient.jsx
- *Lines 8-16:* Form state initialized with empty values:
  - name, email, password, confirmPassword, conditions, conditions_description, address
- *Lines 21-27:* handleChange updates formData as therapist types each field
- *Line 29:* Therapist submits form - handleSubmit triggered

### Step 4: Frontend Validation
*File:* frontend/src/components/AddPatient.jsx
- *Lines 32-35:* Check if passwords match
  - If not: Set error "Passwords do not match", return
- *Lines 37-40:* Validate password length (minimum 8 characters)
  - If too short: Set error, return
- *Line 42:* Set loading = true (shows loading spinner)

### Step 5: API Call - Register Patient Request
*File:* frontend/src/components/AddPatient.jsx
- *Line 45:* Remove confirmPassword from data
- *Line 46:* Call await registerPatient(registrationData)
- Data sent: {name, email, password, conditions, conditions_description, address}

*File:* frontend/src/api/patient.api.js
- *Lines 3-10:* registerPatient function
- *Line 5:* POST request to http://127.0.0.1:8000/patients/register

*File:* frontend/src/api/axios.js
- *Lines 14-25:* Request interceptor executes
- *Lines 17-21:* Gets auth token from localStorage (auth-storage key)
- *Line 20:* Adds header: Authorization: Bearer {therapist_token}
- *Flow:* Request sent to backend with therapist's JWT token

### Step 6: Backend - Verify Therapist Authentication
*File:* backend/app/main.py
- FastAPI receives POST request at /patients/register
- CORS middleware allows request from localhost:5174

*File:* backend/app/patients/router.py
- *Line 20:* @router.post("/register") endpoint activated
- *Lines 21-24:* Function signature with:
  - patient_data: PatientRegister (request body)
  - db: Session = Depends(get_db) (database session)
  - current_therapist: Therapist = Depends(get_current_therapist) (auth dependency)

*File:* backend/app/auth/utils.py
- *Lines 62-77:* get_current_therapist dependency executes
- *Line 64:* Extracts JWT token from Authorization header
- *Line 64:* Calls decode_access_token(token)
- *Lines 46-60:* JWT token decoded and validated
  - Verifies signature with SECRET_KEY
  - Checks expiration timestamp
  - Extracts email and user ID from payload
- *Lines 68-75:* Query database for therapist by email
- *Line 76:* Returns therapist object (or raises 401 if not found)
- *Flow:* Only proceeds if valid therapist token provided

### Step 7: Backend Validation - Check Patient Email
*File:* backend/app/patients/router.py
- *Lines 38-43:* Check if patient email already exists
  - Query: db.query(Patient).filter(Patient.email == patient_data.email).first()
  - If exists: Raise HTTPException 400 "Email already registered"
- *Flow:* Ensures unique patient email addresses

### Step 8: Password Hashing
*File:* backend/app/patients/router.py
- *Line 48:* hashed_password = get_password_hash(patient_data.password)

*File:* backend/app/auth/utils.py
- *Lines 27-29:* get_password_hash function
- Uses passlib CryptContext with bcrypt scheme (cost factor 12)
- Returns 60-character hash starting with $2b$12$...
- *Security:* Original password never stored, only bcrypt hash

### Step 9: Database - Create Patient Record
*File:* backend/app/patients/router.py
- *Lines 51-59:* Create new Patient object with all fields:
  - name, email, hashed_password, conditions, conditions_description, address
  - *Line 58:* therapist_id=current_therapist.id (links patient to therapist)
- *Line 62:* db.add(new_patient) - Add to database session
- *Line 63:* db.commit() - Commit transaction to PostgreSQL
- *Line 64:* db.refresh(new_patient) - Reload with auto-generated values
- *Line 65:* Return patient data (serialized as PatientResponse)

*Database:* PostgreSQL patients table
- Auto-generates: id (primary key), created_at, updated_at timestamps
- Stores: patient info with foreign key therapist_id → therapists.id
- Indexes: Unique index on email for fast lookups

### Step 10: Frontend - Update Patient List
*File:* frontend/src/components/AddPatient.jsx
- *Line 46:* Receives patient data from backend
- *Lines 49-57:* Reset form to empty values
- *Line 59:* setShowForm(false) - Close modal
- *Lines 60-62:* Call onPatientAdded(patient) callback

*File:* frontend/src/dashboards/TherapistDashboard.jsx
- *Lines 34-36:* handlePatientAdded callback executes
- *Line 35:* setPatients([...patients, newPatient])
- *Flow:* New patient immediately appears in dashboard grid (no page refresh needed)

### Step 11: Display Success
*File:* frontend/src/dashboards/TherapistDashboard.jsx
- *Lines 105-123:* Patient card rendered in grid
- Shows: Avatar (first letter of name), name, email, conditions, date added
- Card is clickable: onClick={() => handlePatientClick(patient.id)}
- *Flow:* Therapist sees new patient in list, can click to view details

---

## 🔐 WORKFLOW 2: PATIENT LOGS IN

### Step 1: Patient Navigates to Login
*File:* frontend/src/pages/LandingPage.jsx
- Patient clicks "Login" button → navigates to /select-role

*File:* frontend/src/pages/RoleSelection.jsx
- *Lines 23-28:* Patient clicks "Login as Patient" card
- *Line 23:* onClick={() => navigate('/patient/login')}

*File:* frontend/src/routes/AppRoutes.jsx
- *Line 19:* Route matches: <Route path="/patient/login" element={<PatientLogin />} />
- *Flow:* PatientLogin component loads

### Step 2: Patient Enters Credentials
*File:* frontend/src/auth/PatientLogin.jsx
- *Lines 10-13:* Form state initialized with empty email and password
- *Lines 17-23:* handleChange updates formData as patient types
- *Line 25:* Patient clicks "Sign In" - handleSubmit triggered
- *Line 27:* Prevent default form submission
- *Line 29:* Set loading = true

### Step 3: API Call - Login Request
*File:* frontend/src/auth/PatientLogin.jsx
- *Line 33:* Call await loginPatient(formData)
- Sends: {email: "noman@gmail.com", password: "12345678"}

*File:* frontend/src/api/patient.api.js
- *Lines 40-47:* loginPatient function
- *Line 42:* POST request to http://127.0.0.1:8000/patients/login
- *Note:* NO Authorization header needed for login (public endpoint)

### Step 4: Backend - Find Patient by Email
*File:* backend/app/patients/router.py
- *Line 147:* @router.post("/login") endpoint activated
- *Lines 148-151:* Function signature with login_data: PatientLogin and database session
- *Lines 155-157:* Query database for patient by email
  - Query: db.query(Patient).filter(Patient.email == login_data.email).first()
- *Line 159:* Check if patient not found
  - *Line 160:* Log: [LOGIN FAILED] Patient not found with email: {email}
  - *Lines 161-165:* Raise HTTPException 401 "Incorrect email or password"

### Step 5: Backend - Verify Password
*File:* backend/app/patients/router.py
- *Line 168:* Call verify_password(login_data.password, patient.hashed_password)

*File:* backend/app/auth/utils.py
- *Lines 21-23:* verify_password function
- Uses bcrypt to compare plain password with stored hash
- Returns True if match, False otherwise

*File:* backend/app/patients/router.py
- *Line 169:* Log attempt: [LOGIN ATTEMPT] Email: {email}, Patient: {name}, Password Valid: {bool}
- *Lines 171-177:* If password invalid:
  - *Line 172:* Log: [LOGIN FAILED] Invalid password for patient: {name}
  - Raise HTTPException 401 "Incorrect email or password"

### Step 6: Backend - Generate JWT Token
*File:* backend/app/patients/router.py
- *Line 180:* Create access token
- *Payload:* {"sub": patient.email, "id": patient.id, "role": "patient"}
- *Note:* role: "patient" differentiates from therapist tokens

*File:* backend/app/auth/utils.py
- *Lines 31-44:* create_access_token function
- *Line 38:* Calculate expiration (default 30 days from settings)
- *Line 40:* Add expiration to payload: {"exp": timestamp}
- *Line 41:* Encode JWT with SECRET_KEY using HMAC-SHA256
- *Line 42:* Return JWT token string

*File:* backend/app/patients/router.py
- *Line 181:* Log: [LOGIN SUCCESS] Patient: {name} ({email})
- *Line 183:* Return {"access_token": token, "token_type": "bearer"}

### Step 7: Frontend - Store Token Temporarily
*File:* frontend/src/auth/PatientLogin.jsx
- *Line 33:* Receive {access_token, token_type} from backend
- *Lines 36-39:* Call Zustand store's login function with minimal data
  - *Line 37:* email: formData.email
  - *Line 38:* role: 'patient' (important for role-based routing)
  - Token passed as second argument

*File:* frontend/src/store/authStore.js
- *Lines 11-17:* login function updates state:
  - user: {email, role: 'patient'}
  - token: access_token
  - isAuthenticated: true
- *Line 30:* Zustand persist middleware saves to localStorage auth-storage

### Step 8: Fetch Full Patient Profile
*File:* frontend/src/auth/PatientLogin.jsx
- *Line 42:* Call await getCurrentPatient()

*File:* frontend/src/api/patient.api.js
- *Lines 49-56:* getCurrentPatient function
- *Line 51:* GET request to http://127.0.0.1:8000/patients/me

*File:* frontend/src/api/axios.js
- *Lines 14-25:* Request interceptor adds Authorization header
- *Line 20:* Authorization: Bearer {patient_token}

### Step 9: Backend - Verify Patient Token
*File:* backend/app/patients/router.py
- *Line 186:* @router.get("/me") endpoint activated
- *Line 187-190:* Function depends on get_current_patient dependency

*File:* backend/app/auth/utils.py
- *Lines 79-95:* get_current_patient function executes
- *Line 81:* Decode JWT token (same as therapist auth)
- *Line 83:* Check if role != "patient" in token payload
  - If wrong role: Raise HTTPException 403 "Not authorized as patient"
- *Lines 88-94:* Query database for patient by email
  - Query: db.query(Patient).filter(Patient.email == token_data.email).first()
- *Line 95:* Return patient object with all details

*File:* backend/app/patients/router.py
- *Line 191:* Return complete patient data (name, email, conditions, address, therapist_id, timestamps)

### Step 10: Update Store with Full Profile
*File:* frontend/src/auth/PatientLogin.jsx
- *Lines 44-47:* Update Zustand store with complete patient data
- *Line 45:* Spread all patient fields: {...patientData, role: 'patient'}
- Includes: id, name, email, conditions, conditions_description, address, etc.

### Step 11: Navigate to Patient Dashboard
*File:* frontend/src/auth/PatientLogin.jsx
- *Line 52:* navigate('/patient/dashboard')

*File:* frontend/src/routes/AppRoutes.jsx
- *Lines 21-27:* Protected route for /patient/dashboard
- *Line 24:* <ProtectedRoute allowedRoles={['patient']}>

### Step 12: Protected Route Verification
*File:* frontend/src/auth/ProtectedRoute.jsx
- Checks: isAuthenticated === true from Zustand store
- Checks: user.role === 'patient' (matches allowedRoles)
- *If valid:* Renders children (PatientDashboard component)
- *If invalid:* Redirects to landing page with <Navigate to="/" />

### Step 13: Patient Dashboard Loads
*File:* frontend/src/dashboards/PatientDashboard.jsx
- *Component mounts* with patient data from Zustand store
- *Displays:* Welcome message with patient name
- *Shows:* Coming soon features (sessions, resources, progress, communication, exercises)
- *Provides:* Logout button in header

---

## 🗄️ DATABASE RELATIONSHIPS

*Table:* patients
sql
CREATE TABLE patients (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    email VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR(60) NOT NULL,
    conditions VARCHAR NOT NULL,
    conditions_description TEXT,
    address VARCHAR NOT NULL,
    therapist_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (therapist_id) REFERENCES therapists(id)
);


*Relationship:*
- Each patient belongs to exactly one therapist
- patients.therapist_id → therapists.id (foreign key constraint)
- One therapist can have many patients (one-to-many)

*SQLAlchemy Models:*
- *File:* backend/app/patients/models.py - Patient model
- *File:* backend/app/therapists/models.py - Therapist model
- *Relationship:* Therapist.patients = relationship("Patient", back_populates="therapist")

---

## 🔒 AUTHENTICATION & AUTHORIZATION

### Patient Registration (Therapist-Only Endpoint)
*Authorization Required:* Valid therapist JWT token in Authorization: Bearer {token} header

*Flow:*
1. Extract token from request header
2. Decode and verify JWT signature
3. Check token expiration
4. Query therapists table by email from token
5. If valid therapist found → proceed with patient creation
6. If invalid/expired → return 401 Unauthorized

*Why:* Prevents unauthorized patient creation, ensures only licensed therapists can register patients

### Patient Login (Public Endpoint)
*Authorization Required:* None (public endpoint)

*Flow:*
1. Query patients table by email
2. Verify password using bcrypt
3. Generate JWT token with role: "patient"
4. Return token to patient

*JWT Token Differences:*
- *Therapist token:* {sub: email, id: therapist_id, role: "therapist" (optional), exp: timestamp}
- *Patient token:* {sub: email, id: patient_id, role: "patient", exp: timestamp}

*Role-Based Access:*
- /patients/register → Requires therapist token
- /patients/ (list) → Requires therapist token
- /patients/{id} (detail) → Requires therapist token (ownership verified)
- /patients/me → Requires patient token (role must be "patient")
- /patient/dashboard → Frontend protected route for patients only

---

## 🔄 SIMPLE TEXT WORKFLOW


PATIENT REGISTRATION (by Therapist):
TherapistDashboard.jsx (Therapist logged in)
  → Clicks "Patients" button (Line 65)
    → showPatients state becomes true
      → Floating AddPatient button appears (Line 139)
        → AddPatient.jsx (Click "+ Add New Patient")
          → Modal form opens (Line 79: setShowForm(true))
            → Therapist fills 7 fields (name, email, password, etc.)
              → Form validation (Lines 32-40: check passwords, length)
                → patient.api.js (Line 5: POST /patients/register)
                  → axios.js (Lines 17-21: Add Authorization: Bearer {therapist_token})
                    → Backend router.py (/patients/register endpoint Line 20)
                      → auth/utils.py (Line 62: get_current_therapist dependency)
                        → Decode JWT token, verify therapist identity
                      → router.py (Lines 38-43: Check email uniqueness)
                      → auth/utils.py (Line 48: Hash password with bcrypt)
                      → patients/models.py (Create Patient ORM object)
                        → PostgreSQL (Insert into patients table with therapist_id FK)
                      → Return new patient data (Line 65)
                  → AddPatient.jsx (Line 46: Receive patient data)
                    → Reset form, close modal (Lines 49-59)
                    → Call onPatientAdded callback (Line 61)
                      → TherapistDashboard.jsx (Line 35: Add to patients array)
                        → Patient card renders in grid (Lines 105-123)
                          → Shows avatar, name, email, conditions, date

PATIENT LOGIN:
LandingPage → Click "Login"
  → RoleSelection.jsx (Click "Login as Patient" Line 23)
    → navigate('/patient/login')
      → AppRoutes.jsx (Route Line 19)
        → PatientLogin.jsx (Component loads)
          → Patient enters email + password (Lines 10-13)
            → Submits form (Line 25)
              → patient.api.js (Line 42: POST /patients/login)
                → Backend router.py (/patients/login endpoint Line 147)
                  → Query patients table by email (Line 155)
                  → auth/utils.py (Line 168: verify_password with bcrypt)
                  → auth/utils.py (Line 180: create_access_token)
                    → Generate JWT: {sub, id, role: "patient", exp}
                  → Log success, return token (Line 183)
              → PatientLogin.jsx (Line 33: Receive token)
                → authStore.js (Lines 36-39: Store token + email + role)
                  → localStorage updated via persist middleware
                → patient.api.js (Line 51: GET /patients/me with token)
                  → axios.js (Line 20: Add Authorization: Bearer {patient_token})
                    → Backend router.py (/patients/me endpoint Line 186)
                      → auth/utils.py (Line 79: get_current_patient dependency)
                        → Decode JWT, verify role === "patient"
                        → Query patients table by email
                        → Return full patient data (Line 95)
                → authStore.js (Lines 44-47: Update with full patient data)
                  → navigate('/patient/dashboard') (Line 52)
                    → AppRoutes.jsx (Protected route Lines 21-27)
                      → ProtectedRoute.jsx (Verify auth + role)
                        → PatientDashboard.jsx (Component loads)
                          → Display welcome + logout (uses patient data from store)


---

## ✨ KEY DIFFERENCES: Therapist vs Patient

### Registration Process:
- *Therapist:* Self-registration via /auth/register (public endpoint)
- *Patient:* Registered by therapist via /patients/register (protected endpoint)

### Authentication:
- *Therapist:* Login via /auth/login → Token with optional role
- *Patient:* Login via /patients/login → Token with required role: "patient"

### Authorization:
- *Therapist:* Can register patients, view/edit their own patients, manage practice
- *Patient:* Can view own dashboard, access therapy resources (future features)

### Token Validation:
- *Therapist endpoints:* Check if valid therapist exists in database
- *Patient endpoints:* Check if valid patient exists AND role === "patient"

### Dashboard Access:
- *Therapist:* /therapist/dashboard → Patient management, analytics, practice tools
- *Patient:* /patient/dashboard → Personal therapy journey, resources, communication

---

## 🔐 SECURITY MEASURES

1. *Password Security:* All passwords hashed with bcrypt (cost factor 12, 60-char hash)
2. *JWT Tokens:* Signed with SECRET_KEY, include expiration, stateless authentication
3. *Role-Based Access:* Token payload includes role, endpoints verify appropriate role
4. *Foreign Key Constraint:* Patients linked to therapists, orphaned records prevented
5. *Unique Email Constraint:* No duplicate patient emails, enforced at database level
6. *Authorization Headers:* Token required for protected endpoints, validated on every request
7. *Error Messages:* Generic "Incorrect email or password" prevents email enumeration
8. *HTTPS Ready:* Backend configured for HTTPS in production (CORS settings)

---

## 📊 SUMMARY

*Patient Registration Flow:*
- Therapist authenticated → Fills patient form → Backend validates therapist token → Checks email uniqueness → Hashes password → Creates patient record with therapist_id FK → Returns patient data → Frontend updates list

*Patient Login Flow:*
- Patient enters credentials → Backend validates email → Verifies password with bcrypt → Generates JWT with role="patient" → Returns token → Frontend stores token → Fetches full patient data → Verifies role → Loads dashboard

*Key Points:*
- Patient registration requires therapist authentication (protected endpoint)
- Patient login is public but generates role-specific token
- All passwords hashed with bcrypt, never stored in plain text
- JWT tokens enable stateless authentication across requests
- Foreign key relationships maintain data integrity between therapists and patients
- Role-based access control ensures proper authorization throughout system