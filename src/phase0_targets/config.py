import os
import json
from typing import List, Dict, Any

# Resolve the path to schemes.json relative to this file
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMES_JSON_PATH = os.path.join(CURRENT_DIR, "schemes.json")

def load_target_schemes() -> List[Dict[str, Any]]:
    """
    Loads target schemes from schemes.json and performs basic schema validation.
    """
    if not os.path.exists(SCHEMES_JSON_PATH):
        raise FileNotFoundError(f"Schemes configuration file not found at: {SCHEMES_JSON_PATH}")
        
    with open(SCHEMES_JSON_PATH, "r", encoding="utf-8") as f:
        schemes = json.load(f)
        
    # Validate schemes schema
    required_keys = {"id", "name", "groww_url", "scheme_type", "amc"}
    for idx, scheme in enumerate(schemes):
        missing = required_keys - scheme.keys()
        if missing:
            raise ValueError(f"Scheme at index {idx} is missing required keys: {missing}")
            
        url = scheme["groww_url"]
        if not url.startswith("https://groww.in/mutual-funds/"):
            raise ValueError(f"Invalid Groww URL format at index {idx}: {url}")
            
    return schemes

# Preload schemes for ease of importing
try:
    TARGET_SCHEMES = load_target_schemes()
except Exception as e:
    TARGET_SCHEMES = []
    # Avoid crashing on import if initialization fails, but print/log
    print(f"Warning: Failed to load target schemes configuration: {e}")
