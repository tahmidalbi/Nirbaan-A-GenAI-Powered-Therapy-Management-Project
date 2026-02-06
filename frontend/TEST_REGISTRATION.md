# Testing Patient Registration

## Steps to Debug Registration Issues:

### 1. Check if you're logged in as a therapist
- Open browser console (F12)
- Run: `localStorage.getItem('auth-storage')`
- Verify it shows a token and role='therapist'

### 2. Test the backend endpoint directly
Open a new terminal and run:

```powershell
cd backend
.\venv\Scripts\Activate.ps1

# Get your auth token from localStorage (from browser console)
# Replace YOUR_TOKEN_HERE with actual token

python -c "
import requests

token = 'YOUR_TOKEN_HERE'
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
data = {
    'name': 'Test Patient',
    'email': 'test@example.com',
    'password': 'testpass123',
    'conditions': 'Test Condition',
    'conditions_description': 'Test description',
    'address': '123 Test St'
}

response = requests.post('http://127.0.0.1:8000/patients/register', json=data, headers=headers)
print(f'Status: {response.status_code}')
print(f'Response: {response.json()}')
"
```

### 3. Common Issues:

**Issue: 401 Unauthorized**
- Solution: You're not logged in as a therapist. Go to /login and sign in.

**Issue: 400 Bad Request - "Email already registered"**
- Solution: Try a different email address.

**Issue: 422 Validation Error**
- Solution: Check all required fields are filled:
  - Name (required)
  - Email (required, valid format)
  - Password (required, min 8 characters)
  - Conditions (required)
  - Address (required)
  - Conditions_description (optional)

**Issue: CORS Error**
- Solution: Backend needs CORS enabled for localhost:5174 (already configured)

**Issue: Network Error**
- Solution: Backend server not running. Start it:
  ```powershell
  cd backend
  .\venv\Scripts\Activate.ps1
  uvicorn app.main:app --host 127.0.0.1 --port 8000
  ```

### 4. Check Backend Logs
In the terminal where the backend is running, you should see:
- POST /patients/register requests
- Any error messages
- Database query logs

### 5. Manual Test via Form
1. Login as therapist at http://localhost:5174/login
2. Click "Patients" in navbar
3. Click the floating "+ Add New Patient" button (bottom-right)
4. Fill the form with test data
5. Click "Register Patient"
6. **Check browser console (F12)** for detailed error messages

The error logs will now show:
- Full error message
- HTTP status code
- Response data
- Authentication status
