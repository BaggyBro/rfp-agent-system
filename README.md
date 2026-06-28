# AI-Powered RFP Processing Pipeline

An end-to-end automated RFP (Request for Proposal) processing system that leverages a multi-agent AI architecture to analyze procurement documents, match items against a product catalog, perform risk analysis, and generate executive summaries.

---

## 🏗️ Architecture & Pipeline Flow

The backend orchestrates **six specialized AI agents** sequentially using **LangGraph** to process shared state:

```
[ RFP PDF Upload ]
        │
        ▼
 1. Sales Agent         ──▶ Extracts text, chunks, embeds (Pinecone), & generates abstract (Redis/Gemini)
        │
        ▼
 2. Technical Agent     ──▶ Extracts technical requirements & queries database for matches (PostgreSQL)
        │
        ▼
 3. Pricing Agent       ──▶ Heuristically calculates conductor & armor cost multipliers
        │
        ▼
 4. Comparison Agent    ──▶ Ranks products based on a custom composite score
        │
        ▼
 5. Risk & Compliance   ──▶ Assesses standards compliance and sets risk tier (LOW/MEDIUM/HIGH)
        │
        ▼
 6. Master Agent        ──▶ Synthesizes all data into a final procurement decision brief
        │
        ▼
[ Executive Recommendation ]
```

---

## 🛠️ Tech Stack

| Component | Technology | Version / Description |
| :--- | :--- | :--- |
| **Backend** | Python / FastAPI | 3.12 / 0.124.4 (Asynchronous REST API) |
| **Orchestration** | LangGraph / LangChain | Multi-agent state management DAG |
| **Reasoning LLM** | Google Gemini 2.0 Flash | Fast JSON extraction, reasoning, and summarization |
| **Embeddings** | SentenceTransformers | `all-mpnet-base-v2` (768-dimensional local embeddings) |
| **Vector DB** | Pinecone | Index `ey` (768-dim, cosine similarity) |
| **Relational DB** | PostgreSQL | Holds product catalog data |
| **Cache Store** | Redis | Caches intermediate agent states (24h TTL) |
| **Frontend** | Next.js 15 / Tailwind CSS 4 | React 19 / TypeScript UI for uploading and reviewing |

---

## 📁 Repository Layout

```
ey_hack/
├── agents/             # LangGraph agent definitions
│   ├── sales_agent.py, technical_agent.py, pricing_agent.py, 
│   ├── comparison_agent.py, risk_compliance_agent.py, master_agent.py
├── utils/              # Shared utilities (DB, Redis, Vector, LLM, Text)
├── app/                # Next.js 15 Frontend
├── scripts/            # Database scripts & mock data
│   ├── generate_database.py
│   └── dummy_cable_catalog_extended.csv
├── tests/              # Pytest backend test suite
├── main.py             # FastAPI App & CLI Entrypoint
├── requirements.txt    # Backend Dependencies
└── README.md           # Documentation
```

---

## ⚙️ Configuration & Setup

### 1. Environment Configuration (`.env`)
Create a `.env` file in the root directory:
```bash
# LLM & Vector API Keys
API_KEY=AIzaSy...            # Google Gemini API key (acts as GOOGLE_API_KEY)
PINECONE_KEY=pcsk_...        # Pinecone API key
PINECONE_INDEX=ey

# Databases
POSTGRES_URI=postgresql+psycopg2://postgres:password@localhost/rfp_catalog
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Local Embeddings
EMBED_MODEL_NAME=sentence-transformers/all-mpnet-base-v2
```

### 2. Database Seeding & Initialization
Generate a mock catalog CSV containing 200 products:
```bash
python scripts/generate_database.py
```
Initialize the PostgreSQL `products` table and import the generated CSV:
```sql
CREATE TABLE products (
    sku VARCHAR PRIMARY KEY,
    product_name VARCHAR,
    voltage VARCHAR,
    insulation VARCHAR,
    core_count INTEGER,
    cross_section_mm2 FLOAT,
    armor VARCHAR,
    standard VARCHAR,
    conductor_material VARCHAR,
    base_price FLOAT
);

-- Copy CSV data into the PostgreSQL table
\copy products FROM 'scripts/dummy_cable_catalog_extended.csv' DELIMITER ',' CSV HEADER;
```

---

## 🚀 Running the System

### 💻 Backend Setup & Execution
1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. **CLI Mode** (Run a standalone check on a PDF/Text RFP):
   ```bash
   python main.py --rfp-path sample_rfp.pdf --rfp-id demo-001
   ```
3. **Web Server Mode** (Start FastAPI):
   ```bash
   uvicorn main:app --reload --port 8000
   ```

### 🌐 Frontend Setup & Execution
1. Navigate to the frontend directory:
   ```bash
   cd app
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
4. Access the dashboard at [http://localhost:3000](http://localhost:3000).

---

## 🔌 API Summary

* **`POST /rfp-upload/`** (Accepts `multipart/form-data` containing PDF/Text file)
* **`POST /process-rfp-text/`** (Accepts raw text string input)
* **`GET /health`** (Returns service health status)

---

## 🧪 Testing

Run backend tests using `pytest` (stubs are configured to run without databases):
```bash
pytest tests/
```
