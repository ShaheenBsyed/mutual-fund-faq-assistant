# Edge Cases: Phase 6 (Minimalist Web Interface & API Layer)

This document discusses UI responsiveness bugs, security vulnerabilities, and API failures in the application frontend and gateway layer.

---

## 1. Edge Case: Cross-Site Scripting (XSS) via LLM Response Injection
*   **Description:** An attacker submits a query containing specialized markdown or HTML formatting. If the LLM generates or echoes these formatting structures and the frontend markdown library renders them as raw HTML, arbitrary JavaScript can run in the user's browser.
*   **Impact:** User session hijacking, defacement of the UI, or security warnings from modern browser sandbox engines.
*   **Mitigation Strategy:**
    1.  **Sanitization Library:** Use a library like `DOMPurify` (for JS clients) or python's `html.escape` before outputting content to the DOM.
    2.  **HTML-Safe Markdown Parser:** Configure the markdown rendering engine to escape raw HTML tags (e.g. disabling `dangerouslySetInnerHTML` in React or using secure markdown parsers in vanilla JS).

---

## 2. Edge Case: Rate Limiting & Denial of Service (DoS)
*   **Description:** A user rapidly submits API requests (manually or via a bot script) or sends extremely long queries (>10,000 characters) to the `/api/chat` endpoint.
*   **Impact:** Fast API resources are exhausted, vector lookup latency spikes, and LLM token usage costs balloon, leading to service downtime.
*   **Mitigation Strategy:**
    1.  **Backend Input Validation:** Set a strict character limit constraint (e.g., maximum 500 characters) on the `message` string input in FastAPI using Pydantic. Reject larger inputs with HTTP `422 Unprocessable Entity`.
    2.  **Rate Limiter Middleware:** Integrate `slowapi` or standard Redis-based rate limiting on the `/api/chat` route, restricting each user (by IP) to 5 requests per minute.
    3.  **UI Character Count:** Render a real-time character tracker next to the chat text input and disable the send button if the threshold is crossed.

---

## 3. Edge Case: High Latency / LLM Gateway Timeout
*   **Description:** The backend LLM provider (e.g., OpenAI or Google Gemini APIs) experiences high traffic, causing API responses to take longer than the HTTP timeout threshold (e.g. >10 seconds).
*   **Impact:** The client browser receives a `504 Gateway Timeout` or the frontend loader spins infinitely without showing a response.
*   **Mitigation Strategy:**
    1.  **UI State Handling:** Display a progress skeleton / loading indicator that times out after 10 seconds, replacing it with a helpful retry warning: *"We are experiencing high traffic. Please try submitting your question again."*
    2.  **Retry & Fallback Logic:** Configure backend request clients with a max timeout of 8 seconds and a retry counter of 1. If both attempts fail, return a clean, cached refusal or static response to the client rather than breaking.
