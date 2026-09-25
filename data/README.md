# Data sources

Source documents are not committed to this repository (large files, and redistribution
terms for third-party reports are not cleared).

## UEFA Champions League Technical Report 2024/25

- Expected at: `data/raw/pdfs/UCL_Technical-Report_2025_DIGITAL.pdf`
- Publisher: UEFA
- Obtain the report from UEFA's official technical reports page and place it at the
  path above before running ingestion.

## Ingest

Once the PDF is in place:

```bash
python -m scripts.ingest_pdf
```

This extracts text, chunks it, and populates the `ucl_technical_report_2025`
ChromaDB collection under `app/chroma_db/` (also not committed — regenerate locally).
