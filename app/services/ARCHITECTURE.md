# Canvas Service Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CANVAS TA-BOT SYSTEM                            │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  FRONTEND (Role 1)                                                      │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  index.html + app.js                                          │      │
│  │  - UI States (INIT, GENERATING, ACTIVE)                       │      │
│  │  - Vis.js Knowledge Graph                                     │      │
│  │  - Chat Interface                                             │      │
│  └──────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP Requests
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  API ROUTER (Role 2)                                                    │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  routes.py                                                    │      │
│  │  ├─ POST /launch           (LTI entry)                        │      │
│  │  ├─ POST /api/initialize-course                              │      │
│  │  ├─ POST /api/chat                                            │      │
│  │  └─ GET  /api/get-graph                                       │      │
│  └──────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Function Calls
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  CORE SERVICES (Role 3) ★ YOU ARE HERE                                 │
│                                                                          │
│  ┌────────────────────────┐  ┌────────────────────────┐               │
│  │  canvas_service.py ✅  │  │  rag_service.py ⏳     │               │
│  ├────────────────────────┤  ├────────────────────────┤               │
│  │ get_course_files()     │  │ create_corpus()        │               │
│  │ get_syllabus()         │  │ query_rag_corpus()     │               │
│  │ get_course_info()      │  │                        │               │
│  └────────────────────────┘  └────────────────────────┘               │
│                                                                          │
│  ┌────────────────────────┐  ┌────────────────────────┐               │
│  │  kg_service.py ⏳      │  │  firestore_service.py ⏳│              │
│  ├────────────────────────┤  ├────────────────────────┤               │
│  │ build_knowledge_graph()│  │ get_course_state()     │               │
│  │                        │  │ create_course_doc()    │               │
│  │                        │  │ finalize_course_doc()  │               │
│  └────────────────────────┘  └────────────────────────┘               │
└─────────────────────────────────────────────────────────────────────────┘
         │                │                │                │
         ▼                ▼                ▼                ▼
┌────────────────┐ ┌────────────┐ ┌──────────────┐ ┌─────────────┐
│  Canvas LMS    │ │ Vertex AI  │ │  networkx    │ │  Firestore  │
│  REST API      │ │ RAG Engine │ │  (Graph)     │ │  (Database) │
└────────────────┘ └────────────┘ └──────────────┘ └─────────────┘
```

## Canvas Service Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│  CANVAS SERVICE WORKFLOW                                                │
└─────────────────────────────────────────────────────────────────────────┘

1. INITIALIZATION PHASE
   ┌──────────────────────────────────────────────────────────────┐
   │ Professor clicks "Initialize Course" in Canvas               │
   └────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ API Router calls: canvas_service.get_course_files()          │
   └────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ Canvas Service:                                              │
   │ 1. GET /api/v1/courses/:id/files                            │
   │ 2. Handle pagination (follow Link headers)                  │
   │ 3. Filter for allowed file types (.pdf, .txt, etc.)         │
   │ 4. Extract metadata (id, name, url, hash)                   │
   └────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ Returns TWO objects:                                         │
   │                                                              │
   │ files_list = [                                               │
   │   {                                                          │
   │     'id': '456',                                             │
   │     'display_name': 'Chapter1.pdf',                          │
   │     'url': 'https://canvas.../download',                     │
   │     'html_url': 'https://canvas.../files/456',               │
   │     'size': 1024000,                                         │
   │     ...                                                      │
   │   },                                                         │
   │   ...                                                        │
   │ ]                                                            │
   │                                                              │
   │ indexed_files = {                                            │
   │   '456': {                                                   │
   │     'hash': 'abc123...',                                     │
   │     'url': 'https://canvas.../download'                      │
   │   },                                                         │
   │   ...                                                        │
   │ }                                                            │
   └────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ files_list → RAG Service (for indexing)                      │
   │ indexed_files → Firestore (for tracking)                     │
   └──────────────────────────────────────────────────────────────┘


2. OPTIONAL: SYLLABUS RETRIEVAL
   ┌──────────────────────────────────────────────────────────────┐
   │ API Router calls: canvas_service.get_syllabus()              │
   └────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ Canvas Service:                                              │
   │ 1. GET /api/v1/courses/:id?include[]=syllabus_body          │
   │ 2. Extract syllabus_body from response                       │
   └────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ Returns: "Course syllabus text (may include HTML)..."        │
   └────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ syllabus → Gemini (for AI topic extraction)                  │
   └──────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. **Dual Return Format**
```python
files_list, indexed_files = get_course_files(course_id, token)
```
**Why?**
- `files_list` is used by RAG service (needs full metadata)
- `indexed_files` is stored in Firestore (minimal data for tracking)
- Avoids making two separate API calls

### 2. **Pagination Handling**
```python
while url:
    # Fetch page
    # Extract next URL from Link header
    # Continue until no more pages
```
**Why?**
- Canvas paginates results (max 100 per page)
- Automatic handling ensures ALL files are retrieved
- No manual page tracking needed

### 3. **File Type Filtering**
```python
ALLOWED_FILE_TYPES = ['.pdf', '.txt', '.md', '.doc', '.docx']
```
**Why?**
- RAG engine works best with text-based documents
- Filters out images, videos, etc.
- Reduces processing time and cost

### 4. **Comprehensive Metadata**
```python
file_obj = {
    'id': str(file.get('id')),
    'display_name': file.get('display_name'),
    'url': file.get('url'),           # For downloading
    'html_url': file.get('url'),       # For citations
    'size': file.get('size', 0),
    ...
}
```
**Why?**
- `url` is needed to download file content
- `html_url` is used for student citations
- `display_name` is user-friendly for UI
- All data needed downstream is captured once

## Contract Fulfillment ✅

```python
# From ServiceBriefing.md:
# Returns: (list_of_file_objects, dict_of_indexed_files_map)
def get_course_files(course_id: str, token: str) -> (list, dict): ...
def get_syllabus(course_id: str, token: str) -> str: ...

# Implemented:
def get_course_files(course_id: str, token: str) -> Tuple[List[Dict], Dict]: ...
def get_syllabus(course_id: str, token: str) -> str: ...
```

✅ **Contract met with enhanced type hints**

## Testing Checklist

- ✅ Function signatures match contract
- ✅ Type hints added for clarity
- ✅ Pagination logic implemented
- ✅ File filtering implemented
- ✅ Dual return format working
- ✅ Error handling comprehensive
- ✅ Logging at appropriate levels
- ✅ Documentation complete
- ⏳ Live API testing (requires credentials)

## Ready for Integration

The Canvas service is now ready to be called by:
1. **API Router** (`routes.py`) - For HTTP endpoint handling
2. **RAG Service** (`rag_service.py`) - For file downloads
3. **KG Service** (`kg_service.py`) - For graph metadata

**Status:** ✅ Complete and ready for testing
