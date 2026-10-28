from typing import Any, Dict

from app.services.document_loader import DocumentLoader
from app.services.vector_store_chunked import add_documents_with_chunking
from app.config.rag import (
    DEFAULT_COLLECTION,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_STRATEGY,
)


def ingest_football_profiles(
    collection_name: str = DEFAULT_COLLECTION,
    clean_chunks: bool = False,
) -> Dict[str, Any]:
    """
    Load, chunk and store the built-in football team profiles in Chroma.
    """
    documents = DocumentLoader.from_football_docs()

    if not documents:
        raise ValueError("No football profile documents found")

    print(f"📄 Loaded {len(documents)} football profile documents")

    result = add_documents_with_chunking(
        documents,
        collection_name,
        DEFAULT_CHUNK_SIZE,
        DEFAULT_CHUNK_OVERLAP,
        DEFAULT_CHUNK_STRATEGY,
        recreate=True,
        verbose=True,
        clean_chunks=clean_chunks,
    )

    return result


if __name__ == "__main__":
    import sys
    v2 = "--v2" in sys.argv
    stats = ingest_football_profiles(
        collection_name=DEFAULT_COLLECTION + "_v2" if v2 else DEFAULT_COLLECTION,
        clean_chunks=v2,
    )

    print("\n✅ Football profiles ingestion complete")
    print(f"   Collection: {stats['collection']}")
    print(f"   Documents processed: {stats['documents_processed']}")
    print(f"   Chunks created: {stats['chunks_created']}")
    print(f"   Total chunks: {stats['total_chunks']}")
    print(f"   Status: {stats['status']}")
