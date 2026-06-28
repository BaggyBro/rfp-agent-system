# Technical Overview: AI-Powered RFP Processing Pipeline

## Project Summary

An end-to-end automated RFP (Request for Proposal) processing system that uses a multi-agent AI architecture to analyze procurement documents, match products from a catalog, and generate executive recommendations.

## Architecture

### Tech Stack

**Backend:**
- **FastAPI** (Python 3.12) - REST API server
- **LangGraph** - Multi-agent orchestration framework
- **Google Gemini 2.0 Flash** - LLM for reasoning tasks
- **PostgreSQL** - Product catalog database
- **Redis** - Intermediate state caching
- **Pinecone** - Vector database for semantic search
- **sentence-transformers** - 768-dim embeddings

**Frontend:**
- **Next.js 15** - React framework
- **TypeScript 5.7** - Type-safe frontend
- **Tailwind CSS 4** - Utility-first styling

## System Flow

```
PDF Upload → FastAPI → LangGraph Pipeline → 6 AI Agents → Results
```

### Agent Pipeline

```
Sales Agent → Technical Agent → Pricing Agent → Comparison Agent → Risk Agent → Master Agent
```

Each agent processes the shared state and passes enriched data to the next agent.

## Agent Responsibilities

### 1. Sales Agent
- **Input:** Raw PDF bytes
- **Tasks:**
  - Extract text using PyMuPDF
  - Hierarchical chunking (1000 tokens per chunk, 120 token overlap)
  - Generate abstract using Gemini (140 words)
  - Embed chunks (768-dim) and upsert to Pinecone
  - Cache chunks and abstract to Redis
- **Output:** `raw_text`, `chunks`, `abstract`

### 2. Technical Agent
- **Input:** Cleaned text and chunks
- **Tasks:**
  - Extract technical requirements (hybrid: LLM + regex)
    - Voltage, insulation, core count, standard, conductor material
  - Query PostgreSQL product catalog with soft filters
  - Score products based on requirement matches (0-5.0 scale)
  - Cache technical results to Redis
- **Output:** `extracted_requirements`, `matched_products` (with scores)

### 3. Pricing Agent
- **Input:** Matched products
- **Tasks:**
  - Estimate pricing with heuristic multipliers:
    - Copper conductor: +12%
    - Armor: +5%
  - Generate pricing summary (total, average, per-item)
  - Optional LLM analysis for anomaly detection
  - Cache pricing summary to Redis
- **Output:** `pricing_summary`

### 4. Comparison Agent
- **Input:** Matched products + pricing
- **Tasks:**
  - Calculate composite score: `0.7 * match_score + 0.3 * (1/price)`
  - Rank products by composite score
  - Generate LLM explanation for top 3 rankings
  - Cache comparison report to Redis
- **Output:** `comparison_report` (ranked products + methodology)

### 5. Risk & Compliance Agent
- **Input:** Requirements + matched products
- **Tasks:**
  - Detect missing required fields (voltage, insulation, core_count)
  - Check standards compliance (substring match)
  - Assign risk level: LOW/MEDIUM/HIGH
  - Generate LLM risk assessment
  - Cache risk report to Redis
- **Output:** `risk_report` (risk level, missing fields, compliance findings)

### 6. Master Agent
- **Input:** All previous agent outputs
- **Tasks:**
  - Aggregate results from all agents
  - Generate executive recommendation using Gemini
  - Format as professional procurement decision brief
- **Output:** `final_recommendation`, status: `COMPLETED`

## Key Utilities

### `utils/llm.py`
- **`get_llm()`** - Returns configured Gemini 2.0 Flash instance
- **`extract_structured_data()`** - LLM-based JSON extraction
- **`generate_summary()`** - Document summarization
- **`analyze_with_llm()`** - Generic analysis function

### `utils/db.py`
- **`Product` ORM Model** - SQLAlchemy model for catalog
- **`query_products()`** - Soft-filtered product search
- Connection: `postgresql+psycopg2://postgres@localhost/rfp_catalog`

### `utils/redis_store.py`
- **`get_redis_client()`** - Connect to Redis (localhost:6379)
- **`cache_json()`** - Cache with 24h TTL
- **`fetch_json()`** - Retrieve cached data
- Keys: `rfp:{rfp_id}:{stage}` (e.g., `rfp:rfp-api:chunks`)

### `utils/vector_store.py`
- **`get_embed_model()`** - Loads `all-mpnet-base-v2` (768-dim)
- **`get_pinecone_index()`** - Connect to Pinecone index `ey`
- **`upsert_rfp_chunks()`** - Embed and store chunks with metadata

