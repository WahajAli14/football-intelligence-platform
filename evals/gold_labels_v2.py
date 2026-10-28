"""
Gold retrieval labels for the CLEANED collections (football_docs_chunked_v2,
ucl_technical_report_2025_v2 - see app/services/chunking.py's
clean_and_merge_chunks and EVAL_FINDINGS.md for why these exist: the UEFA
report was 72% single-word/page-number/caption chunks before cleaning).

This is a SEPARATE file from evals/gold_labels.py, not an edit to it -
gold_labels.py's chunk_ids only exist in the original, uncleaned
collections (kept around specifically so the frozen Phase 2A baseline
stays reproducible). Chunk boundaries shifted when cleaning merged/dropped
chunks, so every chunk_id here is different from gold_labels.py even where
the underlying fact is identical.

football_profiles mapping was mechanical and verified: cleaning merged
each document's one-line title into its first content chunk, uniformly
shifting every later chunk's index down by exactly 1
(doc_N_chunkM in the original -> doc_N_chunk(M-1) here) across all 8
documents - confirmed by inspecting the full 48-chunk v2 dump directly, not
assumed. The UEFA report side was NOT mechanical (3356 -> 1098 chunks is a
real restructuring) - every UEFA chunk_id below was re-found by searching
the v2 corpus directly for the same facts, the same way gold_labels.py's
originals were built.

See gold_labels.py's docstring for the general labeling methodology and the
football_profile/multi_context/partial_evidence/unsupported semantics -
unchanged here, just re-pointed at new chunk_ids.
"""

