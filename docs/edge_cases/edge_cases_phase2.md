# Edge Cases: Phase 2 (Indexing & Retrieval Engine)

This document addresses indexing errors, database failures, and retrieval inaccuracies occurring in the vector store and semantic search operations.

---

## 1. Edge Case: Scheme Cross-Contamination (Factual Mismatch)
*   **Description:** A user queries: *"What is the exit load of HDFC Large Cap?"*. The dense retriever finds the term "exit load" highly similar across all chunks and retrieves the exit load description of the *HDFC Mid-Cap* fund because it has a more semantically descriptive exit load chunk.
*   **Impact:** The assistant answers the user with details of the wrong scheme, resulting in a critical accuracy failure.
*   **Mitigation Strategy:**
    1.  **Strict Metadata Prefiltering:** Extract the specific scheme name from the user query via deterministic keyword checks (e.g., matching "large cap", "mid cap", "elss") before querying ChromaDB.
    2.  **ChromaDB Filter Query:** Execute the vector search with a hard filter argument, e.g., `where={"scheme_name": "HDFC Top 100 / Large Cap Fund"}`. This restricts the database search strictly to that fund's chunks.

---

## 2. Edge Case: Synonym and Abbreviation Mismatches
*   **Description:** The user queries using colloquial phrases or abbreviations (e.g., *"tax saver lock-in duration"*, *"min systematic investment"*) while the Groww HTML corpus uses formal terms like *"ELSS"*, *"lock-in period"*, and *"Minimum SIP"*.
*   **Impact:** Zero or low-quality semantic matches from the vector database, causing retrieval failures.
*   **Mitigation Strategy:**
    1.  **Hybrid Search:** Combine the vector search results with standard keyword indexing (`BM25`) configured with a basic thesaurus mapping (e.g., mapping "SIP" to "Systematic Investment Plan", "Tax Saver" to "ELSS").
    2.  **Query Expansion:** Use a lightweight local synonym expander or direct the classifier/LLM layer to clean and normalize financial terminology in the query before sending it to the retriever.

---

## 3. Edge Case: ChromaDB SQLite Lock issues on Windows
*   **Description:** ChromaDB uses SQLite under the hood. On Windows systems, rapid concurrent API requests or simultaneous ingestion/querying threads can lead to `sqlite3.OperationalError: database is locked`.
*   **Impact:** The API crashes or hangs when responding to client chat inputs.
*   **Mitigation Strategy:**
    1.  **Single-Threaded Ingestion Writes:** Ensure the ingestion parser script runs completely, closes its database connection handlers, and persists the index *before* starting the FastAPI service.
    2.  **Read-Only Database Access:** Open the ChromaDB client in read-only mode inside the API service to avoid SQLite lock contentions during runtime lookups.
