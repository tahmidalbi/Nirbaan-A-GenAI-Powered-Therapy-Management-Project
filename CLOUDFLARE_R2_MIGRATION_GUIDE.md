# Cloudflare R2 Migration Guide

## Overview

Your RAG implementation has been updated to use **Cloudflare R2** instead of AWS S3. R2 is S3-compatible, so the code remains largely the same with just configuration changes.

---

## ✅ Why Cloudflare R2?

| Feature | AWS S3 | Cloudflare R2 |
|---------|--------|---------------|
| **Egress Fees** | $0.09/GB | **$0.00** (FREE) |
| **Storage Cost** | $0.023/GB/month | $0.015/GB/month |
| **API** | S3 API | S3-compatible API |
| **Global Network** | Regional | Cloudflare's global network |
| **Best For** | Large enterprises | Cost-sensitive apps |

**💰 Cost Savings Example:**
- 100GB storage + 500GB downloads/month
- **AWS S3**: ~$47/month
- **Cloudflare R2**: ~$1.50/month
- **Savings**: ~$45.50/month (96% cheaper!)

---

## 🔧 Setup Instructions

### Step 1: Create Cloudflare R2 Bucket

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com/) → **R2 Object Storage**
2. Click **Create bucket**
3. Enter bucket name: `nirbaan-knowledge-base`
4. Location: **Automatic** (Cloudflare's global network)
5. Click **Create bucket**

### Step 2: Generate API Tokens

1. In R2 dashboard, click **Manage R2 API Tokens**
2. Click **Create API Token**
3. Configure:
   - Token Name: `nirbaan-backend-token`
   - Permissions: **Object Read & Write**
   - Bucket: Select `nirbaan-knowledge-base`
4. Click **Create API Token**
5. **SAVE THESE VALUES** (shown only once):
   ```
   Access Key ID: xxxxxxxxxxxxx
   Secret Access Key: yyyyyyyyyyyyyy
   Endpoint URL: https://<account-id>.r2.cloudflarestorage.com
   ```

### Step 3: Get Your Account ID

1. In Cloudflare dashboard, go to **R2**
2. Copy your **Account ID** from the URL or sidebar
3. Example: `https://dash.cloudflare.com/<account-id>/r2`

### Step 4: Configure CORS

1. Select your bucket `nirbaan-knowledge-base`
2. Go to **Settings** tab
3. Scroll to **CORS policy**
4. Add this policy:

```json
[
  {
    "AllowedOrigins": ["http://localhost:5173", "http://localhost:5174"],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["ETag"],
    "MaxAge": 3000
  }
]
```

5. Click **Save**

---

## 📝 Environment Variables

Update your `backend/.env` file:

```bash
# Remove old AWS S3 variables (if any)
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...
# AWS_REGION=...
# S3_BUCKET_NAME=...
# S3_PRESIGNED_URL_EXPIRY=...

# Add new Cloudflare R2 variables
R2_ACCOUNT_ID=your-cloudflare-account-id
R2_ACCESS_KEY_ID=your-r2-access-key-id
R2_SECRET_ACCESS_KEY=your-r2-secret-access-key
R2_BUCKET_NAME=nirbaan-knowledge-base
R2_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
R2_PRESIGNED_URL_EXPIRY=3600
```

**Replace placeholders:**
- `<account-id>`: Your Cloudflare account ID
- `your-r2-access-key-id`: From Step 2
- `your-r2-secret-access-key`: From Step 2

---

## 🔄 Code Changes Summary

### File: `backend/app/resources/r2_storage.py`

**Changed from `s3_storage.py` to `r2_storage.py`**

Key differences:
```python
# OLD (AWS S3)
self.s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
    config=Config(signature_version='s3v4')
)

# NEW (Cloudflare R2)
self.s3_client = boto3.client(
    's3',
    endpoint_url=R2_ENDPOINT_URL,  # ← Custom endpoint
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    region_name='auto',  # ← R2 uses 'auto'
    config=Config(
        signature_version='s3v4',
        s3={'addressing_style': 'path'}  # ← R2 requires path-style
    )
)
```

### File: `backend/app/resources/models.py`

```python
# OLD
s3_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
s3_key: Mapped[str] = mapped_column(String(1000), nullable=False)

# NEW
r2_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
r2_key: Mapped[str] = mapped_column(String(1000), nullable=False)
```

### File: `backend/app/resources/router.py`

```python
# OLD
from app.resources.s3_storage import s3_storage

# NEW
from app.resources.r2_storage import r2_storage
```

All method calls changed from `s3_storage.*` to `r2_storage.*`.

---

## 🧪 Testing

### Test 1: Verify R2 Connection

```python
# backend/test_r2.py
import os
import boto3
from dotenv import load_dotenv

load_dotenv()

client = boto3.client(
    's3',
    endpoint_url=os.getenv("R2_ENDPOINT_URL"),
    aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
    region_name='auto'
)

# List buckets
response = client.list_buckets()
print("Buckets:", [b['Name'] for b in response['Buckets']])

# Should show: ['nirbaan-knowledge-base']
```

Run:
```bash
cd backend
python test_r2.py
```

### Test 2: Upload/Download Test

```python
# backend/test_r2_operations.py
import os
import boto3
from dotenv import load_dotenv

load_dotenv()

client = boto3.client(
    's3',
    endpoint_url=os.getenv("R2_ENDPOINT_URL"),
    aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
    region_name='auto'
)

bucket = os.getenv("R2_BUCKET_NAME")

# Upload test file
test_content = b"Hello from Cloudflare R2!"
client.put_object(Bucket=bucket, Key='test.txt', Body=test_content)
print("✅ Upload successful")

# Download test file
response = client.get_object(Bucket=bucket, Key='test.txt')
content = response['Body'].read()
print(f"✅ Download successful: {content.decode()}")

# Delete test file
client.delete_object(Bucket=bucket, Key='test.txt')
print("✅ Delete successful")
```

Run:
```bash
cd backend
python test_r2_operations.py
```

---

## 📊 Migration Checklist

### Backend Changes
- ✅ Updated `RAG_IMPLEMENTATION_GUIDE.md` with R2 setup
- ✅ Renamed `s3_storage.py` → `r2_storage.py` (in guide)
- ✅ Updated models: `s3_bucket/s3_key` → `r2_bucket/r2_key`
- ✅ Updated router imports: `s3_storage` → `r2_storage`
- ✅ Updated Celery tasks: `s3_storage` → `r2_storage`
- ✅ Updated environment variables documentation

### Database Migration
If you already have existing S3 data, you'll need to rename columns:

```sql
-- Rename columns in resources table
ALTER TABLE resources 
  RENAME COLUMN s3_bucket TO r2_bucket;

ALTER TABLE resources 
  RENAME COLUMN s3_key TO r2_key;
```

**Or create fresh tables:**
```bash
cd backend
python create_tables.py
```

### Environment Configuration
- ✅ Remove AWS S3 variables from `.env`
- ✅ Add Cloudflare R2 variables to `.env`
- ✅ Configure CORS in R2 dashboard
- ✅ Test R2 API connection

---

## 🚀 Deployment Considerations

### For Production:

1. **Custom Domain** (Optional):
   - Set up custom domain in R2 settings
   - Add to `.env`: `R2_PUBLIC_URL=https://cdn.yourapp.com`
   - Useful for public URLs (not needed for presigned URLs)

2. **Security**:
   - Keep R2 bucket **private** (block public access)
   - Use presigned URLs for all uploads/downloads
   - Rotate API tokens regularly

3. **Monitoring**:
   - Check R2 analytics in Cloudflare dashboard
   - Monitor request counts and storage usage
   - Set up alerts for unusual activity

4. **Backups**:
   - R2 provides automatic replication
   - Consider periodic backups to another service
   - Export database records regularly

---

## 🆚 R2 vs S3 API Compatibility

### ✅ Compatible Features (What Works):
- ✅ `put_object` - Upload files
- ✅ `get_object` - Download files
- ✅ `delete_object` - Delete files
- ✅ `head_object` - Check file exists
- ✅ `list_objects_v2` - List bucket contents
- ✅ `generate_presigned_post` - Presigned upload URLs
- ✅ `generate_presigned_url` - Presigned download URLs
- ✅ Multipart uploads
- ✅ CORS policies

### ⚠️ Not Yet Supported (Won't Need):
- ❌ S3 Select (SQL queries on objects)
- ❌ S3 Batch Operations
- ❌ S3 Object Lock
- ❌ S3 Replication (R2 auto-replicates globally)
- ❌ S3 Lifecycle policies (coming soon to R2)

**For our RAG use case, R2 supports everything we need!**

---

## 💡 Tips & Best Practices

### 1. File Naming Convention
Keep the same format:
```
therapist_{therapist_id}/resources/{resource_id}/{filename}
```

### 2. Presigned URL Expiry
- Default: 1 hour (3600 seconds)
- Uploads: 1 hour is plenty
- Downloads: Reduce to 5-10 minutes for security

### 3. CORS Configuration
- Allow only your frontend domains
- In production, change from `localhost` to your actual domain
- Use specific methods (GET, PUT, POST, DELETE) not wildcards

### 4. Error Handling
R2 returns same error codes as S3:
- `404 NotFound` - File doesn't exist
- `403 Forbidden` - Invalid credentials
- `400 BadRequest` - Invalid request

### 5. Rate Limits
- R2: **Unlimited requests per second** (huge advantage!)
- S3: Limited by region, requires request for increases

---

## 🔍 Troubleshooting

### Issue: "SignatureDoesNotMatch" error

**Cause**: Wrong endpoint URL or credentials

**Solution**: 
```bash
# Check .env file
echo $R2_ENDPOINT_URL
echo $R2_ACCESS_KEY_ID

# Verify endpoint format
# Should be: https://<account-id>.r2.cloudflarestorage.com
```

### Issue: "NoSuchBucket" error

**Cause**: Bucket name mismatch or doesn't exist

**Solution**:
```bash
# Check bucket name in .env
echo $R2_BUCKET_NAME

# Verify in Cloudflare dashboard
# Bucket name must match exactly
```

### Issue: CORS errors in browser

**Cause**: CORS policy not configured or doesn't match origin

**Solution**:
1. Check R2 bucket CORS settings
2. Ensure frontend URL matches `AllowedOrigins`
3. Check browser console for exact CORS error

### Issue: Presigned URLs not working

**Cause**: Region mismatch or signature version

**Solution**:
```python
# Ensure these settings in R2StorageService
config=Config(
    signature_version='s3v4',  # Must be s3v4
    s3={'addressing_style': 'path'}  # Must be path-style
)
```

---

## 📈 Cost Comparison Calculator

**Monthly Usage Example:**

| Metric | Amount | AWS S3 Cost | R2 Cost |
|--------|--------|-------------|---------|
| Storage | 100GB | $2.30 | $1.50 |
| PUT requests | 10,000 | $0.05 | $0.00* |
| GET requests | 100,000 | $0.40 | $0.00* |
| Egress (downloads) | 500GB | $45.00 | **$0.00** |
| **TOTAL** | - | **$47.75** | **$1.50** |

**Annual Savings: ~$555** 💰

*R2 includes 10M Class A operations/month free, unlimited Class B operations

---

## 🎯 Summary

### What Changed:
- ✅ Storage backend: AWS S3 → Cloudflare R2
- ✅ Zero egress fees (save ~96% on monthly costs)
- ✅ S3-compatible API (boto3 still works)
- ✅ Configuration changes only (no code rewrite)

### What Stayed the Same:
- ✅ All RAG functionality
- ✅ Presigned URL uploads
- ✅ Celery async processing
- ✅ Database models (just renamed columns)
- ✅ API endpoints (no frontend changes)

### Migration Time:
- **Environment setup**: 10 minutes
- **Code updates**: Already done in guide
- **Testing**: 5 minutes
- **Total**: ~15 minutes

---

## 📚 Resources

- **R2 Documentation**: https://developers.cloudflare.com/r2/
- **R2 API Reference**: https://developers.cloudflare.com/r2/api/
- **S3 Compatibility**: https://developers.cloudflare.com/r2/platform/s3-compatibility/
- **boto3 Documentation**: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html

---

**Ready to deploy your RAG system with Cloudflare R2! 🚀**

**Cost savings achieved, same functionality maintained!**
