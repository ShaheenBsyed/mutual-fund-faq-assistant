import os
import time
import logging
import requests
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import targets from phase0
try:
    from src.phase0_targets import TARGET_SCHEMES
except ImportError:
    # Fallback in case of module resolution issues
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    from src.phase0_targets import TARGET_SCHEMES

# Target output directory
DATA_RAW_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw"))

# Headers to mimic a real desktop browser and avoid basic user-agent blocks
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0"
}

def scrape_and_cache_schemes(schemes: List[Dict[str, Any]] = TARGET_SCHEMES) -> List[str]:
    """
    Downloads raw HTML content from target Groww URLs and caches them locally.
    Raises RuntimeError if a URL fails to load.
    """
    os.makedirs(DATA_RAW_DIR, exist_ok=True)
    cached_paths = []
    
    for scheme in schemes:
        scheme_id = scheme["id"]
        url = scheme["groww_url"]
        name = scheme["name"]
        
        logger.info(f"Starting crawl for: {name}")
        logger.info(f"Target URL: {url}")
        
        output_file_path = os.path.join(DATA_RAW_DIR, f"{scheme_id}.html")
        
        try:
            # Adding timeout to prevent hanging, and using browser headers
            response = requests.get(url, headers=HEADERS, timeout=15)
            
            # Raise error on bad status code if cache does not exist
            if response.status_code != 200:
                if os.path.exists(output_file_path):
                    logger.warning(f"Failed to fetch {name} (HTTP {response.status_code}). Using existing local cache.")
                    cached_paths.append(output_file_path)
                    continue
                else:
                    logger.error(f"Failed to fetch {name}. HTTP Status Code: {response.status_code}")
                    raise RuntimeError(
                        f"Failed to download {name} from {url}. Status Code: {response.status_code}"
                    )
                
            html_content = response.text
            
            # Validate that the page has some content and is not empty/placeholder
            if not html_content or len(html_content.strip()) < 1000:
                if os.path.exists(output_file_path):
                    logger.warning(f"Fetched content for {name} is empty/invalid. Using existing local cache.")
                    cached_paths.append(output_file_path)
                    continue
                else:
                    raise RuntimeError(
                        f"Retrieved content for {name} is empty or too small: {len(html_content)} bytes"
                    )
                
            # Write out to raw data cache file
            with open(output_file_path, "w", encoding="utf-8") as f:
                f.write(html_content)
                
            logger.info(f"Successfully cached raw page to: {output_file_path} ({len(html_content)} characters)")
            cached_paths.append(output_file_path)
            
            # Simple rate limiting delay between network hits
            time.sleep(2)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error occurred while fetching {name}: {e}")
            raise RuntimeError(f"Network error fetching {url}: {e}") from e
            
    logger.info("Scraping and caching pipeline completed successfully.")
    return cached_paths

if __name__ == "__main__":
    scrape_and_cache_schemes()
