# Therapist Registration & Login Workflow Documentation

## Complete Flow: From Landing Page to Dashboard

---

## 🔐 WORKFLOW 1: THERAPIST REGISTRATION

### Step 1: Landing Page - User Initiates Registration
**File:** `frontend/src/pages/LandingPage.jsx`
- **Line 127:** User clicks "Sign Up" button
- **Action:** `onClick={() => navigate('/signup')}`
- **Flow:** Navigates to `/signup` route

### Step 2: Routing - Navigate to Signup Page
**File:** `frontend/src/routes/AppRoutes.jsx`
- **Line 18:** Route definition `<Route path="/signup" element={<Signup />} />`
- **Flow:** React Router loads Signup component

### Step 3: Signup Form - User Enters Data
**File:** `frontend/src/auth/Signup.jsx`
- **Lines 10-17:** `useState` initializes form data (name, email, password, confirmPassword, license_number, specialty, address)
- **Lines 22-27:** `handleChange` updates form state as user types
- **Lines 29-72:** `handleSubmit` processes form submission

### Step 4: Form Validation (Frontend)
**File:** `frontend/src/auth/Signup.jsx`
- **Line 33-36:** Check if passwords match - if not, display error
- **Line 39-42:** Validate password length (minimum 8 characters)
- **Line 44:** Set loading state to `true`

### Step 5: API Call - Registration Request
**File:** `frontend/src/auth/Signup.jsx`
- **Line 49:** Extract form data, remove `confirmPassword`
- **Line 50:** Call `await registerTherapist(registrationData)`

**File:** `frontend/src/api/auth.api.js`
- **Lines 3-10:** `registerTherapist` function
- **Line 5:** POST request to `http://127.0.0.1:8000/auth/register`
- **Flow:** axios interceptor adds headers (Content-Type: application/json)

**File:** `frontend/src/api/axios.js`
- **Lines 14-25:** Request interceptor runs - no token needed for registration

### Step 6: Backend - Receive Registration Request
**File:** `backend/app/main.py`
- FastAPI receives POST request at `/auth/register`
- CORS middleware allows request from localhost:5174

**File:** `backend/app/auth/router.py`
- **Line 16:** `@router.post("/register")` endpoint activated
- **Lines 17-20:** Function signature with `therapist_data: TherapistRegister` and `db: Session`

### Step 7: Backend Validation
**File:** `backend/app/auth/router.py`
- **Lines 33-39:** Check if email already exists in database
  - Query: `db.query(Therapist).filter(Therapist.email == therapist_data.email).first()`
  - If exists: Raise 400 error "Email already registered"
- **Lines 42-48:** Check if license_number already exists
  - Query: `db.query(Therapist).filter(Therapist.license_number == therapist_data.license_number).first()`
  - If exists: Raise 400 error "License number already registered"

### Step 8: Password Hashing
**File:** `backend/app/auth/router.py`
- **Line 51:** `hashed_password = get_password_hash(therapist_data.password)`

**File:** `backend/app/auth/utils.py`
- **Lines 27-29:** `get_password_hash` function uses bcrypt
- Uses passlib CryptContext with bcrypt scheme
- Returns hashed password starting with `$2b$12$...`

### Step 9: Database - Create Therapist Record
**File:** `backend/app/auth/router.py`
- **Lines 54-61:** Create new Therapist object with all fields
  - name, email, hashed_password, license_number, specialty, address
- **Line 64:** `db.add(new_therapist)` - Add to database session
- **Line 65:** `db.commit()` - Commit transaction to PostgreSQL
- **Line 66:** `db.refresh(new_therapist)` - Get auto-generated ID and timestamps
- **Line 67:** Return `new_therapist` (serialized as TherapistResponse schema)

**Database:** PostgreSQL `therapists` table
- Auto-generates: `id` (primary key), `created_at`, `updated_at`
- Stores: all therapist information with hashed password

### Step 10: Auto-Login After Registration
**File:** `frontend/src/auth/Signup.jsx`
- **Lines 53-56:** Immediately call `loginTherapist` with email and password
- **Flow:** Same as Step 5 in Login Workflow (see below)

### Step 11: Store Authentication Data
**File:** `frontend/src/auth/Signup.jsx`
- **Lines 59-63:** Call `login()` from Zustand store with user data and token

**File:** `frontend/src/store/authStore.js`
- **Lines 11-17:** `login` function sets state:
  - `user`: {email, name, role: 'therapist'}
  - `token`: JWT access token
  - `isAuthenticated`: true
- **Line 30:** Zustand persist middleware saves to localStorage key `auth-storage`

### Step 12: Navigate to Dashboard
**File:** `frontend/src/auth/Signup.jsx`
- **Line 66:** `navigate('/therapist/dashboard')`

**File:** `frontend/src/routes/AppRoutes.jsx`
- **Lines 31-37:** Protected route for `/therapist/dashboard`
- **Flow:** ProtectedRoute checks role, loads TherapistDashboard component

---