gold_labels_v2 = {
    # --- FOOTBALL PROFILES ---
    "Which team uses aggressive high pressing?": {
        "relevant_chunk_ids": ["doc_5_chunk1"],
    },
    "How does Arsenal build up play?": {
        "relevant_chunk_ids": ["doc_1_chunk0", "doc_1_chunk1"],
    },
    "What are Real Madrid known for in the Champions League?": {
        "relevant_chunk_ids": ["doc_2_chunk1", "doc_2_chunk2", "doc_2_chunk5"],
    },
    "How does Manchester City play possession football?": {
        "relevant_chunk_ids": ["doc_3_chunk0", "doc_3_chunk1", "doc_3_chunk2"],
    },
    "What is Barcelona's possession style?": {
        "relevant_chunk_ids": ["doc_6_chunk0", "doc_6_chunk1", "doc_6_chunk2"],
    },
    "What are PSG's attacking strengths?": {
        "relevant_chunk_ids": ["doc_4_chunk1"],
    },

    # --- UEFA REPORT ---
    "What does the UEFA report say about Arsenal's pressing?": {
        "relevant_chunk_ids": [
            "UCL_Technical-Report_2025_DIGITAL_chunk708",
            "UCL_Technical-Report_2025_DIGITAL_chunk709",
        ],
    },
    "Which team had the most shots from counter-attacks in the UEFA report?": {
        "relevant_chunk_ids": ["UCL_Technical-Report_2025_DIGITAL_chunk798"],
    },
    "What does the UEFA report say about Liverpool's pressing strategy?": {
        "relevant_chunk_ids": [
            "UCL_Technical-Report_2025_DIGITAL_chunk211",
            "UCL_Technical-Report_2025_DIGITAL_chunk212",
            "UCL_Technical-Report_2025_DIGITAL_chunk213",
            "UCL_Technical-Report_2025_DIGITAL_chunk214",
            "UCL_Technical-Report_2025_DIGITAL_chunk216",
        ],
        "notes": "still non-contiguous after cleaning (211-214 come before "
                 "216 but continue its quote) - the reading-order issue is a "
                 "PDF extraction/layout artifact, not something chunk "
                 "merging addresses or was expected to fix.",
    },
    "How does the report describe Paris Saint-Germain's defensive fundamentals?": {
        "relevant_chunk_ids": [
            "UCL_Technical-Report_2025_DIGITAL_chunk314",
            "UCL_Technical-Report_2025_DIGITAL_chunk315",
        ],
    },
    "What did Luis Enrique say about Arsenal after the match?": {
        "relevant_chunk_ids": ["UCL_Technical-Report_2025_DIGITAL_chunk708"],
    },
    "Which teams excelled in counter-pressing according to the UEFA report?": {
        "relevant_chunk_ids": ["UCL_Technical-Report_2025_DIGITAL_chunk835"],
    },

    # --- MULTI-CONTEXT ---
    "Compare how Arsenal and Manchester City press after losing the ball.": {
        "relevant_chunk_ids": ["doc_1_chunk2", "doc_3_chunk2"],
    },
    "According to the UEFA report, which team led in counter-pressing intensity and which team was most dangerous in transitions?": {
        "relevant_chunk_ids": [
            "UCL_Technical-Report_2025_DIGITAL_chunk835",
            "UCL_Technical-Report_2025_DIGITAL_chunk798",
        ],
    },
    "Compare the transition and counter-attacking threat of Real Madrid and Bayern Munich.": {
        "relevant_chunk_ids": ["doc_2_chunk1", "doc_5_chunk3"],
    },
    "What defensive weaknesses do Barcelona and Manchester City share?": {
        "relevant_chunk_ids": ["doc_6_chunk4", "doc_3_chunk4"],
    },

    # --- CROSS-SOURCE ---
    "Compare how the general football profile explains high pressing with how Liverpool applied it against Milan in the UEFA report.": {
        "relevant_chunk_ids": [
            "doc_8_chunk0", "doc_8_chunk1", "doc_8_chunk2",
            "UCL_Technical-Report_2025_DIGITAL_chunk211",
            "UCL_Technical-Report_2025_DIGITAL_chunk212",
            "UCL_Technical-Report_2025_DIGITAL_chunk213",
            "UCL_Technical-Report_2025_DIGITAL_chunk214",
            "UCL_Technical-Report_2025_DIGITAL_chunk216",
        ],
    },
    "What similarities exist between Bayern Munich's pressing style and Arsenal's pressing against Paris?": {
        "relevant_chunk_ids": [
            "doc_5_chunk1",
            "UCL_Technical-Report_2025_DIGITAL_chunk708",
            "UCL_Technical-Report_2025_DIGITAL_chunk709",
        ],
    },
    "How does Manchester City's own pressing profile relate to their counter-pressing performance in the UEFA report?": {
        "relevant_chunk_ids": [
            "doc_3_chunk2",
            "UCL_Technical-Report_2025_DIGITAL_chunk835",
        ],
    },
    "How does the general high-pressing explanation describe team coordination, and how was this reflected in Arsenal's pressing against PSG per the UEFA report?": {
        "relevant_chunk_ids": [
            "doc_8_chunk2",
            "UCL_Technical-Report_2025_DIGITAL_chunk708",
            "UCL_Technical-Report_2025_DIGITAL_chunk709",
        ],
    },

    # --- UNSUPPORTED / HALLUCINATION-RESISTANCE (no relevant evidence exists) ---
    "What does the available knowledge base say about Inter Miami's pressing strategy?": {
        "relevant_chunk_ids": [],
        "notes": "intentional - Inter Miami isn't in the corpus at all.",
    },
    "What does the available knowledge base say about Chelsea's pressing strategy?": {
        "relevant_chunk_ids": [],
        "notes": "intentional - Chelsea isn't in the corpus at all.",
    },

    # --- PARTIAL EVIDENCE (relevant evidence exists, but is insufficient) ---
    "According to the UEFA report, how many goals did Erling Haaland score in the competition?": {
        "relevant_chunk_ids": ["UCL_Technical-Report_2025_DIGITAL_chunk475"],
        "notes": "same passage as gold_labels.py's chunk810 (Haaland's goal "
                 "against Sparta Praha) - survived cleaning intact, just "
                 "renumbered.",
    },
}
