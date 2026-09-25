"""Vector Store with Chunking - Add chunked documents to ChromaDB"""
import json
from datetime import datetime
from pathlib import Path
import logging
from typing import List, Dict, Any, Optional

from app.db.chroma_client import get_chroma_client, get_or_create_collection
from app.services.chunking import DocumentChunker
from app.services.rag_service import retrieve_similar_documents
from app.services.document_loader import DocumentLoader


__all__ = ["add_documents_with_chunking", "compare_collections", "get_collection_stats", "append_run_result"]

def get_collection_stats(collection_name: str) -> Dict[str, Any]:
    """
    Get statistics for a ChromaDB collection.

    Args:
        collection_name: Name of the collection

    Returns:
        Dictionary containing collection statistics
    """
    chroma_client = get_chroma_client()
    try:
        collection = get_or_create_collection(chroma_client, collection_name)
        return {
            "name": collection_name,
            "count": collection.count(),
        }
    except Exception as e:
        logging.error(f"Error getting collection stats for {collection_name}: {e}")
        return {
            "name": collection_name,
            "count": 0,
            "error": str(e),
        }
    

def add_documents_with_chunking(
    documents: List[Dict[str, Any]],
    collection_name: str,
    chunk_size: int = 400,
    chunk_overlap: int = 50,
    strategy: str = "paragraph",
    recreate: bool = False,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Add documents to a ChromaDB collection with chunking.

    Args:
        documents: List of documents, each as a dictionary with 'text' and optional 'metadata'.
        collection_name: Name of the ChromaDB collection.
        chunk_size: Target characters per chunk.
        chunk_overlap: Characters to overlap between chunks.
        strategy: Chunking strategy ("fixed", "paragraph", or "semantic").
        recreate: If True, recreate the collection (delete existing).
        verbose: If True, print progress messages.

    Returns:
        Dictionary with the number of chunks added and any errors encountered.
    """
    required_fields = {"id", "title", "text"}
    for i,doc in enumerate(documents):
        missing = required_fields - doc.keys()
        if missing:
            raise ValueError(f"Document at index {i} is missing required fields: {missing}")
        
    if verbose:
        print(f"📂 Processing {len(documents)} documents with chunking strategy '{strategy}'...")
        print(f"   Chunk size: {chunk_size}, Overlap: {chunk_overlap}, Strategy: {strategy}")

    # Connect to ChromaDB
    client = get_chroma_client()

    # Delete existing collection if explicitly requested
    if recreate:
        try:
            client.delete_collection(collection_name)
            if verbose:
                print(f"🗑️  Deleted existing collection '{collection_name}'")
        except Exception as e:
            logging.error(f"Error deleting collection '{collection_name}': {e}")
            if verbose:
                print(f"ℹ️ No existing collection to delete")
    
    collection = get_or_create_collection(client, collection_name)

    if collection.count() > 0 and not recreate:
        if verbose:
            print(f"⚠️  Collection '{collection_name}' already exists and contains {collection.count()} items.")
            print(f"   Use 'recreate=True' to overwrite.")
        return {
            "collection": collection_name,
            "documents_processed": len(documents),
            "chunks_created": 0,
            "total_chunks": collection.count(),
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "strategy": strategy,
            "status": "skipped_existing"
        }
    
    chunker = DocumentChunker(chunk_size=chunk_size, overlap=chunk_overlap, strategy=strategy)
    chunked_docs = chunker.chunk_documents(documents)

    if not chunked_docs:
        if verbose:
            print("❌ No chunks created")
        return {
            "collection": collection_name,
            "documents_processed": len(documents),
            "chunks_created": 0,
            "total_chunks": collection.count(),
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "strategy": strategy,
            
    "status": "no_chunks"
        }
    
    if verbose: 
        print(f"📄 Created {len(chunked_docs)} chunks from {len(documents)} documents")
    
    # Prepare for ChromaDB
    ids = []
    texts=[]
    metadatas=[]

    for doc in chunked_docs:
        ids.append(doc["id"])
        texts.append(doc["text"])
        metadatas.append({
            "title": doc.get("title", ""),
            "parent_id": doc.get("parent_id", "unknown"),
            "chunk_index": doc.get("chunk_index", 0),
            "chunk_start": doc.get("char_start", 0),
            "chunk_end": doc.get("char_end", 0),
            "source": doc.get("source", "unknown")
        })

    collection.add(
        ids=ids,
        documents=texts,
        metadatas=metadatas
    )
    
    if verbose:
        print(f"✅ Added {len(chunked_docs)} chunks to collection '{collection_name}'")
        print(f"📊 Total chunks in collection: {collection.count()}")
    
    return {
        "collection": collection_name,
        "documents_processed": len(documents),
        "chunks_created": len(chunked_docs),
        "total_chunks": collection.count(),
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "strategy": strategy,
        "status": "success"
    }


def compare_collections(
    query: str,
    n_results: int=3,
    original_collection: str = "football_docs",
    chunked_collection: str = "football_docs_chunked"
) -> Dict[str, Any]:
    """
    Compare search results between the original and chunked collections.

    Args:
        query: The search query string.
        n_results: Number of top results to retrieve from each collection.
        original_collection: Name of the original collection.
        chunked_collection: Name of the chunked collection.
    """
    results = {
        "query": query,
        "original": [],
        "chunked": []
    }

    print("=" * 60)
    print(f"🔍 Query: {query}")
    print("=" * 60)

    print(f"\n:📂 ORIGINAL COLLECTION ({original_collection}):")
    try:
        original_results = retrieve_similar_documents(query, original_collection, n_results)
        for i,doc in enumerate(original_results):
            results["original"].append({
                "rank":i,
                "title": doc['metadata'].get('title', 'Unknown'),
                "score": doc.get('similarity_score', 0),
                "preview": doc['document'][:80]
            })
            print(f"  {i}. {doc['metadata'].get('title', 'Unknown')}")
            print(f"     Score: {doc.get('similarity_score', 0):.4f}")
            print(f"     Preview: {doc['document'][:80]}...")
    except Exception as e:
        print(f"  Error: {e}")
        results["original_error"] = str(e)

    print(f"\n:📂 CHUNKED COLLECTION ({chunked_collection}):")
    try:
        chunked_results = retrieve_similar_documents(query, chunked_collection, n_results)
        for i,doc in enumerate(chunked_results):
            title = doc['metadata'].get('title', 'Unknown')
            parent = doc['metadata'].get('parent_id', 'unknown')
            results["chunked"].append({
                "rank":i,
                "title": title,
                "parent": parent,
                "score": doc.get('similarity_score', 0),
                "preview": doc['document'][:80]
            })
            print(f"  {i}. {title} (from {parent})")
            print(f"     Score: {doc.get('similarity_score', 0):.4f}")
            print(f"     Preview: {doc['document'][:80]}...")
    except Exception as e:
        print(f"  Error: {e}")
        results["chunked_error"] = str(e)
    
    return results


def append_run_result(
    run_data: Dict[str, Any],
    file_path: str = "logs/chunking_runs.jsonl"
) -> None:
    """
    Append one chunking/retrieval experiment result to a JSONL file.

    Each line in the file is one complete run.
    """

    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(run_data, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("🏃 CHUNKING PIPELINE")
    print("=" * 60)

    query = sys.argv[1] if len(sys.argv) > 1 else "Which team uses high pressing?"
    strategy = sys.argv[2] if len(sys.argv) > 2 else "paragraph"
    chunk_size = int(sys.argv[3]) if len(sys.argv) > 3 else 400
    chunk_overlap = int(sys.argv[4]) if len(sys.argv) > 4 else 50

    print(f"\n⚙️ Runtime settings:")
    print(f"   Query: {query}")
    print(f"   Strategy: {strategy}")
    print(f"   Chunk size: {chunk_size}")
    print(f"   Chunk overlap: {chunk_overlap}")

    docs = DocumentLoader.from_football_docs()
    print(f"\n📚 Loaded {len(docs)} documents")

    print("\n🔄 Adding documents with chunking...")

    result = add_documents_with_chunking(
        documents=docs,
        collection_name="football_docs_chunked",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        strategy=strategy,
        recreate=True,
        verbose=True
    )

    print(f"\n✅ Done!")
    print(f"   Collection: {result['collection']}")
    print(f"   Chunks created: {result['chunks_created']}")
    print(f"   Total chunks: {result['total_chunks']}")
    print(f"   Status: {result['status']}")

    print("\n" + "=" * 60)
    print("📊 COMPARISON: ORIGINAL vs CHUNKED")
    print("=" * 60)

    compare_collection = compare_collections(query=query)
    run_data = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "query": query,
        "strategy": strategy,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "collection": result["collection"],
        "documents_processed": result["documents_processed"],
        "chunks_created": result["chunks_created"],
        "total_chunks": result["total_chunks"],
        "status": result["status"],
        "comparison": compare_collection,
    }

    append_run_result(run_data)

    print("\n📝 Run result appended to logs/chunking_runs.jsonl")
