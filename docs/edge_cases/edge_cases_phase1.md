# Edge Cases: Phase 1 (Corpus Definition & Data Ingestion Pipeline)

This document details the edge cases, parsing failures, and ingestion anomalies related to scraping and chunking content from the 5 Groww URLs.

---

## 1. Edge Case: Anti-Scraping Shields and CAPTCHAs
*   **Description:** Groww uses Cloudflare or other Web Application Firewalls (WAF) to detect and block automated scraping scripts, throwing a `403 Forbidden` or challenging the request with a CAPTCHA.
*   **Impact:** The ingestion pipeline cannot retrieve the latest HTML files, leading to a failure to update the index.
*   **Mitigation Strategy:**
    1.  **Request Decoration:** Use realistic `User-Agent` headers (mimicking modern browsers), keep-alive headers, and accept-language headers.
    2.  **Scrape Scheduling:** Run the scraper once per day (or during low-traffic off-market hours) and cache the raw HTML files locally. Do not scrape on-demand on every user request.
    3.  **Local Static Snapshot:** Provide a seed folder containing pre-downloaded HTML files so that the project can start instantly and run entirely offline if needed.

---

## 2. Edge Case: React/SPA Dynamic Content Loading
*   **Description:** The page's key metrics (like Expense Ratio, Exit Load, or Assets Under Management) are not embedded in the initial raw HTML response but are loaded asynchronously via client-side API requests or client-side hydration.
*   **Impact:** Naive scrapers (like basic `urllib` or `requests` fetches) will retrieve an empty layout container or a template page without actual numbers.
*   **Mitigation Strategy:**
    1.  **Direct API Access:** Inspect browser network traffic to locate the public JSON endpoint used by Groww to load fund data and query it directly, which is faster and cleaner than parsing HTML.
    2.  **Playwright/Selenium Headless Browser:** If API endpoints are authenticated/protected, use a headless browser wrapper to wait for the DOM to fully load before extracting the text content.

---

## 3. Edge Case: DOM Structure Drift
*   **Description:** Groww updates its frontend CSS classes, Tailwind utility classes, or DOM layout tags (e.g., nesting expense ratio under a different div tag or class).
*   **Impact:** The parser script returns null or extracts wrong values (e.g., grabbing "AUM" value instead of "Expense Ratio").
*   **Mitigation Strategy:**
    1.  **Schema Validation:** Enforce strict validation constraints on the parsed output (e.g., checking that the expense ratio is a string containing `%` and is greater than `0.0%` but less than `5.0%`).
    2.  **Semantic Chunking Fallback:** Instead of extracting specific values using brittle CSS class selectors, parse the entire text content of the page sections, chunking it structurally, and let the semantic retrieval query it.

---

## 4. Edge Case: Special Character Encodings & Formatting Anomalies
*   **Description:** Numerical metrics might contain non-breaking spaces (`&nbsp;` or `\xa0`), custom currency markers (like ₹), or formatting differences (e.g., `-` representing zero exit load).
*   **Impact:** Python scripts fail to parse text into numbers (e.g., throwing a `ValueError` when attempting to cast `1.2%` to a float or handling empty fields).
*   **Mitigation Strategy:**
    1.  **Cleaners:** Implement regular expression cleaners to strip out currency symbols, commas, percent signs, and whitespace characters before storing metrics in metadata.
    2.  **Hyphen Handling:** Map null/hyphen characters (`-`, `Nil`, `N/A`) strictly to standard defaults (e.g., `0.0%` or `"None"` depending on context).
