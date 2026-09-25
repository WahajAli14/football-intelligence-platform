from app.db.chroma_client import get_chroma_client, get_or_create_collection
from app.data.football_docs import football_documents

def create_vector_store():
    """
        Create embeddings and store football documents in ChromaDB.
        Run this once to populate the database.
    """
    client = get_chroma_client()
    collection = get_or_create_collection(client, "football_docs")
    
    existing_count = collection.count() 
    if existing_count > 0:
        print(f"Collection already has {existing_count} documents. Skipping population.")
        return
    
    #data to be stored in ChromaDB
    ids = []
    texts = []
    metadatas = []

    for doc in football_documents:
        ids.append(doc["id"])
        texts.append(doc["text"])
        metadatas.append({"title": doc["title"]})

    collection.add(
        ids=ids,
        documents=texts,
        metadatas=metadatas
    )

    print(f"✅ Added {len(ids)} documents to ChromaDB")
    print(f"📊 Total documents in collection: {collection.count()}")

    return collection

def delete_collection():
    """
        Delete the football_docs collection from ChromaDB.
        Use this if you want to reset the database and re-run create_vector_store().
    """
    try:
        client = get_chroma_client()
        client.delete_collection("football_docs")
        print("🗑️ Deleted 'football_docs' collection from ChromaDB")
    except Exception as e:
        print(f"Error occurred while deleting collection: {e}")


if __name__ == "__main__":
    create_vector_store()
    # delete_collection()  # Uncomment to delete the collection if needed