# Nirbaan AI - Complete Technical Explanation
*How therapists upload knowledge and get AI-powered answers*

---

## 🎯 THE BIG PICTURE

**What happens:** A therapist uploads PDFs or web links → Nirbaan AI automatically processes them → Therapist asks questions → AI answers using ONLY the uploaded content (no hallucination)

**You have 2 apps:**
1. **Frontend** (React) - Your browser UI on http://localhost:5174
2. **Backend** (FastAPI/Python) - Server on http://127.0.0.1:8000

---

## 📚 PART 1: UPLOADING RESOURCES (Files or Web Links)

### Step 1: Therapist Opens Resources Tab

**File:** `frontend/src/dashboards/TherapistDashboard.jsx` (Line 160)
```jsx
{activeTab === 'resources' && <ResourceManager />}
```
Renders the ResourceManager component when "Resources" tab is clicked.

---

### Step 2: Upload Interface Shows Two Options

**File:** `frontend/src/components/ResourceManager.jsx` (Line 98-119)
```jsx
<div className="upload-tabs">
  <button className={uploadMode === 'file' ? 'active' : ''}>Upload File</button>
  <button className={uploadMode === 'url' ? 'active' : ''}>Add Web Link</button>
</div>
```

**State variables:**
- `uploadMode` - Either `'file'` or `'url'`
- `title` - Name of the resource
- `selectedFile` - PDF/TXT file (for file upload)
- `url` - Web address (for URL upload)

---

### 🔹 OPTION A: UPLOADING A PDF/TXT FILE

#### Frontend Step 1: User selects file
**File:** `ResourceManager.jsx` (Line 29-37)
```jsx
const handleFileSelect = (e) => {
  const file = e.target.files[0];
  setSelectedFile(file);
  if (!title) {
    setTitle(file.name.replace(/\.[^/.]+$/, '')); // Auto-fill title
  }
};
```

#### Frontend Step 2: User clicks "Upload & Process"
**File:** `ResourceManager.jsx` (Line 39-59)
```jsx
const handleUpload = async (e) => {
  e.preventDefault();
  setUploading(true);
  await uploadResource(selectedFile, title); // Calls API
  await fetchResources(); // Refresh list
};
```

#### API Call: 3-Step Upload Flow
**File:** `frontend/src/api/resource.api.js` (Line 10-49)

**STEP 1 - Initialize Upload (Backend creates DB record)**
```javascript
const initResponse = await axiosInstance.post('/resources/init-upload', {
  title,
  filename: file.name,
  file_type: file.name.endsWith('.pdf') ? 'pdf' : 'txt',
  mime_type: file.type,
  size_bytes: file.size,
});
// Backend returns: { resource_id: 10, upload_url: "https://r2.cloudflarestorage.com/...", r2_key: "..." }
```

**Backend handler:** `backend/app/resources/router.py` (Line 36-85)
1. Validates file type (only PDF/TXT allowed)
2. Creates `Resource` database record with `status='initiated'`
3. Generates unique R2 key: `therapist_1/resource_10/document.pdf`
4. Creates presigned PUT URL (expires in 1 hour)
5. Returns URL to frontend

**STEP 2 - Upload to Cloudflare R2 (Direct from browser)**
```javascript
const r2Response = await fetch(upload_url, {
  method: 'PUT',
  body: file,
  headers: { 'Content-Type': file.type },
});
// File goes DIRECTLY to Cloudflare R2, not through our backend
```

**Why R2?** 
- Cloud storage (like AWS S3) for PDFs/documents
- Presigned URL = secure temporary link
- Browser uploads directly = fast, saves backend bandwidth

**STEP 3 - Confirm Upload (Trigger processing)**
```javascript
await axiosInstance.post(`/resources/${resource_id}/confirm-upload`);
```

**Backend handler:** `router.py` (Line 101-142)
1. Updates resource `status='uploaded'`
2. Creates `IngestionJob` record with `status='queued'`
3. Triggers Celery task: `ingest_resource_task.delay(resource_id)`
4. Returns job_id to frontend

