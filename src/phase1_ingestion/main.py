import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Resolve path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.phase1_ingestion.scraper import scrape_and_cache_schemes
from src.phase1_ingestion.parser import parse_all_crawled_pages, CORPUS_OUTPUT_PATH, DATA_RAW_DIR
from src.phase0_targets import TARGET_SCHEMES

def run_ingestion_pipeline(force_scrape: bool = False) -> str:
    """
    Coordinates Subphases 1.1 through 1.4:
    1. Downloads raw HTML data from target Groww URLs if missing or force_scrape is True (1.1).
    2. Parses HTML pages and extracts relevant details (1.2).
    3. Semantically chunks the data by metric categories (1.3).
    4. Enriches with metadata tags and serializes to data/processed/corpus.json (1.4).
    """
    logger.info("Initializing Phase 1 Ingestion Pipeline...")
    
    # Check if raw files exist
    raw_files_exist = True
    for scheme in TARGET_SCHEMES:
        file_path = os.path.join(DATA_RAW_DIR, f"{scheme['id']}.html")
        if not os.path.exists(file_path):
            raw_files_exist = False
            break
            
    # Step 1: Ingestion/Scrape raw HTML if needed
    if force_scrape or not raw_files_exist:
        logger.info("Raw HTML files missing or force scrape requested. Running web scraper...")
        scrape_and_cache_schemes()
    else:
        logger.info("Raw HTML files already cached locally. Skipping network scraper step.")
        
    # Step 2, 3, 4: Parse, Chunk, Enrich, and Serialize
    logger.info("Running parsing, chunking, and serialization pipeline...")
    num_chunks = parse_all_crawled_pages()
    
    logger.info(f"Phase 1 Ingestion Pipeline complete! Generated {num_chunks} chunks.")
    return CORPUS_OUTPUT_PATH

if __name__ == "__main__":
    # If run directly, execute the pipeline
    # Allow passing '--force' argument to trigger scraping
    force = "--force" in sys.argv
    run_ingestion_pipeline(force_scrape=force)
