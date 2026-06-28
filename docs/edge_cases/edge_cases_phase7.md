# Edge Cases: Phase 7 (Verification & Testing Framework)

This document addresses issues related to flaky evaluation tests, network dependencies, and metric drifting within the validation and testing suites.

---

## 1. Edge Case: Flaky Tests due to LLM Non-Determinism
*   **Description:** The verification test suite checks generated responses against expected outputs. Because LLM outputs are inherently probabilistic, even with `temperature=0.0`, small syntactic changes (e.g., swapping "lock-in period" for "lock-in duration") cause exact string match tests to fail.
*   **Impact:** The CI/CD build fails repeatedly on valid releases, wasting developer time.
*   **Mitigation Strategy:**
    1.  **Avoid Exact String Matching:** Do not assert on exact text responses. Instead, assert on structural constraints:
        *   Sentence count ($\le 3$).
        *   Contains target numeric value (e.g. check for `"3 years"` using substring or regex).
        *   Contains exactly one valid URL.
    2.  **Semantic Similarity Metrics:** Use a local embedding comparison script to calculate the cosine similarity between the generated response and the golden target. Assert that similarity must be $\ge 0.85$.

---

## 2. Edge Case: External API Dependencies during CI/CD Runs
*   **Description:** The integration test suite makes live calls to the LLM API (e.g., Gemini or OpenAI) during the GitHub Actions or local test runs.
*   **Impact:** Network latency, rate limit limits, or API outages cause tests to fail, blocks deployments, and leaks API tokens if logs are not properly handled.
*   **Mitigation Strategy:**
    1.  **Mocking the LLM Layer:** Use python's `unittest.mock` to mock the API responses during standard unit tests. Ensure that testing the API connection is separated from the core logic verification.
    2.  **Recorded HTTP Interactions:** Use tools like `vcr.py` to record HTTP requests during the first successful run and play them back locally in subsequent runs, eliminating network dependencies.

---

## 3. Edge Case: Evaluation Data Stale Drift (Outdated Golden Dataset)
*   **Description:** Groww updates the expense ratio for HDFC Mid-Cap from `0.8%` to `0.9%`. The crawler successfully pulls this new value, but the test suite fails because the golden dataset expected value is still hardcoded to `0.8%`.
*   **Impact:** The test suite flags a "regression" error when the system is actually returning more accurate/up-to-date data.
*   **Mitigation Strategy:**
    1.  **Dynamic Reference Validation:** Instead of hardcoding expected values, configure the test runner to scrape the target page dynamically, extract the ground-truth value, and match it against the LLM's response.
    2.  **Separate Verification Suites:** Keep regression testing (system behavior, format constraints) separate from data consistency audits.
