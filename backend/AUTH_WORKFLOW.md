# JWT Authentication Workflow Documentation

## Overview
This document explains the JWT-based authentication system for therapist registration and login in the Nirbaan Therapy Management Platform.

## Architecture Components

### 1. **Database Layer** (`app/database/`)
- **base.py**: SQLAlchemy declarative base class
- **session.py**: Database connection and session management
- **deps.py**: Dependency injection for database sessions

### 2. **Models** (`app/therapists/models.py`)
```python
Therapist Model:
- id: Primary key (auto-increment)
- name: Therapist's full name
- email: Unique email address (indexed)
- hashed_password: Bcrypt-hashed password
- license_number: Unique professional license (indexed)
- specialty: Area of expertise
- address: Physical address
- created_at: Timestamp of registration
- updated_at: Auto-updated timestamp
```

### 3. **Schemas** (`app/schemas/auth.py`)
**Request Schemas:**
- `TherapistRegister`: Registration data validation
  - Validates email format
  - Enforces password minimum 8 characters
  - All fields required
  
- `TherapistLogin`: Login credentials
  - Email and password only

**Response Schemas:**
- `TherapistResponse`: Therapist profile data (excludes password)
- `Token`: JWT access token response
- `TokenData`: Decoded token payload

### 4. **Configuration** (`app/core/config.py`)
- JWT secret key (load from .env)
- Algorithm: HS256
- Token expiration: 24 hours
- Database URL configuration

### 5. **Authentication Utilities** (`app/auth/utils.py`)

**Password Functions:**
- `get_password_hash(password)`: Hash password using bcrypt
- `verify_password(plain, hashed)`: Verify password match

**JWT Functions:**
- `create_access_token(data, expires_delta)`: Generate JWT token
  - Payload includes: email (sub), therapist ID, expiration time
  
- `decode_access_token(token)`: Verify and decode JWT
  - Returns TokenData or raises 401 error

**Authentication Dependency:**
- `get_current_therapist(token, db)`: 
  - Extracts token from Authorization header
  - Validates token and retrieves therapist from database
  - Used as FastAPI dependency for protected routes

### 6. **API Endpoints** (`app/auth/router.py`)

#### **POST /auth/register**
Registers a new therapist account.

**Request Body:**
```json
{
  "name": "Dr. Jane Smith",
  "email": "jane.smith@example.com",
  "password": "SecurePass123",
  "license_number": "LIC12345",
  "specialty": "Cognitive Behavioral Therapy",
  "address": "123 Main St, Dhaka, Bangladesh"
}
```

**Success Response (201):**
```json
{
  "id": 1,
  "name": "Dr. Jane Smith",
  "email": "jane.smith@example.com",
  "license_number": "LIC12345",
  "specialty": "Cognitive Behavioral Therapy",
  "address": "123 Main St, Dhaka, Bangladesh",
  "created_at": "2026-02-07T10:30:00"
}
```

**Error Responses:**
- 400: Email already registered
- 400: License number already registered
- 422: Validation error (invalid email, short password, etc.)

**Workflow:**
1. Validate input data (Pydantic schema)
2. Check if email already exists → reject if duplicate
3. Check if license number exists → reject if duplicate
4. Hash password using bcrypt
5. Create Therapist record in database
6. Return therapist profile (without password)

---

#### **POST /auth/login**
Authenticates therapist and returns JWT token.

**Request Body:**
```json
{
  "email": "jane.smith@example.com",
  "password": "SecurePass123"
}
```

**Success Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Response:**
- 401: Incorrect email or password

**Workflow:**
1. Query database for therapist by email
2. Verify password using bcrypt
3. If valid, create JWT token with:
   - `sub`: therapist email
   - `id`: therapist ID
   - `exp`: expiration timestamp (24 hours)
4. Return access token

---

#### **GET /auth/me**
Returns authenticated therapist's profile.

**Headers Required:**
```
Authorization: Bearer <access_token>
```

**Success Response (200):**
```json
{
  "id": 1,
  "name": "Dr. Jane Smith",
  "email": "jane.smith@example.com",
  "license_number": "LIC12345",
  "specialty": "Cognitive Behavioral Therapy",
  "address": "123 Main St, Dhaka, Bangladesh",
  "created_at": "2026-02-07T10:30:00"
}
```

**Error Responses:**
- 401: Missing or invalid token
- 401: Token expired

**Workflow:**
1. Extract token from Authorization header (OAuth2PasswordBearer)
2. Decode and verify JWT token
3. Query database for therapist using email from token
4. Return therapist profile

---

## Security Features

### Password Security
- **Bcrypt hashing**: Passwords never stored in plain text
- **Salt included**: Each password hash is unique
- **Minimum length**: 8 characters enforced

### JWT Token Security
- **Signature verification**: Tokens cannot be forged
- **Expiration**: Tokens expire after 24 hours
- **Payload**: Contains minimal data (email, ID)
- **Secret key**: Stored in environment variables

### Database Security
- **Unique constraints**: Email and license_number indexed
- **SQL injection protection**: SQLAlchemy parameterization
- **Transaction rollback**: Failed operations don't corrupt data

---

## File Structure
```
backend/
├── app/
│   ├── auth/
│   │   ├── router.py          # Registration & login endpoints
│   │   └── utils.py           # JWT & password utilities
│   ├── core/
│   │   └── config.py          # Configuration settings
│   ├── database/
│   │   ├── base.py            # SQLAlchemy base
│   │   ├── session.py         # DB connection
│   │   └── deps.py            # DB dependency
│   ├── schemas/
│   │   └── auth.py            # Pydantic schemas
│   ├── therapists/
│   │   └── models.py          # Therapist database model
│   └── main.py                # FastAPI app with router
├── create_tables.py           # Database table creation script
└── requirements.txt           # Python dependencies
```

---

## Testing the API

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Set Environment Variables
Create `.env` file in backend directory:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/nirbaan
SECRET_KEY=your-super-secret-key-change-in-production
```

### 3. Create Database Tables
```bash
python create_tables.py
```

### 4. Start Server
```bash
uvicorn app.main:app --reload
```

Server runs at: `http://localhost:8000`

### 5. Test Registration
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Dr. Jane Smith",
    "email": "jane@example.com",
    "password": "SecurePass123",
    "license_number": "LIC12345",
    "specialty": "CBT",
    "address": "123 Main St"
  }'
```

### 6. Test Login
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jane@example.com",
    "password": "SecurePass123"
  }'
```

Copy the `access_token` from response.

### 7. Test Protected Endpoint
```bash
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer <paste_access_token_here>"
```

---

## API Documentation

FastAPI automatically generates interactive API docs:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Use Swagger UI to test endpoints directly in browser!

---

## Common Issues & Solutions

### Issue: "Could not validate credentials"
- **Cause**: Invalid or expired token
- **Solution**: Login again to get new token

### Issue: "Email already registered"
- **Cause**: Email exists in database
- **Solution**: Use different email or login with existing account

### Issue: "Connection to database failed"
- **Cause**: Database not running or wrong credentials
- **Solution**: Check DATABASE_URL in .env, ensure PostgreSQL is running

---

## Next Steps

After authentication is working:
1. Add patient management endpoints (therapist creates patient accounts)
2. Implement role-based access control (THERAPIST, PATIENT, EMERGENCY_HANDLER)
3. Add refresh token mechanism for long-lived sessions
4. Implement password reset functionality
5. Add email verification for new registrations
