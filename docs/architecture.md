# Architectural Specification: Mutual Fund FAQ Assistant (Facts-Only Q&A)

This document details the multi-phase technical architecture for building a lightweight, compliant, facts-only Retrieval-Augmented Generation (RAG) assistant for mutual fund queries, based on the [problem statement](file:///c:/Milestone%202/docs/problemstatement.md).

---

## Architectural Overview

The assistant is designed to prioritize **verifiable accuracy and compliance** over generative creativity. It uses a semantic routing layer to separate factual queries from advisory or subjective queries, processes factual queries using a high-precision RAG pipeline, and enforces strict compliance guardrails on outputs before rendering them to the user.

```mermaid
graph TD
    %% Styling
    classDef default fill:#1a1a24,stroke:#3b3b4f,color:#fff;
    classDef client fill:#00d09c,stroke:#00a37b,color:#fff;
    classDef logic fill:#2a2b3d,stroke:#5c5d80,color:#fff;
    classDef database fill:#1d2d44,stroke:#3e5c76,color:#fff;
    classDef external fill:#4a154b,stroke:#6b2c70,color:#fff;

    %% Elements
    User([User Query]) :::client --> UI[Minimalist Web UI] :::client
    UI --> API[FastAPI Backend Gateway] :::logic
    
    %% Semantic Router
    API --> Router{Semantic Query Router} :::logic
    
    %% Refusal Flow
    Router -- "Advisory / Subjective / Comparative" --> Refusal[Refusal Engine] :::logic
    Refusal --> EduLink[Educational Link Selector] :::logic
    EduLink --> UI
    
    %% FAG RAG Flow
    Router -- "Facts-Only / Verifiable Query" --> Retriever[Hybrid Retriever] :::logic
    Retriever --> VecDB[(ChromaDB Vector Store)] :::database
    Retriever --> Context[Context Aggregator & Pinning] :::logic
    Context --> LLM[LLM Synthesis Engine] :::logic
    
    %% Guardrails
    LLM --> Guard{Compliance & Formats Guardrail} :::logic
    Guard -- "Passed (<= 3 Sentences, Factual, Correct Citations)" --> UI
    Guard -- "Failed (Advisory Language, Hallucinations, Formatting Error)" --> Fallback[Regeneration or Refusal Router] :::logic
    Fallback --> Refusal
    
    %% Ingestion Pipeline
    Groww_URLs[Groww Fund Product Pages] :::external --> Crawler[HTML Scraper & Parser] :::logic
    Crawler --> Chunking[Semantic Chunker & Metadata Tagger] :::logic
    Chunking --> Embed[Embedding Generator] :::logic
    Embed --> VecDB
```

---

## Phase 0: Target Schemes & Groww Source Reference

For this project, the core target mutual fund schemes and their Groww product pages are defined as follows:

1.  **HDFC Mid-Cap Opportunities Fund (Direct Growth)**
    *   URL: [https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth](https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth)
2.  **HDFC Flexi Cap Fund / Equity Fund (Direct Growth)**
    *   URL: [https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth](https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth)
3.  **HDFC Focused 30 Fund (Direct Growth)**
    *   URL: [https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth](https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth)
4.  **HDFC ELSS Tax Saver Fund (Direct Plan Growth)**
    *   URL: [https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth](https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth)
5.  **HDFC Top 100 / Large Cap Fund (Direct Growth)**
    *   URL: [https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth](https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth)

---

## Phase 1: Corpus Definition & Data Ingestion Pipeline

The search corpus is strictly constrained to the 5 Groww product URLs defined in Phase 0. No other external sources, documents, AMC portals, or PDFs will be ingested or indexed.

To implement this systematically, Phase 1 is broken down into the following sequential subphases:

### Subphase 1.1: Web Scraper Implementation (Network Layer)
*   **Objective:** Robustly download and cache the raw HTML pages from the 5 Groww URLs.
*   **Implementation Details:**
    *   Utilizes a Python script (`scraper.py`) that runs HTTP requests decorated with modern browser headers (`User-Agent`, `Accept-Language`, etc.) to minimize bot-detection filters.
    *   Saves raw HTML responses locally to `data/raw/{scheme_id}.html` to prevent repeated network hits and ensure reproducibility.
    *   Implements error-resilience, logging non-200 HTTP statuses and raising errors if URLs fail to load.
*   **Automated Scheduling (GitHub Actions Workflow):**
    *   To keep the mutual fund data continuously updated, a GitHub Action workflow (`.github/workflows/data_refresh.yml`) is scheduled to run daily (e.g., at 04:30 UTC / 10:00 AM IST).
    *   **Workflow Operations:**
        1. Checks out the main codebase.
        2. Sets up Python.
        3. Installs dependencies (`requests`, `beautifulsoup4`).
        4. Triggers the ingestion pipeline (`python -m src.phase1_ingestion.main --force`) to scrape fresh HTML and rebuild `corpus.json`.
        5. Commits any updated HTML cache files and `corpus.json` changes back to the repository.
        6. Can trigger Phase 2 index regeneration upon successful ingestion commits.

### Subphase 1.2: HTML Parser Development (Data Extraction)
*   **Objective:** Clean raw HTML and extract the factual data structures.
*   **Implementation Details:**
    *   Uses `BeautifulSoup4` inside a module (`parser.py`) to parse cached raw HTML files.
    *   Implements section extraction targeting specific CSS class names, tags, or page markers for:
        *   **Scheme Core Info:** Expense Ratio, Exit Load, Benchmark index, Riskometer category.
        *   **Investment Thresholds:** Minimum SIP amount, minimum lump-sum investment.
        *   **Organizational Data:** Fund Managers, launch date, AUM.
    *   Discards dynamic or irrelevant layout tags (such as navigation bars, user review sections, similar fund recommendations, footer links).

### Subphase 1.3: Semantic Section Chunking & Structuring
*   **Objective:** Divide extracted text into semantically cohesive paragraphs without breaking numeric/factual contexts.
*   **Implementation Details:**
    *   Splits parsed data logically by target sections (e.g. creating one chunk specifically containing all Exit Load definitions, another containing Benchmark and Riskometer details).
    *   Enforces a strict sliding-window overlap of 100 characters to prevent loss of details across boundaries.
    *   Validates that no numerical metric (like exit load percentages) is disconnected from its description text.

### Subphase 1.4: Metadata Enrichment & Corpus Serialization
*   **Objective:** Structure each chunk with its raw text and routing metadata, then serialize the final database.
*   **Implementation Details:**
    *   Appends a structured `metadata` object to every text chunk containing:
        *   `source_url`: The original Groww product page link.
        *   `scheme_name`: The canonical scheme name from the config (e.g., `"HDFC Mid-Cap Opportunities Fund (Direct Growth)"`).
        *   `doc_type`: Hardcoded source classification `"Groww Product Page"`.
        *   `last_updated`: Ingestion timestamp.
        *   `metric_tags`: Search-optimized tags identifying the specific mutual fund parameters present in the text (e.g., `"nav"`, `"aum"`, `"expense_ratio"`, `"exit_load"`).
    *   Writes the output as a clean, list-of-objects JSON format to `data/processed/corpus.json`.
    *   **Data Structure Example:**
        ```json
        {
          "text": "Overview of HDFC Mid Cap Fund Direct Growth: This scheme is an Equity Mutual Fund categorized as Mid Cap. As of 25 Jun '26, its Net Asset Value (NAV) is ₹226.92. The scheme has a Groww rating of 5 stars. The Total Assets Under Management (AUM) is ₹97,350.48 Cr. The Expense Ratio is 0.75%. The Riskometer category is classified as Very High Risk.",
          "metadata": {
            "source_url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
            "doc_type": "Groww Product Page",
            "scheme_name": "HDFC Mid-Cap Opportunities Fund (Direct Growth)",
            "last_updated": "2026-06-28",
            "metric_tags": [
              "nav",
              "rating",
              "aum",
              "fund_size",
              "expense_ratio",
              "risk",
              "riskometer",
              "overview"
            ]
          }
        }
        ```

---

## Phase 2: Indexing & Retrieval Engine

The retrieval engine maps user queries to the precise context block containing the required factual answer using a local vector store and hybrid keyword ranking.

### 1. Vector Database & Embeddings
*   **Embedding Model:** Local `all-MiniLM-L6-v2` via the `sentence-transformers` library (fully self-contained, offline operation, 384-dimension embeddings).
*   **Vector Store:** **ChromaDB** persistent SQLite store saved locally at `data/vector_db/`.
*   **Indexing Pipeline (`indexer.py`):** On rebuild, the collection is cleared to prevent duplicates, and the 30 chunks are loaded from `corpus.json` and loaded into Chroma.

### 2. Hybrid Retrieval & RRF Mechanism (`retriever.py`)
To ensure high keyword fidelity for financial metrics (e.g., exact AUM or exit load numbers) and eliminate fund cross-contamination, the system uses a **four-step retrieval pipeline**:

1.  **Query Entity Classifier (Scheme Pre-Filtering):**
    *   The query is scanned for keywords mapping to our 5 target HDFC schemes (e.g. "elss", "mid cap", "top 100").
    *   If a specific scheme is matched, a metadata constraint is passed to both Dense and Sparse retrievers:
        `where_filter = {"scheme_name": "<Canonical Scheme Name>"}`
        This reduces search scope from 30 chunks to exactly the 6 chunks of that fund.
2.  **Dense Semantic Querying:**
    *   ChromaDB queries vectors using Cosine Distance (`1 - cosine_similarity`), returning the top 10 closest document chunks matching the query.
3.  **Dynamic Subset-Specific BM25 Search:**
    *   The corpus is filtered in-memory to only include the matching scheme's chunks.
    *   A local `BM25Okapi` model is fit dynamically on this filtered subset, scoring tokenized query terms against tokenized chunks.
4.  **Reciprocal Rank Fusion (RRF) Re-ranking:**
    *   Since vector distance scores and BM25 scores are on incompatible scales, we rank candidates from each search from $1$ to $K$ ($K=10$), and merge them using:
        $$\text{RRF\_Score}(d) = \frac{1}{60 + \text{Rank}_{\text{Dense}}(d)} + \frac{1}{60 + \text{Rank}_{\text{Sparse}}(d)}$$
    *   The chunks are sorted by RRF score, and the top 3 highest scoring chunks are retrieved.

---

## Phase 3: Semantic Router & Query Classification

To protect against compliance violations, queries are routed dynamically before they reach the main generative pipeline.

```
                  [User Input]
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
    Factual/Verifiable     Advisory/Subjective
    (e.g., "Exit load?")   (e.g., "Should I buy?")
             │                   │
             ▼                   ▼
      [RAG Pipeline]      [Refusal Engine]
```

### 1. Query Classifier Rules
*   **Factual Queries (Allowed):** Expense ratios, exit load details, minimum SIP, ELSS lock-in durations, riskometer categories, benchmark indexes, operational processes (downloads, reports).
*   **Advisory/Subjective Queries (Blocked):** Market predictions, investment advice, comparisons of performance metrics, "better/best" recommendations, portfolio allocation.
*   **Privacy & Personal Information Filter (Strictly Blocked):** Queries requesting or containing sensitive Personal Identifiable Information (PII) such as PAN numbers, Aadhaar, account numbers, OTPs, email addresses, or phone numbers.
*   **Refusal without URL Citation:** If the system classifies a query as out-of-scope, advisory, containing PII, or if the retrieved search context does not contain the answer (unknown query), the system must route to the Refusal Engine and **must not attach any citation URL** or links that might lead to login screens or personal data request fields.

### 2. Routing Implementation
*   **Methodology:** A lightweight classifier combining deterministic keyword/regex checks (for PII and common advisory terms) and an LLM-based classifier for semantic category detection.
*   **Educational Routing:** If a query is identified as advisory, it is immediately routed to the **Refusal Engine** to generate a compliant refusal block.
*   **Safety Routing:** If a query is classified as containing PII or is unknown, it is routed to a safe refusal state with zero URL links.

---

## Phase 4: Prompt Engineering & LLM Synthesis

Once a query is determined to be factual, the prompt template constraints the LLM from hallucinating or inserting opinions.

### 1. Strict System Prompt Template
```yaml
System Prompt:
You are a facts-only assistant for HDFC Mutual Fund. Your sole task is to answer the user's question using the provided verified context.
Strictly adhere to the following rules:
1. Provide only factual, objective information derived from the provided context.
2. Do not offer investment opinions, performance comparisons, projections, or advice.
3. Your answer must be concise and limited to a maximum of 3 sentences.
4. Include exactly one citation link mapping to the source document URL.
5. Do not include any external markdown or HTML links other than the exact source URL provided in the context metadata.
6. Provide a footer: "Last updated from sources: <date>" using the most recent date found in the retrieved metadata.

Context:
---
{retrieved_context}
---

Question: {user_query}
```

### 2. Guardrails & Compliance Validation (Output Filters)
A post-generation parsing layer inspects the raw output before sending it to the frontend:
*   **Constraint 1: Sentence Count:** Splitting by sentences using regex or NLTK to verify the total count is $\le 3$.
*   **Constraint 3: Citations:** Ensuring exactly one valid URL exists in the response and matching it against the source URL list.
*   **Constraint 4: Advisory Checks:** Scanning the generated answer for blacklist terms (e.g., "should", "recommend", "better", "buy", "sell", "growth potential", "outperform").
*   *Action on Failure:* If any constraint is violated, the system triggers a self-correction loop or defaults to a standardized refusal message.

---

## Phase 5: Refusal & Educational Engine

For out-of-scope or advisory inputs, the Refusal Engine serves as a polite gateway, ensuring users are educated without being advised.

### 1. Standardized Refusal Template
*   **Core Message:** Polite, direct statement reinforcing the facts-only constraint.
*   **Educational Link Injection:** Automatically links to trusted educational hubs (e.g., AMFI Investor Education or SEBI Investor FAQs).
*   **Example Response:**
    > "I am a facts-only FAQ assistant and cannot provide investment advice or compare scheme performances. To make informed investment decisions, please refer to official scheme factsheets or read educational resources on the [AMFI Investor Education Website](https://www.amfiindia.com/investor-corner/education-series)."

---

## Phase 6: Minimalist Web Interface & API Layer

The system features a simple web page matching Groww’s clean design language.

### 1. Design & Styling (Aesthetic Specification)
*   **Color Palette:**
    *   Primary/Success Accent: Modern Green (`#00d09c` / `#00b889`)
    *   Dark Mode Background: `#0f1115` (Deep Slate)
    *   Cards/Containers: `#1a1e26`
    *   Borders: Solid thin `#2a2f3a`
    *   Text: High-contrast `#f0f2f5`, Muted body `#9ba3b0`
*   **Typography:** Google Font `Outfit` or `Inter`, fallback to system sans-serif.
*   **Layout Structure:**
    *   **Header:** Title "Mutual Fund FAQ Assistant" with a permanent subtitle/badge stating **"Facts-only. No investment advice."** in a warning-orange or vivid-green outlined banner.
    *   **Quick Start Panels:** Three clickable cards representing example factual queries:
        1.  *"What is the exit load for HDFC Mid-Cap Opportunities Fund?"*
        2.  *"How can I download my capital gains statement?"*
        3.  *"What is the riskometer classification of the HDFC ELSS Tax Saver?"*
    *   **Chat Container:** Scrolling message log.
    *   **Footer Badge:** Every response card explicitly shows the single citation button and the metadata source date.

### 2. Backend API Contract
*   **`POST /api/chat`**
    *   **Request Schema:**
        ```json
        {
          "message": "What is the ELSS lock-in period?"
        }
        ```
    *   **Response Schema (Factual):**
        ```json
        {
          "response": "The lock-in period for ELSS (Equity Linked Savings Scheme) funds is 3 years from the date of investment. This is the shortest lock-in period among all Section 80C tax-saving options.",
          "citation": "https://www.amfiindia.com/investor-corner/education-series/elss",
          "last_updated": "2026-06-28",
          "is_refusal": false
        }
        ```
    *   **Response Schema (Refused):**
        ```json
        {
          "response": "I am a facts-only FAQ assistant and cannot provide investment advice. To learn more about mutual funds, please visit the official AMFI Investor Education portal.",
          "citation": "https://www.amfiindia.com/investor-corner/education-series",
          "last_updated": "2026-06-28",
          "is_refusal": true
        }
        ```

---

## Phase 7: Verification & Testing Framework

To ensure the assistant complies with SEBI regulations and remains factual, we define automated evaluations.

### 1. Golden Evaluation Dataset
Create a json-based evaluation suite containing:
*   25 target queries with expected factual answers.
*   25 advisory/subjective queries where the expected classification is `is_refusal: true`.

### 2. Retrieval Evaluation (Retrieval Triad)
*   **Context Relevance:** Evaluates if the retrieved chunks actually match the user query (measured via Cosine Similarity between query embedding and chunk embedding).
*   **Groundedness:** Evaluates if the generated LLM response is derived *strictly* from the context without bringing in external knowledge.
*   **Clarity & Format Checker:** Automated test assertions validating length (character and sentence counts) and citation validity.
