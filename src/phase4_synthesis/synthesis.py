import os
import re
import logging
from typing import List, Dict, Any, Tuple
import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
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

# Compliance Blacklist Terms
BLACKLIST_TERMS = ["should", "recommend", "better", "buy", "sell", "growth potential", "outperform", "investment advice"]

# Try loading Google GenAI
GEMINI_AVAILABLE = False
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    logger.warning("google-genai package not found. Using Mock Summarizer fallback.")

class LLMSynthesisEngine:
    """
    Handles LLM prompt template generation, response synthesis, and strict output guardrails
    to ensure compliance with facts-only constraints.
    """
    def __init__(self):
        # Retrieve API key from environment variables
        self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.client = None
        
        if GEMINI_AVAILABLE and self.api_key:
            try:
                logger.info("Initializing Google GenAI client...")
                self.client = genai.Client(api_key=self.api_key)
                logger.info("GenAI client initialized successfully.")
            except Exception as e:
                logger.error(f"Error initializing GenAI client: {e}. Falling back to Mock mode.")
        else:
            logger.info("No Gemini API key found in environment. Running in Mock Summarizer mode.")

    def build_system_prompt(self, context: str) -> str:
        """
        Creates the system instructions restricting the LLM to facts-only, short responses.
        """
        return (
            "You are a facts-only mutual fund assistant for HDFC schemes. Your sole task is to answer the user's "
            "question using ONLY the provided verified context. You must strictly adhere to the following rules:\n"
            "1. Provide only factual, objective information derived from the provided context.\n"
            "2. Do not offer investment opinions, performance comparisons, market projections, or advice.\n"
            "3. Your answer must be extremely concise and limited to a maximum of 3 sentences.\n"
            "4. You must include exactly one citation link mapping to the source document URL.\n"
            "5. Do not include any external markdown or HTML links other than the exact source URL provided in the context metadata.\n"
            "6. Provide a footer in the exact format: 'Last updated from sources: <date>' using the date found in the metadata.\n"
            "\nContext:\n"
            "---\n"
            f"{context}\n"
            "---"
        )

    def validate_output(self, text: str, retrieved_chunks: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Validates LLM response against strict regulatory constraints.
        Returns (is_valid, error_reason).
        """
        if not text:
            return False, "Response is empty"
            
        # Constraint 1: Sentence Count <= 3
        # Split by punctuation followed by space
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
        if len(sentences) > 3:
            return False, f"Sentence count ({len(sentences)}) exceeds maximum limit of 3"
            
        # Constraint 2: Exactly one citation link
        urls = re.findall(r"https?://[^\s)\]]+", text)
        if len(urls) != 1:
            return False, f"Found {len(urls)} URLs in response (exactly 1 required)"
            
        # Verify that the URL matches one of our retrieved sources to avoid hallucinated links
        source_urls = {chunk["metadata"]["source_url"] for chunk in retrieved_chunks}
        response_url = urls[0].rstrip(".,;:")
        if response_url not in source_urls:
            return False, f"Response URL '{response_url}' does not match any source URLs: {source_urls}"
            
        # Constraint 3: No blacklist terms (advisory checks)
        text_lower = text.lower()
        for term in BLACKLIST_TERMS:
            # Match word boundaries to prevent false positives (e.g. "buying" vs "buy")
            pattern = rf"\b{term}\b"
            if re.search(pattern, text_lower):
                return False, f"Blacklisted term '{term}' found in response"
                
        # Constraint 4: Contains footer 'Last updated from sources:'
        if "last updated from sources:" not in text_lower:
            return False, "Required footer 'Last updated from sources: <date>' is missing"
            
        return True, ""

    def mock_synthesize(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """
        Failsafe mock generator when no API key is set. Generates compliant responses
        derived directly from RAG chunks.
        """
        logger.info("Generating response using Mock Summarizer...")
        if not retrieved_chunks:
            return (
                "I am sorry, but the target source documents do not contain information regarding this query.\n"
                "Last updated from sources: 2026-06-28"
            )
            
        # Use the highest-ranked retrieved chunk
        best_chunk = retrieved_chunks[0]
        text_content = best_chunk["text"]
        meta = best_chunk["metadata"]
        
        # Split text content into sentences and select up to 2 sentences for conciseness
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text_content.strip()) if s.strip()]
        summary = " ".join(sentences[:2])
        if not summary.endswith("."):
            summary += "."
            
        source_url = meta["source_url"]
        last_updated = meta["last_updated"]
        
        # Format a fully compliant response
        response = f"{summary} For details, refer to the source page: {source_url}\nLast updated from sources: {last_updated}"
        return response

    def synthesize(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """
        Queries Gemini API if available, else falls back to Mock Synthesize.
        Runs validation and implements a single-attempt self-correction loop.
        """
        if not retrieved_chunks:
            return (
                "I am sorry, but the target source documents do not contain information regarding this query.\n"
                "Last updated from sources: 2026-06-28"
            )
            
        # If client/key is not set, use the mock generator directly
        if not self.client:
            return self.mock_synthesize(query, retrieved_chunks)
            
        # Format RAG context blocks
        context_blocks = []
        for idx, chunk in enumerate(retrieved_chunks):
            context_blocks.append(
                f"Source URL: {chunk['metadata']['source_url']}\n"
                f"Date: {chunk['metadata']['last_updated']}\n"
                f"Content: {chunk['text']}"
            )
        context_str = "\n\n".join(context_blocks)
        
        system_prompt = self.build_system_prompt(context_str)
        
        try:
            logger.info("Sending query request to Gemini API (gemini-1.5-flash)...")
            response = self.client.models.generate_content(
                model="gemini-1.5-flash",
                contents=query,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.0
                )
            )
            
            raw_text = response.text.strip()
            
            # Validate output
            is_valid, error_reason = self.validate_output(raw_text, retrieved_chunks)
            
            if is_valid:
                logger.info("Gemini response passed all compliance guardrail checks.")
                return raw_text
                
            logger.warning(f"Guardrail failed: {error_reason}. Initiating self-correction request...")
            
            # Self-Correction prompt loop (Attempt 1)
            correction_instruction = (
                f"{system_prompt}\n\n"
                f"Your previous attempt: '{raw_text}' violated this rule: {error_reason}.\n"
                "Please rewrite the answer ensuring it satisfies all sentence count limits (<=3), "
                "contains exactly one source URL, does not contain advisory terms, and includes the footer."
            )
            
            response = self.client.models.generate_content(
                model="gemini-1.5-flash",
                contents=query,
                config=types.GenerateContentConfig(
                    system_instruction=correction_instruction,
                    temperature=0.0
                )
            )
            
            corrected_text = response.text.strip()
            is_valid, error_reason = self.validate_output(corrected_text, retrieved_chunks)
            
            if is_valid:
                logger.info("Corrected response passed all compliance guardrail checks.")
                return corrected_text
                
            logger.error(f"Self-correction failed: {error_reason}. Falling back to safe mock generator.")
            return self.mock_synthesize(query, retrieved_chunks)
            
        except Exception as e:
            logger.error(f"Exception during LLM generation: {e}. Falling back to safe mock generator.")
            return self.mock_synthesize(query, retrieved_chunks)

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    # Test script directly if run
    # Mocking retrieved chunks for testing
    mock_chunks = [{
        "text": (
            "HDFC Mid Cap Fund Direct Growth is an Equity Mutual Fund categorized as Mid Cap. "
            "As of 25 Jun '26, its Net Asset Value (NAV) is ₹226.92. "
            "The scheme has a Groww rating of 5 stars. The Expense Ratio is 0.75%."
        ),
        "metadata": {
            "source_url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
            "doc_type": "Groww Product Page",
            "scheme_name": "HDFC Mid-Cap Opportunities Fund (Direct Growth)",
            "last_updated": "2026-06-28",
            "metric_tags": ["nav", "rating", "expense_ratio"]
        }
    }]
    
    engine = LLMSynthesisEngine()
    print("=== TESTING MOCK SYNTHESIS ===")
    answer = engine.synthesize("What is HDFC Mid Cap's NAV?", mock_chunks)
    print(answer)
    
    print("\n=== TESTING GUARDRAIL VALIDATION ===")
    # Valid output
    valid_text = (
        "Overview of HDFC Mid Cap Fund: Net Asset Value (NAV) is ₹226.92 as of June 25, 2026. "
        "Source: https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth\n"
        "Last updated from sources: 2026-06-28"
    )
    is_v, err = engine.validate_output(valid_text, mock_chunks)
    print(f"Valid Text is valid? {is_v} (Error: {err})")
    
    # Invalid: Too many sentences
    invalid_sentences = (
        "This is sentence one. This is sentence two. This is sentence three. This is sentence four. "
        "Source: https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth\n"
        "Last updated from sources: 2026-06-28"
    )
    is_v, err = engine.validate_output(invalid_sentences, mock_chunks)
    print(f"Invalid Sentences is valid? {is_v} (Error: {err})")
    
    # Invalid: Blacklist terms
    invalid_blacklist = (
        "We recommend this fund. The exit load is Nil. "
        "Source: https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth\n"
        "Last updated from sources: 2026-06-28"
    )
    is_v, err = engine.validate_output(invalid_blacklist, mock_chunks)
    print(f"Invalid Blacklist is valid? {is_v} (Error: {err})")
