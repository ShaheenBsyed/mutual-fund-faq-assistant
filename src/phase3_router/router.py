import re
import logging
from typing import Dict, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Sensitive data regular expressions
PAN_PATTERN = re.compile(r"\b[A-Za-z]{5}\d{4}[A-Za-z]\b")
AADHAAR_PATTERN = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(r"\b(?:\+91|0)?[6-9]\d{9}\b")
ACCOUNT_PATTERN = re.compile(r"\b\d{9,18}\b") # Matches standard Indian bank account numbers

# Subjective & Advisory keywords
ADVISORY_KEYWORDS = [
    "should i", "which is better", "best fund", "recommend", "predict", "forecast", "future performance",
    "will it double", "is it safe", "safe to invest", "market outlook", "buy or sell", "which fund to choose",
    "better returns", "highest returns", "how much will i earn", "guaranteed", "compare performance",
    "should i invest", "good buy", "is it good", "worth investing", "investment advice"
]

# Allowed mutual fund domain keywords
ALLOWED_DOMAIN_KEYWORDS = [
    "exit load", "expense ratio", "sip", "lumpsum", "nav", "aum", "fund size", "benchmark", "lock-in",
    "lock in", "riskometer", "very high risk", "manager", "portfolio", "hdfc", "mid cap", "large cap",
    "equity", "focused", "elss", "tax saver", "top 100", "minimum investment", "statement", "download",
    "capital gains", "tax implication"
]

class QueryRouter:
    """
    Analyzes user queries to route them into Factual, Advisory, PII, or Out of Scope categories.
    Ensures strict privacy standards and regulatory compliance.
    """
    def __init__(self):
        logger.info("QueryRouter initialized successfully.")

    def has_pii(self, query: str) -> Tuple[bool, str]:
        """
        Scans a query for sensitive personal details or explicit requests for bank details.
        """
        # 1. Regex patterns check
        if PAN_PATTERN.search(query):
            return True, "Indian PAN Number detected"
        if AADHAAR_PATTERN.search(query):
            return True, "Aadhaar Number detected"
        if EMAIL_PATTERN.search(query):
            return True, "Email Address detected"
        if PHONE_PATTERN.search(query):
            return True, "Phone Number detected"
            
        # 2. Check for explicit keywords seeking private details
        query_lower = query.lower()
        pii_keywords = ["otp", "password", "cvv", "pin", "login", "bank account", "balance in my account", "my portfolio value"]
        for kw in pii_keywords:
            if kw in query_lower:
                return True, f"PII keyword '{kw}' detected"
                
        return False, ""

    def is_advisory(self, query: str) -> bool:
        """
        Scans for expressions asking for advice, comparisons, or performance prediction.
        """
        query_lower = query.lower()
        for kw in ADVISORY_KEYWORDS:
            if kw in query_lower:
                return True
        return False

    def is_out_of_scope(self, query: str) -> bool:
        """
        Checks if the query is unrelated to the mutual fund FAQ domain.
        """
        query_lower = query.lower()
        
        # Check if the query contains at least one domain-related keyword
        for kw in ALLOWED_DOMAIN_KEYWORDS:
            if kw in query_lower:
                return False
                
        # If it contains none of the keywords and is completely general
        # (e.g. general questions like "who is president", "write python code", "capital of France")
        # We classify it as out of scope.
        return True

    def route_query(self, query: str) -> Dict[str, Any]:
        """
        Routes the user query and returns routing metadata along with potential safe refusal text.
        """
        # Step 1: Detect PII
        contains_pii, pii_reason = self.has_pii(query)
        if contains_pii:
            logger.warning(f"Query blocked by PII Guardrail: {pii_reason}")
            return {
                "category": "pii",
                "should_refuse": True,
                "reason": f"PII Guardrail Triggered: {pii_reason}",
                "refusal_message": (
                    "For your security and privacy, I do not process personal details, account numbers, "
                    "OTPs, phone numbers, or passwords. Please do not share sensitive information."
                ),
                "citation": None  # STRICT REQUIREMENT: No URLs for PII block
            }
            
        # Step 2: Detect Advisory
        if self.is_advisory(query):
            logger.info("Query routed to Refusal Engine: Advisory content detected")
            return {
                "category": "advisory",
                "should_refuse": True,
                "reason": "Advisory / Subjective Query",
                "refusal_message": (
                    "I am a facts-only mutual fund FAQ assistant and cannot provide investment advice, "
                    "opinions, or fund comparisons. To learn more, please refer to the educational guides on the "
                    "official AMFI Investor Education corner: https://www.amfiindia.com/investor-corner/education-series"
                ),
                "citation": "https://www.amfiindia.com/investor-corner/education-series"
            }
            
        # Step 3: Detect Out of Scope
        if self.is_out_of_scope(query):
            logger.info("Query routed to Refusal Engine: Out of scope")
            return {
                "category": "out_of_scope",
                "should_refuse": True,
                "reason": "Out of Domain Query",
                "refusal_message": (
                    "I am an FAQ assistant for the 5 target HDFC mutual fund schemes and can only answer factual "
                    "queries regarding those funds. For general queries, please search the Groww portal."
                ),
                "citation": None  # No URLs for general out of scope
            }
            
        # Step 4: Pass to Ingestion/Retrieval
        logger.info("Query routed to RAG Retrieval Pipeline: Factual query verified")
        return {
            "category": "factual",
            "should_refuse": False,
            "reason": "Factual / Verifiable Query",
            "refusal_message": None,
            "citation": None
        }

if __name__ == "__main__":
    # Test script directly if run
    router = QueryRouter()
    test_inputs = [
        "What is the exit load of HDFC Mid Cap?",
        "Should I invest in HDFC Large Cap fund?",
        "My email is customer@gmail.com, tell me my balance.",
        "Here is my PAN AAAPN1234F. Is it linked?",
        "What is the capital of Japan?",
        "What is the minimum SIP amount for the ELSS tax saver?"
    ]
    
    for text in test_inputs:
        print(f"\nINPUT: '{text}'")
        res = router.route_query(text)
        print(f"  Category: {res['category'].upper()}")
        print(f"  Refuse?:  {res['should_refuse']}")
        if res['should_refuse']:
            print(f"  Message:  {res['refusal_message']}")
            print(f"  Citation: {res['citation']}")
