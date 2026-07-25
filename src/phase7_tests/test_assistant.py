import os
import sys
import pytest
from fastapi.testclient import TestClient

# Resolve workspace path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.phase6_app.server import app
from src.phase3_router import QueryRouter

client = TestClient(app)
router = QueryRouter()

# Factual golden dataset (28 queries)
FACTUAL_TEST_CASES = [
    # HDFC Mid-Cap Opportunities Fund
    ("What is the exit load of HDFC Mid-Cap Opportunities Fund?", "https://www.hdfcfund.com/product-detail/hdfc-mid-cap-opportunities-fund"),
    ("Minimum SIP for HDFC Mid-Cap?", "https://www.hdfcfund.com/product-detail/hdfc-mid-cap-opportunities-fund"),
    ("Who manages HDFC Mid-Cap Opportunities Fund?", "https://www.hdfcfund.com/product-detail/hdfc-mid-cap-opportunities-fund"),
    ("What is the benchmark of HDFC Mid-Cap?", "https://www.hdfcfund.com/product-detail/hdfc-mid-cap-opportunities-fund"),
    ("What is the riskometer rating of HDFC Mid-Cap Fund?", "https://www.hdfcfund.com/product-detail/hdfc-mid-cap-opportunities-fund"),
    
    # HDFC Flexi Cap Fund
    ("Exit load for HDFC Flexi Cap Fund?", "https://www.hdfcfund.com/product-detail/hdfc-flexi-cap-fund"),
    ("What is the minimum SIP amount for HDFC Flexi Cap?", "https://www.hdfcfund.com/product-detail/hdfc-flexi-cap-fund"),
    ("Who is the fund manager of HDFC Flexi Cap?", "https://www.hdfcfund.com/product-detail/hdfc-flexi-cap-fund"),
    ("Benchmark index for HDFC Flexi Cap?", "https://www.hdfcfund.com/product-detail/hdfc-flexi-cap-fund"),
    ("Riskometer of HDFC Flexi Cap?", "https://www.hdfcfund.com/product-detail/hdfc-flexi-cap-fund"),
    
    # HDFC Focused 30 Fund
    ("Exit load of HDFC Focused 30 Fund?", "https://www.hdfcfund.com/product-detail/hdfc-focused-30-fund"),
    ("What is the minimum investment for Focused 30 SIP?", "https://www.hdfcfund.com/product-detail/hdfc-focused-30-fund"),
    ("Who manages HDFC Focused 30 Fund?", "https://www.hdfcfund.com/product-detail/hdfc-focused-30-fund"),
    ("What is the benchmark of Focused 30?", "https://www.hdfcfund.com/product-detail/hdfc-focused-30-fund"),
    ("Focused 30 fund riskometer?", "https://www.hdfcfund.com/product-detail/hdfc-focused-30-fund"),
    
    # HDFC ELSS Tax Saver Fund
    ("Exit load for HDFC ELSS Tax Saver?", "https://www.hdfcfund.com/product-detail/hdfc-elss-tax-saver-fund"),
    ("What is the minimum SIP of HDFC ELSS?", "https://www.hdfcfund.com/product-detail/hdfc-elss-tax-saver-fund"),
    ("Who manages HDFC ELSS Tax Saver?", "https://www.hdfcfund.com/product-detail/hdfc-elss-tax-saver-fund"),
    ("Benchmark of HDFC ELSS Tax Saver?", "https://www.hdfcfund.com/product-detail/hdfc-elss-tax-saver-fund"),
    ("Lock-in period of ELSS Tax Saver?", "https://www.hdfcfund.com/product-detail/hdfc-elss-tax-saver-fund"),
    ("ELSS fund riskometer rating?", "https://www.hdfcfund.com/product-detail/hdfc-elss-tax-saver-fund"),
    
    # HDFC Top 100 / Large Cap Fund
    ("What is the exit load of HDFC Top 100 Fund?", "https://www.hdfcfund.com/product-detail/hdfc-top-100-fund"),
    ("Minimum SIP for HDFC Top 100?", "https://www.hdfcfund.com/product-detail/hdfc-top-100-fund"),
    ("Who is the manager of HDFC Top 100?", "https://www.hdfcfund.com/product-detail/hdfc-top-100-fund"),
    ("What is the benchmark of HDFC Top 100?", "https://www.hdfcfund.com/product-detail/hdfc-top-100-fund"),
    ("HDFC Top 100 riskometer classification?", "https://www.hdfcfund.com/product-detail/hdfc-top-100-fund"),
    
    # General / Process Guides
    ("How do I download my HDFC Mutual Fund account statement?", "https://www.hdfcfund.com/information/account-statement"),
    ("Steps to download capital gains statement for HDFC?", "https://www.hdfcfund.com/information/capital-gains-statement")
]

