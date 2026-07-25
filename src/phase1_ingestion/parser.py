import os
import json
import logging
import datetime
from bs4 import BeautifulSoup
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import config targets
try:
    from src.phase0_targets import TARGET_SCHEMES
except ImportError:
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    from src.phase0_targets import TARGET_SCHEMES

# Resolve directories
DATA_RAW_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw"))
DATA_PROCESSED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed"))
CORPUS_OUTPUT_PATH = os.path.join(DATA_PROCESSED_DIR, "corpus.json")

def clean_text(text: str) -> str:
    """Cleans excess spaces and collapses consecutive whitespace."""
    if not text:
        return ""
    # Collapse multiple whitespaces and trim
    return " ".join(text.split()).strip()

def parse_html_page(file_path: str, scheme_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parses a cached Groww HTML file and returns a list of semantic chunks with metadata.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Raw HTML file not found at: {file_path}")
        
    with open(file_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    soup = BeautifulSoup(html_content, "html.parser")
    chunks = []
    
    # 1. Scheme Title & Basic Metadata
    h1 = soup.find("h1")
    scheme_title = clean_text(h1.get_text()) if h1 else scheme_config["name"]
    
    # 2. Extract Fund Details Container
    details = {}
    details_container = soup.find(class_=lambda c: c and "fundDetailsContainer" in c)
    if details_container:
        items = details_container.find_all(class_=lambda c: c and "gap4" in c)
        for item in items:
            texts = [clean_text(t) for t in item.get_text(separator="|", strip=True).split("|") if t.strip()]
            if len(texts) >= 2:
                label = texts[0]
                val = texts[1]
                if "NAV" in label:
                    details["NAV"] = val
                    details["NAV_Date"] = label.replace("NAV:", "").strip()
                else:
                    details[label] = val
                    
    nav = details.get("NAV", "N/A")
    nav_date = details.get("NAV_Date", "N/A")
    min_sip = details.get("Min. for SIP", "N/A")
    aum = details.get("Fund size (AUM)", "N/A")
    expense_ratio = details.get("Expense ratio", "N/A")
    rating = details.get("Rating", "N/A")
    
    # 3. Extract Exit Load Section
    exit_load_value = "Nil"
    exit_section = soup.find(class_=lambda c: c and "exitLoadStampDutyTax_section" in c)
    if exit_section:
        exit_text = clean_text(exit_section.get_text(separator=" ", strip=True))
        if "exit load" in exit_text.lower():
            # e.g. "Exit load Nil" -> extract Nil
            # we will store the whole string for context
            exit_load_value = exit_text
    else:
        # Fallback to general search inside exit load container class
        container = soup.find(class_=lambda c: c and "exitLoadStampDutyTax_container" in c)
        if container:
            container_text = clean_text(container.get_text(separator=" | ", strip=True))
            parts = [p.strip() for p in container_text.split("|") if p.strip()]
            for p in parts:
                if p.lower().startswith("exit load"):
                    exit_load_value = p
                    break
                    
    # 4. Extract Benchmark
    benchmark_value = "N/A"
    bench_label = soup.find(string=lambda t: t and "benchmark" in t.lower())
    if bench_label and bench_label.parent and bench_label.parent.parent:
        text_content = clean_text(bench_label.parent.parent.get_text(separator="|", strip=True))
        parts = [p.strip() for p in text_content.split("|") if p.strip()]
        if len(parts) >= 2:
            benchmark_value = parts[1]
            
    # 5. Extract Riskometer & Lock-in from Pills
    riskometer_value = "N/A"
    lock_in_value = "None (Open-ended)"
    pills_container = soup.find(class_=lambda c: c and "pills_container" in c)
    if pills_container:
        pills = pills_container.find_all(class_=lambda c: c and "pill" in c)
        pill_texts = [clean_text(p.get_text()) for p in pills]
        for p in pill_texts:
            if "risk" in p.lower():
                riskometer_value = p
            if "lock-in" in p.lower() or "lock" in p.lower():
                lock_in_value = p
                
    # 6. Extract Fund Management/Managers
    managers_description = "N/A"
    mgmt_container = soup.find(class_=lambda c: c and "fundManagement_container" in c)
    if mgmt_container:
        managers_description = clean_text(mgmt_container.get_text(separator=" ", strip=True))
        # Remove view details label if present
        managers_description = managers_description.replace("View details", "")
        
    # 7. Extract About/Objective Section
    about_text = "N/A"
    about_container = soup.find(class_=lambda c: c and "investmentObjective_container" in c)
    if about_container:
        about_text = clean_text(about_container.get_text(separator=" ", strip=True))
        
    # --- CHUNKING LOGIC (Subphase 1.3) ---
    # We produce 5 high-quality factual context chunks per fund to cover potential FAQ categories
    
    # Chunk 1: Scheme Overview and Vital Details
    chunk_overview = (
        f"Overview of {scheme_title}: "
        f"This scheme is an Equity Mutual Fund categorized as {scheme_config['scheme_type']}. "
        f"As of {nav_date}, its Net Asset Value (NAV) is {nav}. "
        f"The scheme has a Groww rating of {rating} stars. "
        f"The Total Assets Under Management (AUM) is {aum}. "
        f"The Expense Ratio is {expense_ratio}. "
        f"The Riskometer category is classified as {riskometer_value}."
    )
    chunks.append({
        "text": clean_text(chunk_overview),
        "tags": ["nav", "rating", "aum", "fund_size", "expense_ratio", "risk", "riskometer", "overview"],
        "scheme_name": scheme_config["name"]
    })
    
    # Chunk 2: Investment Thresholds and Lock-in Period
    chunk_thresholds = (
        f"Investment criteria for {scheme_title}: "
        f"The minimum Systematic Investment Plan (SIP) amount required is {min_sip}. "
        f"The lock-in period details: {lock_in_value}."
    )
    chunks.append({
        "text": clean_text(chunk_thresholds),
        "tags": ["minimum_sip", "minimum_investment", "lock_in", "lock_in_period"],
        "scheme_name": scheme_config["name"]
    })
    
    # Chunk 3: Fees, Exit Load, and Stamp Duty details
    chunk_fees = (
        f"Fee structure and exit parameters for {scheme_title}: "
        f"The Exit Load details are: {exit_load_value}. "
        f"The Expense Ratio (management fee) is {expense_ratio}."
    )
    chunks.append({
        "text": clean_text(chunk_fees),
        "tags": ["exit_load", "exit_load_details", "expense_ratio", "fees", "stamp_duty"],
        "scheme_name": scheme_config["name"]
    })
    
    # Chunk 4: Benchmark index details
    chunk_benchmark = (
        f"Benchmark classification for {scheme_title}: "
        f"The fund is benchmarked against the {benchmark_value} benchmark index. "
        f"Its regulatory risk classification is {riskometer_value}."
    )
    chunks.append({
        "text": clean_text(chunk_benchmark),
        "tags": ["benchmark", "benchmark_index", "risk", "riskometer"],
        "scheme_name": scheme_config["name"]
    })
    
    # Chunk 5: Fund Management & Managers
    chunk_managers = (
        f"Fund Management details for {scheme_title}: {managers_description}"
    )
    chunks.append({
        "text": clean_text(chunk_managers),
        "tags": ["fund_manager", "manager", "management", "experience", "education"],
        "scheme_name": scheme_config["name"]
    })
    
    # Chunk 6: About / Investment Objective (if present)
    if about_text and about_text != "N/A":
        chunk_about = f"Objective and Details for {scheme_title}: {about_text}"
        chunks.append({
            "text": clean_text(chunk_about),
            "tags": ["about", "objective", "investment_objective"],
            "scheme_name": scheme_config["name"]
        })
        
    # Add metadata properties to every chunk (Subphase 1.4)
    today_str = datetime.date.today().isoformat()
    final_chunks = []
    for c in chunks:
        final_chunks.append({
            "text": c["text"],
            "metadata": {
                "source_url": scheme_config["groww_url"],
                "doc_type": "Groww Product Page",
                "scheme_name": scheme_config["name"],
                "last_updated": today_str,
                "metric_tags": c["tags"]
            }
        })
        
    return final_chunks

def parse_generic_html_page(file_path: str) -> List[Dict[str, Any]]:
    """
    Parses a generic cached official HTML page and returns semantic chunks.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Generic HTML file not found at: {file_path}")
        
    with open(file_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Extract source URL from meta tag
    meta_url = soup.find("meta", attrs={"name": "source-url"})
    source_url = meta_url["content"] if meta_url else "https://www.hdfcfund.com"
    
    # Determine the scheme name if it's scheme-specific, otherwise General
    scheme_name = "General / Non-Scheme Specific"
    file_lower = os.path.basename(file_path).lower()
    for scheme in TARGET_SCHEMES:
        # Match e.g. "hdfc-mid-cap-opportunities-fund" inside "hdfc-mid-cap-opportunities-fund-sid-kim.html"
        clean_scheme_id = scheme["id"].replace("-direct-growth", "").replace("-direct-plan-growth", "").replace("-fund", "")
        if clean_scheme_id in file_lower:
            scheme_name = scheme["name"]
            break
            
    today_str = datetime.date.today().isoformat()
    chunks = []
    
    # Find all divs with class content-chunk
    content_chunks = soup.find_all(class_="content-chunk")
    for chunk in content_chunks:
        text = clean_text(chunk.get_text(separator=" ", strip=True))
        tags_attr = chunk.get("data-tags", "")
        tags = [t.strip() for t in tags_attr.split(",") if t.strip()]
        
        chunks.append({
            "text": text,
            "metadata": {
                "source_url": source_url,
                "doc_type": "Official Public Page",
                "scheme_name": scheme_name,
                "last_updated": today_str,
                "metric_tags": tags
            }
        })
        
    # If no content-chunk divs were found, fall back to parsing body text
    if not chunks:
        body = soup.find("body")
        if body:
            text = clean_text(body.get_text(separator=" ", strip=True))
            chunks.append({
                "text": text,
                "metadata": {
                    "source_url": source_url,
                    "doc_type": "Official Public Page",
                    "scheme_name": scheme_name,
                    "last_updated": today_str,
                    "metric_tags": ["general", "official"]
                }
            })
            
    return chunks

def parse_all_crawled_pages() -> int:
    """
    Parses all cached HTML files (both schemes and generic pages) and outputs a single serialized corpus.json file.
    """
    os.makedirs(DATA_PROCESSED_DIR, exist_ok=True)
    all_chunks = []
    
    scheme_filenames = {f"{scheme['id']}.html" for scheme in TARGET_SCHEMES}
    
    # 1. Parse main schemes (the 5 files with specific Groww-style templates)
    for scheme in TARGET_SCHEMES:
        scheme_id = scheme["id"]
        file_path = os.path.join(DATA_RAW_DIR, f"{scheme_id}.html")
        
        logger.info(f"Parsing main scheme HTML for: {scheme['name']}")
        try:
            chunks = parse_html_page(file_path, scheme)
            all_chunks.extend(chunks)
            logger.info(f"Successfully generated {len(chunks)} chunks for {scheme['name']}")
        except Exception as e:
            logger.error(f"Error parsing scheme {scheme['name']}: {e}")
            raise e
            
    # 2. Parse all other files (the 15 generic official AMC/AMFI/SEBI pages)
    if os.path.exists(DATA_RAW_DIR):
        for filename in os.listdir(DATA_RAW_DIR):
            if filename.endswith(".html") and filename not in scheme_filenames:
                file_path = os.path.join(DATA_RAW_DIR, filename)
                logger.info(f"Parsing generic official page: {filename}")
                try:
                    chunks = parse_generic_html_page(file_path)
                    all_chunks.extend(chunks)
                    logger.info(f"Successfully generated {len(chunks)} chunks for generic file {filename}")
                except Exception as e:
                    logger.error(f"Error parsing generic file {filename}: {e}")
                    raise e
                    
    with open(CORPUS_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)
        
    logger.info(f"Ingestion pipeline complete. Serialized {len(all_chunks)} chunks to: {CORPUS_OUTPUT_PATH}")
    return len(all_chunks)

if __name__ == "__main__":
    parse_all_crawled_pages()
