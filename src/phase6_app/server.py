import os
import re
import sys
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

# Resolve workspace path to import modules
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(CURRENT_DIR, "..", "..")))

from src.phase3_router import QueryRouter
from src.phase2_indexing import HybridRetriever
from src.phase4_synthesis import LLMSynthesisEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="Mutual Fund FAQ Assistant Backend",
    description="Factual Q&A API layer for selected HDFC Mutual Fund schemes",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy singletons — loaded on first request to allow uvicorn to bind the port
# before heavy ML models (sentence-transformers + ChromaDB) are pulled into RAM.
# This prevents OOM crashes on memory-constrained hosts (e.g. Render free tier 512 MB).
router = None
retriever = None
synthesis_engine = None

def _load_components():
    """Load all pipeline components. Safe to call multiple times (no-op if already loaded)."""
    global router, retriever, synthesis_engine
    if router and retriever and synthesis_engine:
        return  # Already loaded
    logger.info("Lazy-loading pipeline components (first request)...")
    router = QueryRouter()
    retriever = HybridRetriever()
    synthesis_engine = LLMSynthesisEngine()
    logger.info("All pipeline components loaded successfully.")

# Request & Response Schemas
class ChatRequest(BaseModel):
    message: str = Field(..., max_length=500, description="The user query to be processed")

class ChatResponse(BaseModel):
    response: str
    citation: Optional[str] = None
    last_updated: str
    is_refusal: bool

def clean_factual_response(llm_text: str, default_citation: str, default_date: str) -> Dict[str, Any]:
    """
    Parses citation links and date stamps from the raw LLM response text
    to conform exactly to the required JSON schema output.
    """
    # 1. Extract URL if present in response
    urls = re.findall(r"https?://[^\s)\]]+", llm_text)
    citation = urls[0].rstrip(".,;:") if urls else default_citation
    
    # 2. Extract last updated date
    date_match = re.search(r"last updated from sources:\s*([^\n]+)", llm_text, re.IGNORECASE)
    last_updated = date_match.group(1).strip() if date_match else default_date
    
    # 3. Clean main response string by stripping URL sentences and footer
    # Remove footer line
    clean_text = re.sub(r"last updated from sources:.*", "", llm_text, flags=re.IGNORECASE).strip()
    
    # Split sentences to remove the ones containing the URL
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean_text) if s.strip()]
    clean_sentences = []
    for s in sentences:
        if citation not in s and "http" not in s:
            clean_sentences.append(s)
            
    final_response = " ".join(clean_sentences).strip()
    if not final_response:
        # Fallback to stripped response text if cleaning left it empty
        final_response = clean_text
        
    return {
        "response": final_response,
        "citation": citation,
        "last_updated": last_updated,
        "is_refusal": False
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    API Chat Route:
    1. Validates and routes query (advisory, PII, out of scope, or factual).
    2. Runs hybrid RAG search if factual.
    3. Synthesizes compliance-validated response.
    """
    query = request.message.strip()
    logger.info(f"Received API Chat Query: '{query}'")
    
    # Safety Check: ensure components are loaded (lazy init on first request)
    try:
        _load_components()
    except Exception as err:
        logger.critical(f"Pipeline components failed to load: {err}")
        raise HTTPException(status_code=500, detail="Core semantic models failed to initialize.")

    # Step 1: Semantic Routing & Classification (Phase 3)
    route_result = router.route_query(query)
    
    if route_result["should_refuse"]:
        # Blocked query (PII, Advisory, or Out-of-Scope)
        return ChatResponse(
            response=route_result["refusal_message"],
            citation=route_result["citation"],
            last_updated="2026-06-28", # Default static date
            is_refusal=True
        )
        
    # Step 2: Factual Query RAG Retrieval (Phase 2)
    try:
        retrieved_chunks = retriever.retrieve(query, top_n=3)
    except Exception as e:
        logger.error(f"Retrieval error: {e}")
        # Default refusal if retrieval fails
        return ChatResponse(
            response="I am sorry, but I encountered an error while searching the source documents.",
            citation=None,
            last_updated="2026-06-28",
            is_refusal=True
        )
        
    if not retrieved_chunks:
        # Factual query but no relevant documents found in index
        return ChatResponse(
            response="I am sorry, but the target source documents do not contain information regarding this query.",
            citation=None,
            last_updated="2026-06-28",
            is_refusal=True
        )
        
    # Step 3: LLM Synthesis & Guardrail Validation (Phase 4)
    raw_llm_response = synthesis_engine.synthesize(query, retrieved_chunks)
    
    # Get defaults from the top retrieved chunk metadata
    top_chunk = retrieved_chunks[0]
    default_url = top_chunk["metadata"]["source_url"]
    default_date = top_chunk["metadata"]["last_updated"]
    
    # Step 4: Schema Formatting (Format clean response JSON)
    formatted_data = clean_factual_response(raw_llm_response, default_url, default_date)
    
    return ChatResponse(
        response=formatted_data["response"],
        citation=formatted_data["citation"],
        last_updated=formatted_data["last_updated"],
        is_refusal=formatted_data["is_refusal"]
    )

# Host static files for Frontend SPA (Subphase 6.1)
static_path = os.path.join(CURRENT_DIR, "static")
if os.path.exists(static_path):
    logger.info(f"Serving static frontend files from: {static_path}")
    app.mount("/", StaticFiles(directory=static_path, html=True), name="static")
else:
    logger.warning(f"Static directory not found at: {static_path}. Server will run as API-only.")

if __name__ == "__main__":
    import uvicorn
    # Load configuration parameters from env
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    logger.info(f"Starting server on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