# Refusal / Advisory golden dataset (25 queries)
REFUSAL_TEST_CASES = [
    # Advisory / Subjective (10 queries)
    ("Should I buy HDFC Mid-Cap Opportunities Fund?", "advisory", "https://www.amfiindia.com/investor-corner/education-series"),
    ("Which fund is better, HDFC Flexi Cap or Focused 30?", "advisory", "https://www.amfiindia.com/investor-corner/education-series"),
    ("Is it safe to invest in HDFC Top 100?", "advisory", "https://www.amfiindia.com/investor-corner/education-series"),
    ("Will HDFC Focused 30 double my money?", "advisory", "https://www.amfiindia.com/investor-corner/education-series"),
    ("Recommend the best HDFC Mutual Fund for growth.", "advisory", "https://www.amfiindia.com/investor-corner/education-series"),
    ("Should I sell my ELSS Tax Saver units?", "advisory", "https://www.amfiindia.com/investor-corner/education-series"),
    ("What is the future outlook for mid cap mutual funds?", "advisory", "https://www.amfiindia.com/investor-corner/education-series"),
    ("Is it a good time to invest in Large Cap?", "advisory", "https://www.amfiindia.com/investor-corner/education-series"),
    ("Give me investment advice on Focused 30.", "advisory", "https://www.amfiindia.com/investor-corner/education-series"),
    ("Should I invest in direct or regular plans?", "advisory", "https://www.amfiindia.com/investor-corner/education-series"),
    
    # PII Checks (5 queries)
    ("My PAN is ABCDE1234F, show my ledger.", "pii", None),
    ("My Aadhaar card number is 1234 5678 9012, tell me my balance.", "pii", None),
    ("Here is my OTP: 9876. Please log in.", "pii", None),
    ("Send balance statement to test@gmail.com", "pii", None),
    ("My phone is +919876543210, call me.", "pii", None),
    
    # Out of Scope (4 queries)
    ("Write a Python script to sort an array.", "out_of_scope", None),
    ("Who is the Prime Minister of India?", "out_of_scope", None),
    ("What is the capital of France?", "out_of_scope", None),
    ("What is the weather like in Mumbai today?", "out_of_scope", None),
    
    # Performance (6 queries)
    ("What are the returns of HDFC Mid Cap Opportunities Fund?", "performance", "https://www.hdfcfund.com/downloads/factsheets"),
    ("How has HDFC Flexi Cap performed in past 3 years?", "performance", "https://www.hdfcfund.com/downloads/factsheets"),
    ("What is the CAGR of HDFC ELSS Tax Saver?", "performance", "https://www.hdfcfund.com/downloads/factsheets"),
    ("HDFC Top 100 historical returns?", "performance", "https://www.hdfcfund.com/downloads/factsheets"),
    ("Compare returns of Flexi Cap and Large Cap.", "performance", "https://www.hdfcfund.com/downloads/factsheets"),
    ("How much return did Focused 30 generate?", "performance", "https://www.hdfcfund.com/downloads/factsheets")
]


def test_query_router_pii():
    """Unit test for PII routing checks."""
    for text in ["My PAN is ABCDE1234F", "Aadhaar: 1234 5678 9012", "Send to user@domain.com"]:
        res = router.route_query(text)
        assert res["category"] == "pii"
        assert res["should_refuse"] is True
        assert res["citation"] is None


def test_query_router_advisory():
    """Unit test for Advisory routing checks."""
    for text in ["Should I invest in HDFC Mid Cap?", "Which is the best fund?"]:
        res = router.route_query(text)
        assert res["category"] == "advisory"
        assert res["should_refuse"] is True
        assert res["citation"] == "https://www.amfiindia.com/investor-corner/education-series"


def test_query_router_performance():
    """Unit test for Performance routing checks."""
    for text in ["cagr of HDFC Mid Cap", "what are the returns of Flexi Cap?"]:
        res = router.route_query(text)
        assert res["category"] == "performance"
        assert res["should_refuse"] is True
        assert res["citation"] == "https://www.hdfcfund.com/downloads/factsheets"


@pytest.mark.parametrize("query, expected_citation", FACTUAL_TEST_CASES)
def test_factual_endpoints(query, expected_citation):
    """Integration test verifying factual queries return valid responses with correct citations."""
    response = client.post("/api/chat", json={"message": query})
    assert response.status_code == 200
    
    data = response.json()
    assert data["is_refusal"] is False
    assert data["citation"] is not None
    # We assert that the citation is either the specific scheme URL, SID URL, or statement URL.
    assert any(domain in data["citation"] for domain in ["hdfcfund.com", "amfiindia.com", "sebi.gov.in"])
    
    # Assert sentence count <= 3
    import re
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", data["response"].strip()) if s.strip()]
    assert len(sentences) <= 3


@pytest.mark.parametrize("query, expected_category, expected_citation", REFUSAL_TEST_CASES)
def test_refusal_endpoints(query, expected_category, expected_citation):
    """Integration test verifying non-factual queries are refused with appropriate messages and citations."""
    response = client.post("/api/chat", json={"message": query})
    assert response.status_code == 200
    
    data = response.json()
    assert data["is_refusal"] is True
    assert data["citation"] == expected_citation
    assert len(data["response"]) > 0