---

### 🔹 OPTION B: UPLOADING A WEB LINK

#### Frontend Step 1: User enters URL
**File:** `ResourceManager.jsx` (Line 62-85)
```jsx
const handleUrlUpload = async (e) => {
  e.preventDefault();
  setUploading(true);
  await uploadFromUrl(url, title, resourceType);
  await fetchResources();
};
```

#### API Call: Single-step URL fetch
**File:** `resource.api.js` (Line 102-112)
```javascript
const response = await axiosInstance.post('/resources/from-url', {
  url: 'https://my.clevelandclinic.org/health/treatments/erp-therapy',
  title: 'ERP Therapy Guide',
  resource_type: 'webpage'
});
```

#### Backend: Fetch & Process URL
**File:** `router.py` (Line 235-318)

**Step 1: Fetch web content**
```python
fetched_title, content = url_processor.fetch_url_content(request.url)
```

**File:** `backend/app/resources/url_processor.py` (Line 12-52)
```python
def fetch_url_content(self, url: str) -> Tuple[str, str]:
    # 1. HTTP GET with User-Agent header
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
    
    # 2. Parse HTML with BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # 3. Extract title
    title_text = soup.find('title').get_text().strip()
    
    # 4. Remove junk (scripts, styles, nav, footer)
    for script in soup(["script", "style", "nav", "footer", "header"]):
        script.decompose()
    
    # 5. Extract all text
    text = soup.get_text(separator='\n')
    
    # 6. Clean up whitespace
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    content = '\n\n'.join(lines)
    
    return title_text, content
```

**Example output:**
```
Title: "ERP Therapy: What It Is & How It Works"
Content: "Exposure and Response Prevention (ERP) is a type of cognitive behavioral therapy..."
```

**Step 2: Create resource & upload to R2**
```python
# Create DB record
resource = Resource(
    title=final_title,
    original_filename="webpage_from_url.txt",
    file_type="txt",
    size_bytes=len(content.encode("utf-8")),
    status="uploaded"
)
db.add(resource)

# Save to temp file
with tempfile.NamedTemporaryFile(mode="w", suffix=".txt") as tmp:
    tmp.write(content)
    # Upload to R2
    r2_storage.s3_client.upload_file(tmp.name, bucket, r2_key)
```

**Step 3: Queue for processing (same as file upload)**
```python
job = IngestionJob(resource_id=resource.id, status="queued")
db.add(job)
ingest_resource_task.delay(resource_id)  # Trigger Celery
```

---

## 🤖 PART 2: BACKGROUND PROCESSING (The RAG Pipeline)

### What is Celery?
**Celery** = Background job worker (runs separately from main server)
- Handles long-running tasks (PDF parsing, chunking, embedding)
- Prevents blocking the API server
- Runs in separate terminal: `celery -A app.core.celery_app worker --pool=solo`

---

### The Ingestion Task Flow

**File:** `backend/app/resources/tasks.py` (Line 20-120)

```python
@celery_app.task(name="ingest_resource_task")
def ingest_resource_task(resource_id: int):
    # This runs in the background worker
```

#### Step 1: Download file from R2
```python
# Download from Cloudflare R2 to local temp file
local_path = r2_storage.download_file(resource.r2_key)
# Example: Downloads to /tmp/tmpXYZ123.pdf
```

#### Step 2: Extract text from file
```python
if resource.file_type == "pdf":
    import PyPDF2
    reader = PyPDF2.PdfReader(local_path)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n\n"
    total_pages = len(reader.pages)
    
elif resource.file_type == "txt":
    with open(local_path, 'r', encoding='utf-8') as f:
        full_text = f.read()
```

**Example extracted text:**
```
Exposure and Response Prevention (ERP) is a specific type of 
Cognitive Behavioral Therapy that helps people confront their fears...
```

