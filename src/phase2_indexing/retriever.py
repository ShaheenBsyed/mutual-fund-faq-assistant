import os
import re
import json
import logging
import chromadb
from chromadb.utils import embedding_functions
from rank_bm25 import BM25Okapi
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv

# Load env vars (.env locally, Render env in production)
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Resolve directory paths
CORPUS_JSON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "corpus.json"))
DB_DIR_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "vector_db"))
COLLECTION_NAME = "mutual_funds"

# Mapping query keywords to canonical scheme names for hard metadata pre-filtering
SCHEME_KEYWORDS_MAP = {
    "mid-cap": "HDFC Mid-Cap Opportunities Fund (Direct Growth)",
    "mid cap": "HDFC Mid-Cap Opportunities Fund (Direct Growth)",
    "midcap": "HDFC Mid-Cap Opportunities Fund (Direct Growth)",
    
    "flexi": "HDFC Flexi Cap Fund / Equity Fund (Direct Growth)",
    "flexicap": "HDFC Flexi Cap Fund / Equity Fund (Direct Growth)",
    "equity": "HDFC Flexi Cap Fund / Equity Fund (Direct Growth)",
    
    "focused": "HDFC Focused 30 Fund (Direct Growth)",
    "focus": "HDFC Focused 30 Fund (Direct Growth)",
    
    "elss": "HDFC ELSS Tax Saver Fund (Direct Plan Growth)",
    "tax saver": "HDFC ELSS Tax Saver Fund (Direct Plan Growth)",
    "tax-saver": "HDFC ELSS Tax Saver Fund (Direct Plan Growth)",
    "taxsaver": "HDFC ELSS Tax Saver Fund (Direct Plan Growth)",
    
    "large cap": "HDFC Top 100 / Large Cap Fund (Direct Growth)",
    "large-cap": "HDFC Top 100 / Large Cap Fund (Direct Growth)",
    "largecap": "HDFC Top 100 / Large Cap Fund (Direct Growth)",
    "top 100": "HDFC Top 100 / Large Cap Fund (Direct Growth)",
    "top100": "HDFC Top 100 / Large Cap Fund (Direct Growth)"
}

def tokenize(text: str) -> List[str]:
    """Simple alphanumeric lowercase tokenizer."""
    return re.findall(r"\b\w+\b", text.lower())