## 🔓 WORKFLOW 2: THERAPIST LOGIN

### Step 1: Landing Page - User Initiates Login
**File:** `frontend/src/pages/LandingPage.jsx`
- **Line 123:** User clicks "Login" button
- **Action:** `onClick={() => navigate('/select-role')}`
- **Flow:** Navigates to role selection page

### Step 2: Role Selection Page
**File:** `frontend/src/pages/RoleSelection.jsx`
- **Lines 16-21:** User sees "Login as Therapist" card
- **Line 16:** Card click handler: `onClick={() => navigate('/login')}`
- **Flow:** Navigates to `/login` route

### Step 3: Routing - Navigate to Login Page
**File:** `frontend/src/routes/AppRoutes.jsx`
- **Line 17:** Route definition `<Route path="/login" element={<Login />} />`
- **Flow:** React Router loads Login component

### Step 4: Login Form - User Enters Credentials
**File:** `frontend/src/auth/Login.jsx`
- **Lines 10-13:** `useState` initializes form (email, password)
- **Lines 17-23:** `handleChange` updates form as user types
- **Line 25:** User submits form - `handleSubmit` triggered

### Step 5: API Call - Login Request
**File:** `frontend/src/auth/Login.jsx`
- **Line 31:** Call `await loginTherapist(formData)`

**File:** `frontend/src/api/auth.api.js`
- **Lines 12-19:** `loginTherapist` function
- **Line 14:** POST request to `http://127.0.0.1:8000/auth/login`
- Sends: `{email: "albitahmid@gmail.com", password: "12345678"}`

### Step 6: Backend - Authenticate Therapist
**File:** `backend/app/auth/router.py`
- **Line 78:** `@router.post("/login")` endpoint activated
- **Lines 90-92:** Query database for therapist by email
  - `db.query(Therapist).filter(Therapist.email == login_data.email).first()`

### Step 7: Password Verification
**File:** `backend/app/auth/router.py`
- **Line 94:** Check if therapist not found - log failure
- **Lines 99-101:** Verify password with `verify_password(login_data.password, therapist.hashed_password)`

**File:** `backend/app/auth/utils.py`
- **Lines 21-23:** `verify_password` uses bcrypt to compare
- Returns True/False

### Step 8: Generate JWT Token
**File:** `backend/app/auth/router.py`
- **Lines 108-110:** `create_access_token(data={"sub": therapist.email, "id": therapist.id})`

**File:** `backend/app/auth/utils.py`
- **Lines 31-44:** `create_access_token` function
- **Line 41:** Encodes JWT with SECRET_KEY using jose library
- Payload: `{sub: email, id: therapist_id, exp: expiration_timestamp}`
- **Line 42:** Returns JWT token string

**File:** `backend/app/auth/router.py`
- **Line 114:** Return `{"access_token": token, "token_type": "bearer"}`

### Step 9: Store Token in Frontend
**File:** `frontend/src/auth/Login.jsx`
- **Lines 34-37:** Store token temporarily in Zustand
- **Line 35:** `login({email, role: 'therapist'}, loginResponse.access_token)`

**File:** `frontend/src/store/authStore.js`
- **Lines 11-17:** Update state with token
- localStorage updated via persist middleware

### Step 10: Fetch Full Therapist Profile
**File:** `frontend/src/auth/Login.jsx`
- **Line 41:** Call `await getCurrentTherapist()`

**File:** `frontend/src/api/auth.api.js`
- **Lines 21-28:** `getCurrentTherapist` function
- **Line 23:** GET request to `http://127.0.0.1:8000/auth/me`

**File:** `frontend/src/api/axios.js`
- **Lines 14-25:** Request interceptor adds Authorization header
- **Line 20:** `config.headers.Authorization = 'Bearer {token}'`

### Step 11: Backend - Return Therapist Profile
**File:** `backend/app/auth/router.py`
- **Line 117:** `@router.get("/me")` endpoint
- **Line 120:** Depends on `get_current_therapist` dependency

**File:** `backend/app/auth/utils.py`
- **Lines 62-77:** `get_current_therapist` function
- **Line 64:** Decode and verify JWT token
- **Lines 68-75:** Query database for therapist
- **Line 76:** Return therapist object

**File:** `backend/app/auth/router.py`
- **Line 121:** Return complete therapist data (name, email, specialty, etc.)

### Step 12: Update Store with Full Profile
**File:** `frontend/src/auth/Login.jsx`
- **Lines 43-47:** Update Zustand store with complete therapist data
- **Line 44:** `login({...therapistData, role: 'therapist'}, loginResponse.access_token)`

### Step 13: Navigate to Dashboard
**File:** `frontend/src/auth/Login.jsx`
- **Line 52:** `navigate('/therapist/dashboard')`

**File:** `frontend/src/routes/AppRoutes.jsx`
- **Lines 31-37:** Protected route checks authentication

