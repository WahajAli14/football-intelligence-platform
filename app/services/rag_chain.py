from typing import List, Dict, Any
from app.services.llm_service import get_llm_service
from app.services.rag_service import retrieve_similar_documents, search_accross_sources


class RAGChain:
    """
        Complete RAG pipeline orchestrator.
        Handles retrieval → generation flow.
    """


    def __init__(self, n_results: int = 3):
        self.n_results = n_results
        self.llm_service = get_llm_service()
    
    def retrieve(
        self,
        query: str,
        source_ids: List[str] = None,
        n_results: int = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents from one or more sources.
        """

        n = n_results if n_results else self.n_results

        if source_ids:
            return search_accross_sources(
                query=query,
                source_ids=source_ids,
                n_results=n,
            )

        return retrieve_similar_documents(
            query=query,
            n_results=n,
        )

    def generate(self, query: str, retrieved_docs: List[Dict[str, Any]]) -> str:
        """
        Args:
        query: User's question
        retrieved_docs: Documents from retrieve()
        
        Returns:
            Generated answer.
        """
        return self.llm_service.generate_answer(query, retrieved_docs)
    
    def ask(self, query: str, source_ids: List[str] = None, n_results: int = None) -> Dict[str, Any]:
        """
        Complete RAG pipeline: Retrieve → Generate.
        
        Args:
            query: User's question
            source_ids: List of source IDs to search across (optional)
            n_results: Number of documents to retrieve
        
        Returns:
            Dictionary with query, answer, and retrieved documents
        """
        retrieved_docs = self.retrieve(query, source_ids=source_ids, n_results=n_results)

        if not retrieved_docs:
            return {
                "query": query,
                "answer": "No relevant documents found to answer the question.",
                "retrieved_documents": [],
                "total_docs": 0,
                "usage": {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0
                },
                "cost_usd": 0.0
            }
        
        answer = self.generate(query, retrieved_docs)

        return {
            "query": query,
            "answer": answer["answer"],
            "retrieved_documents": retrieved_docs,
            "total_docs": len(retrieved_docs),
            "usage": answer["usage"],
            "cost_usd": answer["cost_usd"]
        }
    
    def get_stats(self):
        """
        Get cumulative stats about the RAG chain usage.
        """
        return self.llm_service.get_stats()
    
    def reset_stats(self):
        """
        Reset cumulative stats in the LLM service.
        """
        self.llm_service.reset_stats()

#Singleton instance of RAGChain
_rag_chain_instance = None

def get_rag_chain(n_results: int = 3) -> RAGChain:
    global _rag_chain_instance
    if not _rag_chain_instance:
        _rag_chain_instance = RAGChain(n_results=n_results)
    return _rag_chain_instance


if __name__ == "__main__":
    print("=" * 50)
    print("Testing RAG Chain (Class Version)")
    print("=" * 50)
    
    rag = RAGChain(n_results=3)
    
    test_query = "Which team uses high pressing?"
    print(f"\n🔍 Query: {test_query}")
    
    result = rag.ask(test_query)
    
    print(f"\n📚 Retrieved {result['total_docs']} documents")
    print(f"\n🤖 Answer:\n{result['answer']}")