class HybridRetriever:
    """
    Implements a Hybrid Retrieval Engine combining ChromaDB vector similarity,
    BM25 keyword retrieval, and Reciprocal Rank Fusion (RRF), complete with
    query entity mapping for metadata pre-filtering.
    """
    def __init__(self):
        # 1. Initialize persistent Chroma client & embedding function
        if not os.path.exists(DB_DIR_PATH):
            raise FileNotFoundError(f"ChromaDB persistent directory not found at: {DB_DIR_PATH}. Run Indexer first.")

        # Use the same Gemini embedding function as the indexer (text-embedding-004, 768-dim).
        # This matches the vectors already stored in the DB and avoids loading PyTorch locally.
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError("GEMINI_API_KEY environment variable is not set.")

        logger.info(f"Connecting to ChromaDB index at: {DB_DIR_PATH}")
        self.client = chromadb.PersistentClient(path=DB_DIR_PATH)
        self.embedding_fn = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
            api_key=api_key,
            model_name="models/text-embedding-004"
        )
        self.collection = self.client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=self.embedding_fn
        )
        
        # 2. Load the raw corpus dataset for BM25 mapping
        if not os.path.exists(CORPUS_JSON_PATH):
            raise FileNotFoundError(f"Cleaned corpus not found at: {CORPUS_JSON_PATH}")
            
        with open(CORPUS_JSON_PATH, "r", encoding="utf-8") as f:
            self.raw_corpus = json.load(f)
            
        logger.info(f"HybridRetriever successfully initialized with {len(self.raw_corpus)} cached chunks.")

    def detect_scheme_filter(self, query: str) -> str:
        """
        Scans query for keywords pointing to a specific mutual fund scheme
        to avoid cross-contamination.
        """
        normalized_query = query.lower()
        for kw, canonical_name in SCHEME_KEYWORDS_MAP.items():
            if kw in normalized_query:
                logger.info(f"Identified entity keyword '{kw}'. Restricting search scope to: '{canonical_name}'")
                return canonical_name
        return ""

    def retrieve(self, query: str, top_n: int = 3, rrf_k: int = 60) -> List[Dict[str, Any]]:
        """
        Executes hybrid retrieval: pre-filters by scheme name, queries vector similarity
        and BM25 keyword matching, runs Reciprocal Rank Fusion, and returns top results.
        """
        # Step 1: Detect specific fund to filter scope
        scheme_filter = self.detect_scheme_filter(query)
        
        # Step 2: Dense Cosine Similarity Search
        dense_results = []
        if scheme_filter:
            where_filter = {
                "$or": [
                    {"scheme_name": scheme_filter},
                    {"scheme_name": "General / Non-Scheme Specific"}
                ]
            }
        else:
            where_filter = None
        
        try:
            # Retrieve up to 10 candidates from vector store
            vector_res = self.collection.query(
                query_texts=[query],
                n_results=10,
                where=where_filter
            )
            
            if vector_res and vector_res["documents"] and vector_res["documents"][0]:
                docs = vector_res["documents"][0]
                metas = vector_res["metadatas"][0]
                # In Chroma, smaller distance values represent closer vectors
                dists = vector_res["distances"][0]
                
                for idx, (doc, meta, dist) in enumerate(zip(docs, metas, dists)):
                    dense_results.append({
                        "text": doc,
                        "metadata": meta,
                        "score": dist,
                        "dense_rank": idx + 1
                    })
        except Exception as e:
            logger.error(f"Error querying ChromaDB vector store: {e}")
            
        # Step 3: Filter Corpus & Fit BM25 dynamically on the matching subset
        if scheme_filter:
            filtered_corpus = [
                c for c in self.raw_corpus 
                if c["metadata"]["scheme_name"] in (scheme_filter, "General / Non-Scheme Specific")
            ]
        else:
            filtered_corpus = self.raw_corpus
            
        sparse_results = []
        if filtered_corpus:
            tokenized_corpus = [tokenize(c["text"]) for c in filtered_corpus]
            bm25 = BM25Okapi(tokenized_corpus)
            
            tokenized_query = tokenize(query)
            scores = bm25.get_scores(tokenized_query)
            
            # Pair docs with scores and sort
            scored_docs = list(zip(filtered_corpus, scores))
            # Sort by score descending
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            
            for idx, (doc, score) in enumerate(scored_docs[:10]):
                if score > 0.0:  # Ignore completely unrelated zero-score matches
                    # Clean tags mapping back to list
                    tags = doc["metadata"]["metric_tags"] if isinstance(doc["metadata"]["metric_tags"], list) else doc["metadata"].get("metric_tags_str", "").split(",")
                    sparse_results.append({
                        "text": doc["text"],
                        "metadata": {
                            "source_url": doc["metadata"]["source_url"],
                            "doc_type": doc["metadata"]["doc_type"],
                            "scheme_name": doc["metadata"]["scheme_name"],
                            "last_updated": doc["metadata"]["last_updated"],
                            "metric_tags_str": ",".join(tags)
                        },
                        "score": score,
                        "sparse_rank": idx + 1
                    })

        # Step 4: Reciprocal Rank Fusion (RRF)
        # Use chunk text as unique identifier for fusion
        fused_scores = {}
        document_registry = {}
        
        # Add Dense ranks
        for item in dense_results:
            text = item["text"]
            document_registry[text] = item["metadata"]
            fused_scores[text] = fused_scores.get(text, 0.0) + (1.0 / (rrf_k + item["dense_rank"]))
            
        # Add Sparse ranks
        for item in sparse_results:
            text = item["text"]
            # Ensure metadata matches (preferring registry update)
            if text not in document_registry:
                document_registry[text] = item["metadata"]
            fused_scores[text] = fused_scores.get(text, 0.0) + (1.0 / (rrf_k + item["sparse_rank"]))
            
        # Step 5: Sort fused documents and prepare output
        sorted_docs = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for text, score in sorted_docs[:top_n]:
            # Convert metric_tags_str back to list for clean UI/synthesis consumption
            meta = document_registry[text]
            tags_list = meta.get("metric_tags_str", "").split(",") if "metric_tags_str" in meta else []
            meta_clean = {
                "source_url": meta["source_url"],
                "doc_type": meta["doc_type"],
                "scheme_name": meta["scheme_name"],
                "last_updated": meta["last_updated"],
                "metric_tags": tags_list
            }
            results.append({
                "text": text,
                "metadata": meta_clean,
                "rrf_score": score
            })
            
        logger.info(f"Retrieval complete. Found {len(results)} merged chunks for query: '{query}'")
        return results

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    # Test script directly if run
    retriever = HybridRetriever()
    test_queries = [
        "What is the exit load of HDFC Mid Cap Fund?",
        "What is the minimum SIP amount for ELSS?",
        "Who manages the Focused 30 fund?"
    ]
    for q in test_queries:
        print(f"\nQUERY: {q}")
        res = retriever.retrieve(q, top_n=2)
        for i, doc in enumerate(res):
            print(f"[{i+1}] (Score: {doc['rrf_score']:.5f}) - {doc['metadata']['scheme_name']}")
            print(f"    Text: {doc['text']}")