### Step 14: Protected Route Verification
**File:** `frontend/src/auth/ProtectedRoute.jsx`
- Checks if user is authenticated
- Checks if user role matches allowed roles ('therapist')
- If valid: renders TherapistDashboard
- If invalid: redirects to landing page

### Step 15: Dashboard Loads
**File:** `frontend/src/dashboards/TherapistDashboard.jsx`
- **Line 11:** `useAuthStore` gets current user data
- **Lines 18-20:** `useEffect` runs on mount
- **Line 19:** Calls `fetchPatients()` to load patient list
- Dashboard displays: Welcome message with therapist name, Patients button, Logout button

---

## 🗄️ DATABASE FLOW

**PostgreSQL Database:** `nirbaan_therapy_db`

**Table:** `therapists`
- id (Integer, Primary Key, Auto-increment)
- name (String)
- email (String, Unique Index)
- hashed_password (String, 60 chars)
- license_number (String, Unique Index)
- specialty (String)
- address (String)
- created_at (Timestamp)
- updated_at (Timestamp)

**SQLAlchemy ORM:** `backend/app/therapists/models.py`
- Maps Python class to database table
- Handles relationships (therapist has many patients)

---

## 🔒 AUTHENTICATION MECHANISM

**JWT Token Structure:**
```
Header: {"alg": "HS256", "typ": "JWT"}
Payload: {"sub": "email@example.com", "id": 1, "exp": 1707308400}
Signature: HMACSHA256(base64(header) + "." + base64(payload), SECRET_KEY)
```

**Token Storage:**
- Frontend: localStorage key `auth-storage` (Zustand persist)
- Expires: 30 days (configurable in backend settings)

**Token Usage:**
- Every API request (except login/register) includes: `Authorization: Bearer {token}`
- Backend validates token and extracts user identity
- Invalid token → 401 Unauthorized response

---

## 📦 KEY DEPENDENCIES

**Frontend:**
- React Router: Navigation between pages
- Zustand: Global state management
- Axios: HTTP client for API calls
- Zustand Persist: localStorage integration

**Backend:**
- FastAPI: Web framework
- SQLAlchemy: ORM for database operations
- Passlib + bcrypt: Password hashing
- python-jose: JWT token generation/validation
- Pydantic: Request/response validation

---

## 🔄 SIMPLE TEXT WORKFLOW

```
REGISTRATION FLOW:
Landing Page (User clicks "Sign Up")
  → AppRoutes.jsx (Router matches /signup)
    → Signup.jsx (Form component loads)
      → User fills form → Validates → Submits
        → auth.api.js (POST /auth/register)
          → axios.js (Adds headers)
            → Backend router.py (/auth/register endpoint)
              → Validates email/license uniqueness
              → auth/utils.py (Hash password with bcrypt)
              → therapists/models.py (ORM model)
                → PostgreSQL (Insert into therapists table)
              → Returns new therapist data
            → Auto-login initiated
              → auth.api.js (POST /auth/login)
                → Backend router.py (/auth/login endpoint)
                  → Verify password
                  → auth/utils.py (Generate JWT token)
                  → Returns {access_token, token_type}
            → authStore.js (Store token + user in localStorage)
              → navigate('/therapist/dashboard')
                → AppRoutes.jsx (Protected route check)
                  → ProtectedRoute.jsx (Verify auth & role)
                    → TherapistDashboard.jsx (Component loads)
                      → Fetch patient list
                      → Display dashboard

LOGIN FLOW:
Landing Page (User clicks "Login")
  → AppRoutes.jsx (Router matches /select-role)
    → RoleSelection.jsx (Choose therapist)
      → navigate('/login')
        → AppRoutes.jsx (Router matches /login)
          → Login.jsx (Form component loads)
            → User enters email/password → Submits
              → auth.api.js (POST /auth/login)
                → Backend router.py (/auth/login endpoint)
                  → Query therapists table by email
                  → auth/utils.py (Verify password with bcrypt)
                  → auth/utils.py (Create JWT token)
                  → Returns {access_token, token_type}
              → authStore.js (Store token temporarily)
                → auth.api.js (GET /auth/me with Bearer token)
                  → axios.js (Adds Authorization header)
                    → Backend router.py (/auth/me endpoint)
                      → auth/utils.py (Decode JWT, get_current_therapist)
                      → Query therapists table
                      → Returns full therapist profile
                → authStore.js (Update with full user data in localStorage)
                  → navigate('/therapist/dashboard')
                    → AppRoutes.jsx (Protected route check)
                      → ProtectedRoute.jsx (Verify auth & role)
                        → TherapistDashboard.jsx (Dashboard loads with user data)
```

---

## ✨ SUMMARY

Both registration and login follow a similar pattern:
1. User interaction on frontend
2. Form validation
3. API call to backend
4. Backend authentication/validation
5. Database operations
6. JWT token generation
7. Token storage in frontend
8. Protected route navigation
9. Dashboard rendering with user context

The system uses JWT-based stateless authentication, bcrypt password hashing, and role-based access control to ensure security throughout the application.
