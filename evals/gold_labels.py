"""
Gold retrieval labels for the Phase 1 evaluation dataset (evals/questions.py),
per PROJECT_PLAN.md Phase 2A.

Each entry maps a question's user_input to the chunk_ids that are actually
relevant to its reference answer. These are independent of the retrieval
system - built by reading the raw chunk dumps directly (ChromaDB's .get(),
not .query()), so labeling a chunk "relevant" never depends on whether
retrieval happened to rank it highly. Using retrieval output to build its
own ground truth would validate retrieval against itself.

A chunk is labeled relevant only if it's actually needed to support the
question's reference answer - not merely on-topic. "notes" records any
non-obvious judgment call so a reviewer can check it without redoing the
search.

Empty relevant_chunk_ids lists appear on the two "unsupported" questions
(Inter Miami, Chelsea) - those entities genuinely don't exist in the corpus,
so "no relevant chunk" is the correct label, and Recall@k is undefined (0/0)
for them - exclude from Recall/Precision/MRR/nDCG aggregates, same as
Context Precision's documented limitation on this category.

Haaland is deliberately NOT in "unsupported" - it's its own category,
"partial_evidence": the corpus does contain one relevant chunk (a specific
goal mention), just not enough to answer the specific question asked (a
cumulative tally). Its gold set is non-empty and should be included in
deterministic IR metrics like any other question - only the two truly
empty-evidence "unsupported" questions are excluded.
"""

