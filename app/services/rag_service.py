
from app.config.source import get_source_config
from app.db.chroma_client import get_chroma_client, get_or_create_collection
from app.config.rag import DEFAULT_COLLECTION, DEFAULT_N_RESULTS

def retrieve_similar_documents(query: str, collection_name:str=DEFAULT_COLLECTION, n_results:int = DEFAULT_N_RESULTS):
    """
        Retrieve similar documents from ChromaDB based on a query.
        Returns a list of documents with their metadata.
    """
    client = get_chroma_client()
    collection = get_or_create_collection(client, collection_name)

    #Query the collection for similar documents
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        include=["documents", "metadatas", "distances"]
    )
    # pdb.set_trace()  # Debugging breakpoint to inspect results


    #for formating the retrieved results
    retrieved_docs = []

    if results["documents"] and len(results["documents"][0]) > 0:
        for i, (doc, meta, dist) in enumerate(
            zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            ),
            start=1
        ):
            retrieved_docs.append({
                "document": doc,
                "metadata": meta,
                "similarity_score": round(1 / (1 + dist), 4),
                "rank": i
            })
            

    return retrieved_docs


def search_accross_sources(
    query: str, 
    source_ids: list[str], 
    n_results: int = DEFAULT_N_RESULTS
) -> list[dict]:
    """
        Search across multiple sources and return results.
    """
    all_results = []
    
    for source_id in source_ids:
        source_config = get_source_config(source_id)
        collection_name = source_config["collection"]
        
        source_results = retrieve_similar_documents(
            query,
            collection_name,
            n_results
        )
        for result in source_results:
            metadata = result.setdefault("metadata", {})
            metadata["source_id"] = source_id
            metadata["source_title"] = source_config["title"]

        all_results.extend(source_results)
    
    # Sort by similarity score in descending order
    all_results.sort(key=lambda x: x["similarity_score"], reverse=True)
    
    return all_results[:n_results]


def search_and_display(query: str):
    """
    Helper function to search and print results nicely
    """
    
    print(f"\n🔍 Query: \"{query}\"")
    print("-" * 50)
    
    results = retrieve_similar_documents(query)
    
    if not results:
        print("❌ No results found.")
        return
    
    for doc in results:
        print(f"\n📄 Rank {doc['rank']}: {doc['metadata'].get('title', 'Unknown')}")
        print(f"   Similarity: {doc['similarity_score']:.4f}")
        print(f"   Preview: {doc['document'][:150]}...")


if __name__ == "__main__":
    print("=" * 50)
    print("🏃 TESTING RAG SERVICE")
    print("=" * 50)
    
    # Test 1: Pressing question
    search_and_display("Which team uses high pressing?")
    
    # Test 2: Specific team
    search_and_display("Tell me about Arsenal's playing style")
    
    # Test 3: Tactical concept
    search_and_display("What is possession football?")
    
    # Test 4: Competition style
    search_and_display("How are Champions League matches decided?")