### `utils/text.py`
- **`clean_text()`** - Normalize whitespace
- **`chunk_text()`** - Sliding window chunking
- **`find_sections()`** - Detect document sections via regex

## Frontend Architecture

### Main Component: `app/app/page.tsx`

**Features:**
- Drag-and-drop PDF upload
- Real-time agent activity logs
- Structured result display:
  - Formatted recommendation (markdown parsing)
  - Requirements as key-value pairs
  - Risk badges with compliance stats
  - Top 5 ranked products with pricing

**State Management:**
```typescript
const [status, setStatus] = useState<PipelineStatus>("idle");
const [logs, setLogs] = useState<LogEntry[]>([]);
const [response, setResponse] = useState<PipelineResponse | null>(null);
```

**API Integration:**
```typescript
const res = await fetch(`${API_BASE}/rfp-upload/`, {
    method: "POST",
    body: formData
});
const data = await res.json();
```

## Data Flow

```
1. User uploads PDF (Next.js)
   ↓
2. FastAPI extracts text, builds LangGraph pipeline
   ↓
3. Sales Agent: Chunks → Pinecone, caches → Redis
   ↓
4. Technical Agent: LLM extracts requirements → PostgreSQL query
   ↓
5. Pricing Agent: Estimates costs
   ↓
6. Comparison Agent: Ranks by composite score
   ↓
7. Risk Agent: Validates compliance
   ↓
8. Master Agent: Generates final recommendation
   ↓
9. FastAPI returns JSON response
   ↓
10. Frontend renders structured UI
```

## Integration Points

### Google Gemini 2.0 Flash
- **Model:** `gemini-2.0-flash-exp`
- **Temperature:** 0.3 (semi-deterministic)
- **Usage:** 5-6 LLM calls per pipeline run
  - Abstract generation
  - Requirement extraction
  - Pricing analysis
  - Ranking explanation
  - Risk assessment
  - Final recommendation

### Pinecone Vector Database
- **Index:** `ey` (768 dimensions, cosine similarity)
- **Namespace:** Per RFP ID (`rfp_id`)
- **Vector IDs:** `{rfp_id}-chunk-{i}`
- **Metadata:** `{rfp_id, chunk_index, text}`

### PostgreSQL Catalog
- **Schema:** `products` table
  - Fields: `sku`, `product_name`, `voltage`, `insulation`, `core_count`, `cross_section_mm2`, `armor`, `standard`, `base_price`, `conductor_material`
- **Query Strategy:** Soft filters (only apply where value exists)
- **Sorting:** By `base_price ASC`

### Redis Cache
- **Keys:** `rfp:{rfp_id}:{stage}`
- **TTL:** 24 hours
- **Purpose:** Debug, resume-from-checkpoint (future)
- **Graceful Degradation:** Pipeline works without Redis

## Environment Variables

```bash
# LLM
API_KEY=<Google Gemini API Key>

# Pinecone
PINECONE_KEY=<Pinecone API Key>
PINECONE_INDEX=ey

# PostgreSQL
POSTGRES_URI=postgresql+psycopg2://postgres:<password>@localhost/rfp_catalog

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Embeddings
EMBED_MODEL_NAME=sentence-transformers/all-mpnet-base-v2
```

## Security

### Secrets Management
- API keys in `.env` file (excluded from Git)
- CORS restricted to `http://localhost:3000` (dev)
- Production: Use AWS Secrets Manager or similar

### `.gitignore`
- `.env` - Contains API keys
- `venv/` - Python virtual environment
- `__pycache__/` - Python bytecode
- `app/node_modules/` - Node dependencies
- `app/.next/` - Next.js build artifacts

## Error Handling

### Resilience Strategy
- **LLM Failures:** Graceful fallback (regex extraction, simple text)
- **Database Unavailable:** Return empty lists, continue pipeline
- **Redis Down:** Skip caching, continue execution
- **Pinecone Unavailable:** Log warning, skip vector storage

### Logging
- **Backend:** Python `logging` module
  - INFO: Agent progress, state transitions
  - DEBUG: Detailed operation traces
  - ERROR: Failures with stack traces
- **Frontend:** Browser console + user-facing error messages

## Performance

### Typical Execution Time
- **Sales Agent:** 3-5 seconds (PDF + chunking + LLM + Pinecone)
- **Technical Agent:** 2-3 seconds (LLM + PostgreSQL)
- **Pricing Agent:** 1-2 seconds (calculation + optional LLM)
- **Comparison Agent:** 1-2 seconds (sorting + optional LLM)
- **Risk Agent:** 1-2 seconds (compliance + optional LLM)
- **Master Agent:** 2-3 seconds (LLM recommendation)

