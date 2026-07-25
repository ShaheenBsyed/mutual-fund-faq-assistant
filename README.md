---
title: HDFC Mutual Fund FAQ Assistant
emoji: 📊
colorFrom: green
colorTo: teal
sdk: docker
pinned: false
app_port: 7860
---

# HDFC Mutual Fund FAQ Assistant

A **facts-only** Retrieval-Augmented Generation (RAG) assistant for 5 selected HDFC Mutual Fund schemes. Answers objective, verifiable queries using data sourced exclusively from official Groww product pages.

> ⚠️ This assistant provides factual data only. It does **not** offer investment advice, performance forecasts, or recommendations.

## Covered Schemes

| Scheme | Type | Benchmark |
|---|---|---|
| HDFC Mid-Cap Opportunities Fund (Direct Growth) | Mid Cap Equity | NIFTY Midcap 150 TRI |
| HDFC Flexi Cap Fund (Direct Growth) | Flexi Cap Equity | NIFTY 500 TRI |
| HDFC Focused 30 Fund (Direct Growth) | Focused Equity | NIFTY 500 TRI |
| HDFC ELSS Tax Saver Fund (Direct Plan Growth) | ELSS | NIFTY 500 TRI |
| HDFC Top 100 / Large Cap Fund (Direct Growth) | Large Cap Equity | NIFTY 100 TRI |

## What you can ask

- Expense Ratio, Exit Load, NAV, AUM
- Minimum SIP / Lump-sum amounts
- Riskometer category, Benchmark index
- Fund Manager details
- ELSS lock-in period and tax implications
- Capital gains statement download guide

## Architecture

```
User Query → FastAPI Backend
              ├── Semantic Query Router  (PII / Advisory / Out-of-scope / Factual)
              ├── Hybrid RAG Retriever   (ChromaDB + BM25 + Reciprocal Rank Fusion)
              └── LLM Synthesis Engine   (Google Gemini + compliance guardrails)
```

## Tech Stack

- **Backend:** FastAPI + Uvicorn
- **Vector Store:** ChromaDB (local persistent)
- **Embeddings:** `all-MiniLM-L6-v2` via sentence-transformers
- **LLM:** Google Gemini (via `google-genai`)
- **Frontend:** Vanilla HTML/CSS/JS (served as FastAPI static files)
