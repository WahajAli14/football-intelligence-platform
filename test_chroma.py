from app.db.chroma_client import get_chroma_client, get_or_create_collection

client = get_chroma_client()
collection = get_or_create_collection(client)

print(f"✅ ChromaDB ready!")
print(f"📁 Database location: chroma_db/")
print(f"📚 Collection name: {collection.name}")
print(f"📊 Current documents: {collection.count()}")