#### Step 3: Split into chunks
```python
# Why chunk? OpenAI embeddings work best on ~500-800 chars
# Too big = loses precision, Too small = loses context

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,        # Max 800 characters per chunk
    chunk_overlap=200,     # 200 char overlap between chunks (preserves context)
    separators=["\n\n", "\n", ". ", " "]  # Split on paragraphs > lines > sentences
)

chunks = text_splitter.split_text(full_text)
```

**Example output:**
```python
chunks = [
    "Exposure and Response Prevention (ERP) is a specific type of Cognitive Behavioral Therapy...",
    "...that helps people confront their fears. The exposure part involves gradually facing...",
    "...facing situations that trigger obsessions. The response prevention part means..."
]
# 3 chunks from 1 document
```

#### Step 4: Generate embeddings for each chunk
```python
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

for chunk_text in chunks:
    # Call OpenAI API to convert text → vector
    response = client.embeddings.create(
        input=[chunk_text],
        model="text-embedding-3-small"  # OpenAI's embedding model
    )
    
    embedding = response.data[0].embedding
    # embedding = [0.041, -0.006, -0.013, ..., -0.009]  (1536 numbers)
```

**What is an embedding?**
- A list of 1536 numbers that represent the "meaning" of text
- Similar concepts = similar vectors
- Example: 
  - "OCD treatment" → [0.5, 0.2, -0.3, ...]
  - "anxiety therapy" → [0.48, 0.19, -0.29, ...] (similar!)
  - "pizza recipe" → [-0.1, 0.9, 0.7, ...] (very different)

#### Step 5: Save chunks to database
```python
chunk_record = ResourceChunk(
    resource_id=resource_id,
    therapist_id=resource.therapist_id,
    chunk_index=idx,
    chunk_text=chunk_text,
    embedding=embedding  # PostgreSQL vector(1536) type
)
db.add(chunk_record)
```

**Database table `resource_chunks`:**
```
id  | resource_id | chunk_text                                      | embedding
1   | 10          | "Exposure and Response Prevention..."           | [0.041, -0.006, ...]
2   | 10          | "...that helps people confront their fears..." | [0.038, -0.004, ...]
3   | 10          | "...facing situations that trigger..."         | [0.042, -0.007, ...]
```

#### Step 6: Update resource status
```python
resource.status = "ready"           # Now searchable!
resource.total_chunks = len(chunks) # e.g., 511 chunks
job.status = "completed"
db.commit()
```

---

## 💬 PART 3: ASKING QUESTIONS (The RAG Query Flow)

### Step 1: Therapist opens Nirbaan AI tab

**File:** `TherapistDashboard.jsx` (Line 162)
```jsx
{activeTab === 'nirbaan-ai' && <RAGChat />}
```

---

### Step 2: Therapist types question

**File:** `frontend/src/components/RAGChat.jsx` (Line 11-38)

```jsx
const handleSubmit = async (e) => {
  e.preventDefault();
  
  // Add user message to chat
  const userMessage = { type: 'user', content: "What is ERP therapy?" };
  setChatHistory([...chatHistory, userMessage]);
  
  // Call RAG API
  const response = await generateAnswer("What is ERP therapy?");
  
  // Add AI response to chat
  const aiMessage = {
    type: 'ai',
    content: response.answer,
    sources: response.sources,      // Which documents were used
    chunksUsed: response.chunks_used // How many chunks
  };
  setChatHistory([...chatHistory, userMessage, aiMessage]);
};
```

---

### Step 3: Frontend calls RAG endpoint

**File:** `resource.api.js` (Line 89-99)
```javascript
const response = await axiosInstance.post('/resources/rag/answer', {
  query: "What is ERP therapy?",
  top_k: 6  // Return top 6 most relevant chunks
});
```

---

### Step 4: Backend RAG endpoint processes request

