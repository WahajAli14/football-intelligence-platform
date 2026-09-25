from pathlib import Path
from typing import Any, Dict

from app.services.document_loader import DocumentLoader
from app.services.vector_store_chunked import add_documents_with_chunking


PDF_PATH = "data/raw/pdfs/UCL_Technical-Report_2025_DIGITAL.pdf"
COLLECTION_NAME = "ucl_technical_report_2025"

def ingest_pdf(file_path: str=PDF_PATH, collection_name: str=COLLECTION_NAME) -> Dict[str, Any]:
    """
    Load, chunk and store pdf in chroma
    """
    # Load the PDF document
    if not Path(file_path).exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    documents = DocumentLoader.load_pdf(file_path)

    if not documents:
        raise ValueError(f"No documents found in PDF: {file_path}")

    print(f"📄 Loaded PDF: {documents['title']}")
    print(f"   Characters: {len(documents['text'])}")
    print(f"   Source: {documents['source']}")

    # Add documents to the vector store with chunking
    result = add_documents_with_chunking(
        [documents],
        collection_name,
        800,
        100,
        "fixed",
        recreate=True,
        verbose=True
    )

    return result


if __name__ == "__main__":
    stats = ingest_pdf()

    print("\n✅ PDF ingestion complete")
    print(f"   Collection: {stats['collection']}")
    print(f"   Documents processed: {stats['documents_processed']}")
    print(f"   Chunks created: {stats['chunks_created']}")
    print(f"   Total chunks: {stats['total_chunks']}")
    print(f"   Status: {stats['status']}")