**Total:** 10-17 seconds for typical RFP (50-page PDF)

### Bottlenecks
1. Sequential LLM API calls (5-6 calls)
2. Large PDF parsing (>200 pages)
3. CPU-based embeddings (SentenceTransformer)

### Optimization Opportunities
- Parallel LLM calls with `asyncio.gather()`
- GPU acceleration for embeddings
- Redis-based result caching
- Streaming responses via SSE

## Deployment

### Local Development
```bash
# Backend
cd /path/to/ey_hack
source venv/bin/activate
uvicorn main:app --reload --port 8000

# Frontend
cd app/
npm run dev  # Port 3000
```

### Production (Example: AWS)
- **Frontend:** S3 + CloudFront (Next.js static export)
- **Backend:** ECS Fargate (FastAPI containers)
- **Load Balancer:** AWS ALB
- **Databases:** RDS (PostgreSQL), ElastiCache (Redis)
- **Secrets:** AWS Secrets Manager

## API Endpoints

### `POST /rfp-upload/`
- **Request:** `multipart/form-data`
  - `file`: PDF or text file
  - `rfp_id`: String identifier (default: `"rfp-api"`)
- **Response:** JSON
  ```json
  {
    "rfp_id": "rfp-api",
    "status": "COMPLETED",
    "final_recommendation": "...",
    "comparison_report": {...},
    "risk_report": {...},
    "extracted_requirements": {...},
    "matched_products_count": 10
  }
  ```

### `GET /health`
- **Response:** `{"status": "healthy", "service": "RFP Processing Pipeline"}`

## Design Decisions

### Why LangGraph?
- **Stateful orchestration** - Each agent updates shared state
- **DAG execution** - Clear, linear agent flow
- **Observability** - Built-in state tracking and logging
- **Extensibility** - Easy to add new agents or branches

### Why Gemini 2.0 Flash?
- **Fast** - Sub-second responses
- **Large context** - 1M tokens (handles long RFPs)
- **Cost-effective** - Free tier available
- **Structured outputs** - Good at JSON extraction

### Why 768-dim Embeddings?
- **Balance** - Good semantic quality without excessive compute
- **Compatibility** - Pinecone index pre-configured for 768-dim
- **Model** - `all-mpnet-base-v2` is well-tested and performant

### Why PostgreSQL + Redis + Pinecone?
- **PostgreSQL** - Structured catalog queries with SQL
- **Redis** - Fast ephemeral caching
- **Pinecone** - Serverless vector search (scales automatically)

## Future Enhancements

1. **Streaming Pipeline Results** - SSE for real-time agent updates
2. **Semantic Search Integration** - Query Pinecone in technical agent
3. **Multi-RFP Comparison** - Compare multiple RFPs side-by-side
4. **User Feedback Loop** - Thumbs up/down on recommendations
5. **Persistent Sessions** - Redis-based state persistence
6. **Async Pipeline Execution** - Celery task queue
7. **Advanced Analytics** - Track pipeline metrics, agent performance
8. **Multi-language Support** - i18n for frontend

## Project Structure

```
ey_hack/
├── agents/                 # AI agents
│   ├── sales_agent.py
│   ├── technical_agent.py
│   ├── pricing_agent.py
│   ├── comparison_agent.py
│   ├── risk_compliance_agent.py
│   └── master_agent.py
├── utils/                  # Shared utilities
│   ├── llm.py             # Gemini integration
│   ├── db.py              # PostgreSQL ORM
│   ├── redis_store.py     # Redis caching
│   ├── vector_store.py    # Pinecone integration
│   ├── text.py            # Text processing
│   └── state.py           # State type definitions
├── app/                    # Next.js frontend
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx       # Main UI component
│   │   └── globals.css
│   ├── package.json
│   └── tsconfig.json
├── scripts/                # Database setup
│   ├── generate_database.py
│   └── dummy_cable_catalog_extended.csv
├── tests/                  # Test files
├── main.py                 # FastAPI entry point
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (gitignored)
├── .gitignore
└── README.md
```

## Dependencies

### Backend (`requirements.txt`)
```
python-dotenv
redis
sqlalchemy
psycopg2-binary
langgraph
langchain-core
langchain-openai
langchain-community
langchain-google-genai
pymupdf
sentence-transformers
pinecone
pytest
fastapi
uvicorn
python-multipart
```

### Frontend (`app/package.json`)
```json
{
  "dependencies": {
    "next": "15.1.4",
    "react": "19.0.0",
    "react-dom": "19.0.0"
  },
  "devDependencies": {
    "typescript": "5.7.3",
    "tailwindcss": "4.0.0"
  }
}
```

---

**Built with ❤️ for EY Hackathon**