**File:** `router.py` (Line 348-384)
```python
@router.post("/rag/answer")
def generate_answer(
    request: RAGAnswerRequest,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)
):
    # Step 1: Find relevant chunks
    chunks = rag_service.retrieve_chunks(
        db=db,
        therapist_id=current_therapist.id,
        query=request.query,
        top_k=request.top_k
    )
    
    # Step 2: Generate answer using chunks
    result = rag_service.generate_answer(
        query=request.query,
        chunks=chunks
    )
    
    return RAGAnswerResponse(
        query=request.query,
        answer=result["answer"],
        sources=result["sources"],
        chunks_used=result["chunks_used"]
    )
```

---

### Step 5: Vector Similarity Search (Finding relevant chunks)

**File:** `backend/app/resources/rag_service.py` (Line 25-83)

#### 5.1: Convert query to embedding
```python
def retrieve_chunks(self, db, therapist_id, query, top_k=6):
    # Convert question to vector (same model as chunks)
    query_embedding = self._generate_query_embedding(query)
    # "What is ERP therapy?" → [0.043, -0.005, -0.012, ...]
```

#### 5.2: Database vector search
```python
# PostgreSQL with pgvector extension
# <=> is "cosine distance" operator (finds similar vectors)

sql = """
    SELECT 
        rc.chunk_text,
        r.title as resource_title,
        1 - (rc.embedding <=> CAST(:query_embedding AS vector)) as similarity
    FROM resource_chunks rc
    JOIN resources r ON rc.resource_id = r.id
    WHERE rc.therapist_id = :therapist_id
        AND r.status = 'ready'
    ORDER BY rc.embedding <=> CAST(:query_embedding AS vector)
    LIMIT :top_k
"""

result = db.execute(sql, {
    "query_embedding": "[0.043,-0.005,...]",  # Query vector
    "therapist_id": 1,
    "top_k": 6
})
```

**What happens:**
1. PostgreSQL compares query vector `[0.043, -0.005, ...]` with ALL chunk vectors in database
2. Calculates similarity score (0.0 to 1.0, higher = more similar)
3. Returns top 6 most similar chunks

**Example result:**
```python
chunks = [
    {
        "chunk_text": "Exposure and Response Prevention (ERP) is a type of CBT...",
        "resource_title": "ERP Therapy Guide",
        "similarity_score": 0.89  # Very relevant!
    },
    {
        "chunk_text": "ERP involves gradual exposure to feared situations...",
        "resource_title": "OCD Treatment Book",
        "similarity_score": 0.85
    },
    ...
]
```

---

### Step 6: Generate AI answer using retrieved chunks

**File:** `rag_service.py` (Line 85-166)

#### 6.1: Build context from chunks
```python
context_parts = []
for idx, chunk in enumerate(chunks, 1):
    context_parts.append(
        f"[Source {idx}: {chunk['resource_title']}]\n{chunk['chunk_text']}"
    )

context = "\n\n---\n\n".join(context_parts)
```

**Example context:**
```
[Source 1: ERP Therapy Guide]
Exposure and Response Prevention (ERP) is a type of CBT...

---

[Source 2: OCD Treatment Book]
ERP involves gradual exposure to feared situations...
```

#### 6.2: Create system prompt
```python
system_prompt = """You are a knowledgeable therapy assistant.

CRITICAL RULES:
1. Answer ONLY using information from the provided sources
2. If sources don't contain the answer, say "I don't have enough information"
3. Always cite your sources by mentioning the resource title
4. Be concise, clear, and professional
5. Do NOT make up information

SOURCES:
{context}"""
```

#### 6.3: Call OpenAI ChatGPT API
```python
response = client.chat.completions.create(
    model="gpt-4o-mini",  # ChatGPT model
    messages=[
        {"role": "system", "content": system_prompt.format(context=context)},
        {"role": "user", "content": "What is ERP therapy?"}
    ],
    temperature=0,  # No creativity, stick to sources
    max_tokens=800
)

answer = response.choices[0].message.content
```

**Example answer:**
```
"Exposure and Response Prevention (ERP) is a specific type of Cognitive 
Behavioral Therapy designed to help people confront their fears through 
gradual exposure to anxiety-triggering situations while preventing 
compulsive responses. This evidence-based treatment is particularly 
effective for OCD (ERP Therapy Guide, OCD Treatment Book)."
```