gold_labels = {
    # --- FOOTBALL PROFILES ---
    "Which team uses aggressive high pressing?": {
        "relevant_chunk_ids": ["doc_5_chunk2"],
    },
    "How does Arsenal build up play?": {
        "relevant_chunk_ids": ["doc_1_chunk1", "doc_1_chunk2"],
        "notes": "chunk2 is the direct continuation of chunk1's sentence "
                 "('...into inverted positions'), split by chunk_size.",
    },
    "What are Real Madrid known for in the Champions League?": {
        "relevant_chunk_ids": ["doc_2_chunk2", "doc_2_chunk3", "doc_2_chunk6"],
    },
    "How does Manchester City play possession football?": {
        "relevant_chunk_ids": ["doc_3_chunk1", "doc_3_chunk2", "doc_3_chunk3"],
        "notes": "chunk1=positional play/patient buildup/controlling territory, "
                 "chunk2=overloads in midfield, chunk3=high defensive line.",
    },
    "What is Barcelona's possession style?": {
        "relevant_chunk_ids": ["doc_6_chunk1", "doc_6_chunk2", "doc_6_chunk3"],
        "notes": "chunk1=technical midfield control/positional rotations/short "
                 "passing, chunk2=ball retention, chunk3=central combinations.",
    },
    "What are PSG's attacking strengths?": {
        "relevant_chunk_ids": ["doc_4_chunk2"],
        "notes": "single chunk is a near-verbatim match for the whole reference.",
    },

    # --- UEFA REPORT ---
    "What does the UEFA report say about Arsenal's pressing?": {
        "relevant_chunk_ids": [
            "UCL_Technical-Report_2025_DIGITAL_chunk1731",
            "UCL_Technical-Report_2025_DIGITAL_chunk1732",
        ],
    },
    "Which team had the most shots from counter-attacks in the UEFA report?": {
        "relevant_chunk_ids": ["UCL_Technical-Report_2025_DIGITAL_chunk2029"],
    },
    "What does the UEFA report say about Liverpool's pressing strategy?": {
        "relevant_chunk_ids": [
            "UCL_Technical-Report_2025_DIGITAL_chunk412",
            "UCL_Technical-Report_2025_DIGITAL_chunk413",
            "UCL_Technical-Report_2025_DIGITAL_chunk414",
            "UCL_Technical-Report_2025_DIGITAL_chunk415",
            "UCL_Technical-Report_2025_DIGITAL_chunk417",
        ],
        "notes": "NOT contiguous - chunk_index 412-415 come BEFORE 417 in the "
                 "corpus but logically continue 417's quote ('...he said: "
                 "Liverpool [had a clear idea to press high...]'). The PDF "
                 "interleaves a sidebar/pull-quote with the main paragraph, so "
                 "pdftotext's extraction order doesn't match reading order for "
                 "this passage. No contiguous chunk range can fully capture it "
                 "- worth keeping in mind for Phase 2B chunking/retrieval work.",
    },
    "How does the report describe Paris Saint-Germain's defensive fundamentals?": {
        "relevant_chunk_ids": [
            "UCL_Technical-Report_2025_DIGITAL_chunk550",
            "UCL_Technical-Report_2025_DIGITAL_chunk551",
        ],
    },
    "What did Luis Enrique say about Arsenal after the match?": {
        "relevant_chunk_ids": ["UCL_Technical-Report_2025_DIGITAL_chunk1731"],
        "notes": "the full quote is self-contained in this one chunk.",
    },
    "Which teams excelled in counter-pressing according to the UEFA report?": {
        "relevant_chunk_ids": ["UCL_Technical-Report_2025_DIGITAL_chunk2189"],
    },

    # --- MULTI-CONTEXT ---
    "Compare how Arsenal and Manchester City press after losing the ball.": {
        "relevant_chunk_ids": ["doc_1_chunk3", "doc_3_chunk3"],
    },
    "According to the UEFA report, which team led in counter-pressing intensity and which team was most dangerous in transitions?": {
        "relevant_chunk_ids": [
            "UCL_Technical-Report_2025_DIGITAL_chunk2189",
            "UCL_Technical-Report_2025_DIGITAL_chunk2029",
        ],
        "notes": "same two-chunk-comparison shape as the football_profiles "
                 "multi_context questions - one chunk per team/fact, confirming "
                 "the Context Precision limitation (PROJECT_PLAN.md Phase 1 "
                 "§4.3) isn't specific to the football_profiles corpus.",
    },
    "Compare the transition and counter-attacking threat of Real Madrid and Bayern Munich.": {
        "relevant_chunk_ids": ["doc_2_chunk2", "doc_5_chunk4"],
    },
    "What defensive weaknesses do Barcelona and Manchester City share?": {
        "relevant_chunk_ids": ["doc_6_chunk5", "doc_3_chunk5"],
    },

    # --- CROSS-SOURCE ---
    "Compare how the general football profile explains high pressing with how Liverpool applied it against Milan in the UEFA report.": {
        "relevant_chunk_ids": [
            "doc_8_chunk1", "doc_8_chunk2", "doc_8_chunk3",
            "UCL_Technical-Report_2025_DIGITAL_chunk412",
            "UCL_Technical-Report_2025_DIGITAL_chunk413",
            "UCL_Technical-Report_2025_DIGITAL_chunk414",
            "UCL_Technical-Report_2025_DIGITAL_chunk415",
            "UCL_Technical-Report_2025_DIGITAL_chunk417",
        ],
    },
    "What similarities exist between Bayern Munich's pressing style and Arsenal's pressing against Paris?": {
        "relevant_chunk_ids": [
            "doc_5_chunk2",
            "UCL_Technical-Report_2025_DIGITAL_chunk1731",
            "UCL_Technical-Report_2025_DIGITAL_chunk1732",
        ],
    },
    "How does Manchester City's own pressing profile relate to their counter-pressing performance in the UEFA report?": {
        "relevant_chunk_ids": [
            "doc_3_chunk3",
            "UCL_Technical-Report_2025_DIGITAL_chunk2189",
        ],
    },
    "How does the general high-pressing explanation describe team coordination, and how was this reflected in Arsenal's pressing against PSG per the UEFA report?": {
        "relevant_chunk_ids": [
            "doc_8_chunk3",
            "UCL_Technical-Report_2025_DIGITAL_chunk1731",
            "UCL_Technical-Report_2025_DIGITAL_chunk1732",
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
        "relevant_chunk_ids": ["UCL_Technical-Report_2025_DIGITAL_chunk810"],
        "notes": "Deliberately not in the 'unsupported' category - the report "
                 "DOES mention one specific Haaland goal (\"Erling Haaland's "
                 "effort against Sparta Praha, ranked eighth\" on a "
                 "most-eye-catching-goals list), just not a total goal tally "
                 "for the competition, which is what the question actually "
                 "asks. questions.py's reference and category were updated to "
                 "match ('partial_evidence' category, reference now describes "
                 "the goal mention and the missing tally explicitly) rather "
                 "than claiming no information exists at all.",
    },
}
