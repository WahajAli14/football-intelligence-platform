import os
import chromadb
from chromadb.config import Settings

BASE_DIR = (
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
chroma_path = os.path.join(BASE_DIR, "chroma_db")

def get_chroma_client():
    """
    Creates a persistent ChromaDB client.

    Persistent means your stored documents/embeddings
    will remain saved even after restarting the app.
    """

    client = chromadb.PersistentClient(
        path=chroma_path,
        settings=Settings(anonymized_telemetry=False)
    )
    return client

def get_or_create_collection(client, collection_name="football_docs"):
    """
    Gets an existing ChromaDB collection.
    If it does not exist, creates a new one.
    """
    collection = client.get_or_create_collection(
        name=collection_name
    )
    return collection