#### 6.4: Return to frontend
```python
return {
    "answer": answer,
    "sources": [
        {
            "resource_title": "ERP Therapy Guide",
            "chunk_text": "Exposure and Response Prevention...",
            "resource_id": 10
        },
        ...
    ],
    "chunks_used": 6
}
```

---

### Step 7: Display answer in chat

**File:** `RAGChat.jsx` (Line 48-70)
```jsx
<p>{message.content}</p>  {/* The AI answer */}

{message.sources && message.sources.length > 0 && (
  <div className="sources-section">
    <strong>📚 Sources:</strong>
    {message.sources.map((source) => (
      <div className="source-card">
        <div className="source-title">{source.resource_title}</div>
        <div className="source-preview">{source.chunk_text}</div>
      </div>
    ))}
  </div>
)}
```

---

## 🔐 AUTHENTICATION FLOW

Every API call includes JWT token for security.

**File:** `frontend/src/api/axios.js` (Line 12-24)
```javascript
axiosInstance.interceptors.request.use((config) => {
  // Read from localStorage
  const authStorage = localStorage.getItem('auth-storage');
  const { state } = JSON.parse(authStorage);
  
  // Add Bearer token to every request
  config.headers.Authorization = `Bearer ${state.token}`;
  return config;
});
```

**Backend verification:** `backend/app/auth/utils.py` (Line 63-75)
```python
async def get_current_therapist(token: str, db: Session):
    # Decode JWT token
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    email = payload.get("sub")
    
    # Find therapist in database
    therapist = db.query(Therapist).filter(Therapist.email == email).first()
    
    return therapist  # Used in request handlers
```

This ensures:
- Only logged-in therapists can upload/query
- Each therapist sees ONLY their own resources (therapist_id filter in SQL)

---

## 📊 DATABASE SCHEMA

**File:** `backend/app/resources/models.py`

```python
# Main resource record
class Resource(Base):
    id: int (primary key)
    therapist_id: int (foreign key → therapists.id)
    title: str ("ERP Therapy Guide")
    original_filename: str ("erp_guide.pdf")
    r2_bucket: str ("nirbaan-knowledge-base")
    r2_key: str ("therapist_1/resource_10/erp_guide.pdf")
    file_type: str ("pdf" or "txt")
    mime_type: str ("application/pdf")
    size_bytes: int (file size)
    status: str ("initiated" → "uploaded" → "processing" → "ready")
    total_pages: int (for PDFs)
    total_chunks: int (511)
    error_message: str (if processing failed)
    created_at: datetime

# Text chunks with embeddings
class ResourceChunk(Base):
    id: int
    resource_id: int (foreign key → resources.id)
    therapist_id: int
    chunk_index: int (0, 1, 2...)
    chunk_text: str (actual content)
    embedding: Vector(1536) (OpenAI embedding vector)

# Processing job tracker
class IngestionJob(Base):
    id: int
    resource_id: int
    therapist_id: int
    status: str ("queued" → "processing" → "completed"/"failed")
    started_at: datetime
    completed_at: datetime
```

---

## 🔄 COMPLETE DATA FLOW DIAGRAM

