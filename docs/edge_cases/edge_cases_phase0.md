# Edge Cases: Phase 0 (Target Schemes & Groww Source Reference)

This document outlines the potential edge cases, risks, and mitigation strategies associated with defining and referencing the target mutual fund schemes and their Groww product URLs.

---

## 1. Edge Case: URL Slug Changes / Redirection
*   **Description:** The host platform (Groww) updates its URL directory structure or slug naming conventions (e.g., changing `/mutual-funds/hdfc-mid-cap-fund-direct-growth` to `/mutual-funds/hdfc-mid-cap-opportunities-direct-growth`).
*   **Impact:** The ingestion pipeline will fail with a `404 Not Found` error, resulting in stale data or complete failure of the ingestion process.
*   **Mitigation Strategy:**
    1.  **URL Resolver Layer:** Implement a verification step that checks for redirects (HTTP Status `301`/`302`).
    2.  **Canonical Verification:** Extract the canonical URL link element from the HTML head tag (`<link rel="canonical" href="...">`) to ensure it maps to the active page.
    3.  **Alerting Alert System:** If any of the 5 URLs return a non-200 code or redirect to a search/landing page, trigger an automated email or slack alert to update the reference file.

---

## 2. Edge Case: Data Discrepancies between Groww and AMC Portal
*   **Description:** Since Groww is a third-party aggregator, there might be a lag in updating key fund characteristics (e.g., expense ratio changes, new exit load policies, riskometer adjustments) compared to HDFC AMC's official factsheet.
*   **Impact:** The assistant will return out-of-date or incorrect factual details, breaching the "accuracy and compliance" constraints.
*   **Mitigation Strategy:**
    1.  **Disclaimer Enrichment:** Include a disclaimer in the web interface specifying: *"Data is fetched directly from Groww product pages. For official legal compliance, consult the latest AMC Scheme Information Document."*
    2.  **Verification Timestamp:** Expose the exact date the data was scraped in the response footer (`"Last updated from sources: <date>"`).

---

## 3. Edge Case: Regional Restrictions or Geo-blocking
*   **Description:** Groww's web servers block requests originating from certain cloud provider IP ranges (e.g., AWS, GCP) or non-Indian IP subnets where the assistant backend is deployed.
*   **Impact:** Scraper requests are blocked with HTTP `403 Forbidden` or timeouts, failing to populate the vector database.
*   **Mitigation Strategy:**
    1.  **Residential/Indian Proxies:** Route crawler requests through local Indian proxy nodes.
    2.  **Offline Cache Fallback:** Maintain a local, pre-loaded JSON snapshot of the crawled data. If live scraping fails due to geo-blocking, fall back to the offline snapshot and log a warning.
