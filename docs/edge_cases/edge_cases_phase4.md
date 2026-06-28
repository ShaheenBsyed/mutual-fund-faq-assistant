# Edge Cases: Phase 4 (Prompt Engineering & LLM Synthesis)

This document addresses generation anomalies, compliance failures, and structural output errors in the LLM synthesis pipeline.

---

## 1. Edge Case: Parametric Knowledge Leaks (Hallucination when Data is Missing)
*   **Description:** The user queries: *"What was HDFC Mid-Cap Fund's NAV on January 15, 2024?"*. The crawled Groww URLs do not contain daily historical NAV data, but the LLM, relying on its internal pre-trained memory, returns a made-up figure.
*   **Impact:** The system generates unverified financial data, breaching compliance.
*   **Mitigation Strategy:**
    1.  **Strict Negative Constraint:** Embed within the prompt: *"If the provided context does not explicitly mention the numerical figure or data point requested, you must answer: 'I cannot find that information in the target Groww sources.' Do not guess."*
    2.  **Verbatim Validation:** In the guardrail layer, cross-check numeric values returned in the LLM response against raw text values in the retrieved context. If a number appears in the response that is not present in the context, trigger a warning and reject the response.

---

## 2. Edge Case: Sentence Count Constraint Violations
*   **Description:** The LLM produces a detailed response consisting of 4 or 5 sentences due to the complexity of the explanation (e.g., explaining exit loads for multi-tiered withdrawal terms).
*   **Impact:** Violates the maximum 3-sentence constraint specified in the requirements.
*   **Mitigation Strategy:**
    1.  **Post-Process Sentence Truncation:** Implement a programmatic python handler using `nltk.sent_tokenize` or simple regular expressions to parse the response. If the length is $>3$, select only the first 3 sentences and append the source citation URL.
    2.  **Fallback Safe Summarizer:** If the sentence count is violated, send the response back to a local model or rules-based truncation engine to compress the text to $\le 3$ sentences.

---

## 3. Edge Case: Markdown Table Extraction and Layout Breakage
*   **Description:** The retrieved chunk contains structured tabular data (e.g., exit load tiers). The LLM attempts to re-create a Markdown table in its response, which is bulky and gets truncated, breaking the layout in the UI.
*   **Impact:** Broken UI layouts or answers that exceed readability limits.
*   **Mitigation Strategy:**
    1.  **Format Constraints:** Enforce in the prompt system rules: *"Do not generate markdown tables. Summarize tabular metrics as inline list elements or a single descriptive sentence."*
    2.  **HTML/Markdown Stripper:** Enforce validation that strips multi-line table layouts (`|` characters) from the generated output.
