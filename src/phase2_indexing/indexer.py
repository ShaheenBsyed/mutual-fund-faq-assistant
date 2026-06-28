import os
import json
import logging
import chromadb
from chromadb.utils import embedding_functions

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

def build_vector_index() -> int:
    """
    Loads data/processed/corpus.json, initializes ChromaDB with all-MiniLM-L6-v2 embeddings,
    and indexes the corpus.
    """
    logger.info("Initializing vector index build...")
    
    # Check if cleaned corpus exists
    if not os.path.exists(CORPUS_JSON_PATH):
        raise FileNotFoundError(f"Cleaned corpus.json not found at: {CORPUS_JSON_PATH}. Please run Phase 1 first.")
        
    with open(CORPUS_JSON_PATH, "r", encoding="utf-8") as f:
        corpus = json.load(f)
        
    if not corpus:
        raise ValueError("The corpus.json file is empty. Nothing to index.")
        
    # 1. Initialize persistent Chroma client
    os.makedirs(DB_DIR_PATH, exist_ok=True)
    logger.info(f"Connecting to persistent ChromaDB at: {DB_DIR_PATH}")
    client = chromadb.PersistentClient(path=DB_DIR_PATH)
    
    # 2. Configure embedding function
    logger.info("Initializing local SentenceTransformerEmbeddingFunction (all-MiniLM-L6-v2)...")
    # This automatically downloads and uses all-MiniLM-L6-v2 locally
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    
    # 3. Create or replace the collection to prevent duplicate accumulation
    try:
        client.delete_collection(COLLECTION_NAME)
        logger.info(f"Deleted existing collection: '{COLLECTION_NAME}'")
    except Exception:
        logger.info(f"No existing collection '{COLLECTION_NAME}' found. Creating fresh one.")
        
    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn
    )
    
    # 4. Batch add documents, metadatas, and IDs
    documents = []
    metadatas = []
    ids = []
    
    for idx, chunk in enumerate(corpus):
        documents.append(chunk["text"])
        
        # Flatten list metadata tags into a string representation if needed, 
        # but ChromaDB natively supports arrays/lists of strings in where filters for some databases,
        # however SQLite filter queries work best with simple primitives, lists, or tags.
        # We'll save metric_tags as a comma-separated string for simpler downstream filters if needed,
        # but Chroma supports query-in constraints for lists too. We'll store it as list.
        meta = {
            "source_url": chunk["metadata"]["source_url"],
            "doc_type": chunk["metadata"]["doc_type"],
            "scheme_name": chunk["metadata"]["scheme_name"],
            "last_updated": chunk["metadata"]["last_updated"],
            "metric_tags_str": ",".join(chunk["metadata"]["metric_tags"])
        }
        metadatas.append(meta)
        ids.append(f"chunk_{idx}")
        
    logger.info(f"Indexing {len(documents)} document chunks into collection '{COLLECTION_NAME}'...")
    
    # Chroma handles the embedding generation under the hood using our embedding function
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    
    # Verify index size
    count = collection.count()
    logger.info(f"Vector database indexing complete. Total indexed chunks: {count}")
    return count

if __name__ == "__main__":
    build_vector_index()