```
UPLOAD FLOW:
┌─────────────┐
│  Therapist  │ Clicks "Upload & Process"
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ ResourceManager.jsx (Frontend)          │
│ - handleUpload() / handleUrlUpload()    │
└──────┬──────────────────────────────────┘
       │ HTTP POST
       ▼
┌─────────────────────────────────────────┐
│ resource.api.js                         │
│ - uploadResource() or uploadFromUrl()   │
└──────┬──────────────────────────────────┘
       │ Axios + JWT token
       ▼
┌─────────────────────────────────────────┐
│ Backend: router.py                      │
│ - /resources/init-upload                │
│ - /resources/{id}/confirm-upload  OR    │
│ - /resources/from-url                   │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ Create Resource in PostgreSQL           │
│ Upload file to Cloudflare R2            │
│ Create IngestionJob                     │
└──────┬──────────────────────────────────┘
       │ Trigger
       ▼
┌─────────────────────────────────────────┐
│ Celery Worker: tasks.py                 │
│ - ingest_resource_task()                │
│   1. Download from R2                   │
│   2. Extract text (PyPDF2/BeautifulSoup)│
│   3. Split into chunks                  │
│   4. Generate embeddings (OpenAI)       │
│   5. Save to resource_chunks table      │
│   6. Update status → "ready"            │
└─────────────────────────────────────────┘

QUERY FLOW:
┌─────────────┐
│  Therapist  │ Types question in Nirbaan AI
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ RAGChat.jsx (Frontend)                  │
│ - handleSubmit()                        │
└──────┬──────────────────────────────────┘
       │ HTTP POST
       ▼
┌─────────────────────────────────────────┐
│ resource.api.js                         │
│ - generateAnswer(query)                 │
└──────┬──────────────────────────────────┘
       │ Axios + JWT token
       ▼
┌─────────────────────────────────────────┐
│ Backend: router.py                      │
│ - /resources/rag/answer                 │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ rag_service.py                          │
│ - retrieve_chunks()                     │
│   1. Embed query with OpenAI            │
│   2. Vector search in PostgreSQL        │
│   3. Return top_k similar chunks        │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ rag_service.py                          │
│ - generate_answer()                     │
│   1. Build context from chunks          │
│   2. Create system prompt               │
│   3. Call OpenAI ChatGPT API            │
│   4. Return answer + sources            │
└──────┬──────────────────────────────────┘
       │ JSON response
       ▼
┌─────────────────────────────────────────┐
│ RAGChat.jsx                             │
│ - Display answer + sources in chat UI   │
└─────────────────────────────────────────┘
```

---

## 🛠️ KEY TECHNOLOGIES

1. **React** - Frontend UI framework
2. **FastAPI** - Python backend web framework
3. **PostgreSQL + pgvector** - Database with vector similarity search
4. **Cloudflare R2** - File storage (S3-compatible)
5. **Celery** - Background task queue
6. **Redis (Memurai)** - Message broker for Celery
7. **OpenAI API** - Embeddings (text-embedding-3-small) + ChatGPT (gpt-4o-mini)
8. **PyPDF2** - PDF text extraction
9. **BeautifulSoup** - HTML parsing for web links
10. **SQLAlchemy** - Python database ORM

---

## ⚠️ WHY WEB LINKS MIGHT NOT WORK

**Potential issue:** Web content extraction might be failing or producing low-quality text.

**Check if URL was processed:**
```sql
SELECT id, title, status, total_chunks FROM resources 
WHERE original_filename LIKE '%from_url%';
```

**If `total_chunks = 0` or `status = 'failed'`:**
1. URL content might be too short (< 100 chars)
2. Website blocked the scraper (needs better User-Agent)
3. JavaScript-heavy site (BeautifulSoup can't run JS)
4. Celery worker crashed during processing

**Debug by checking:**
- Celery worker logs: Look for errors during ingestion
- Database: Check `error_message` field in `resources` table
- Test URL processor directly in Python console

---

## 📝 SUMMARY

**Upload Flow:** Frontend → Backend API → R2 Storage → Celery Worker → Extract Text → Chunk → Embed → Save to DB

**Query Flow:** User Question → Embed Query → Vector Search → Get Chunks → Send to ChatGPT with Context → Return Answer

**Files involved:**
- **Frontend:** `ResourceManager.jsx`, `RAGChat.jsx`, `resource.api.js`
- **Backend:** `router.py`, `rag_service.py`, `tasks.py`, `url_processor.py`, `models.py`
- **Database:** `resources`, `resource_chunks`, `ingestion_jobs` tables
- **External:** OpenAI API, Cloudflare R2, PostgreSQL with pgvector

The whole system is designed to give therapists **grounded AI answers** - meaning the AI can ONLY answer from uploaded documents, preventing hallucination and ensuring accuracy.
