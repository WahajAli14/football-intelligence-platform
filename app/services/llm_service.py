import os
from openai import AuthenticationError, NotFoundError, OpenAI, OpenAIError, RateLimitError
from dotenv import load_dotenv
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.config.pricing import calculate_cost, get_model_pricing

PROJECT_ROOT = Path(__file__).resolve().parents[2]

class LLMService:
    """
    Service for interacting with OpenAI's language models.
    Pure Generation, no retrieval or vector search logic here.
    """

    def __init__(self, model: Optional[str] = None, temperature: float = 0.3, max_tokens: int = 300):
        """
        Initialize the LLMService with OpenAI API key.

        Args:
        model: OpenAI model to use for generation (default: OPENAI_MODEL or "gpt-4.1-mini")
        tempertature: Controls randomness of output Lower values make output more deterministic, higher values make it more creative.)
        max_tokens: Maximum number of tokens to generate in the response.
        """
        load_dotenv(PROJECT_ROOT / ".env")  # Load environment variables from .env file
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set in environment variables.")
        self.client = OpenAI(api_key=self.api_key)
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        self.temperature = temperature
        self.max_tokens = max_tokens

        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.total_requests = 0
        self.request_log = []  # Store details of each request for monitoring and debugging

    def _build_context(self, retrieved_docs: List[Dict[str, Any]]) -> str:
        """
        Build a context string from retrieved documents to provide to the LLM.
        
        Args: retrieved_docs: List of documents with metadata and relevance scores.
        Returns: A formatted string containing the context for the LLM

        """
        context_parts = []
        for doc in retrieved_docs:
            title = doc['metadata'].get('title', 'No Title')
            content = doc['document']
            context_parts.append(f"Title: {title}\nContent: {content}\n\n")
        return "\n\n---\n\n".join(context_parts)
    
    def _build_prompt(self, query: str, context: str) -> str:
        """
        Build a prompt for the LLM that includes the user's query and the retrieved context.
        For anti  hallucination, we explicitly instruct the 
        model to use the provided context to answer the question.
        
        Args:
        query: The user's original query.
        context: The context string built from retrieved documents.
        
        Returns:
        A formatted prompt string to send to the LLM.
        """
        prompt = f"""
        You are a football tactics expert. Answer the user's question based ONLY on the provided documents.
        {context}

        USER QUESTION: {query}

        INSTRUCTIONS:
        - Answer only using the information from the documents above
        - If the documents don't contain the answer, say "I don't know" or "I don't have enough information about that based on the provided documents."
        - Do not add information from your own knowledge
        - Be concise and to the point
        - Cite which document you're referencing
        Answer:"""
        return prompt
    
    def log_request(self, query: str, input_tokens: int, output_tokens: int, cost: float, success: bool = True):
        """
        Log details of each LLM request for monitoring and debugging.
        
        Args:
        query: The user's original query.
        input_tokens: Number of tokens in the input (prompt + context).
        output_tokens: Number of tokens in the generated answer.
        cost: Calculated cost of the request based on token usage and model pricing.
        success: Whether the request was successful or if an error occurred.
        """
        self.request_log.append({
            "query": query,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "success": success
        })

    def generate_answer(self, query: str, retrieved_docs: List[Dict[str, Any]]) -> str:
        """
        Generate an answer using retrieved documents as context.

        Args:
            query: User's original question
            retrieved_docs: List of documents from retrieve_similar_documents()
        Returns:
            Generated answer as string
        """
        if not retrieved_docs:
            return "No documents provided. Cannot generate an answer."

        # Build context and prompt
        context =  self._build_context(retrieved_docs= retrieved_docs)
        prompt  = self._build_prompt(query=query, context=context)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions about football tactics based on provided documents."},
                    {"role": "user", "content": prompt}
                ]
            )
            usage = response.usage
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens
            total_tokens = input_tokens + output_tokens

            cost = calculate_cost(model_name=self.model, input_tokens=input_tokens, output_tokens=output_tokens)

            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.total_cost += cost
            self.total_requests += 1

            return {
                "answer": response.choices[0].message.content.strip(),
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens
                },
                "cost_usd": cost
            }

        except AuthenticationError:
            print("OpenAI authentication failed. Check OPENAI_API_KEY.")
            return "OpenAI authentication failed. Check your API key."
        except NotFoundError:
            print(f"OpenAI model not found or not accessible: {self.model}")
            return f"The configured OpenAI model '{self.model}' is not available for this API project."
        except RateLimitError as e:
            if "insufficient_quota" in str(e):
                print("OpenAI quota exceeded. Check your plan and billing details.")
                return "OpenAI quota exceeded. Check your plan and billing details."

            print("OpenAI rate limit exceeded. Try again later.")
            return "OpenAI rate limit exceeded. Try again later."
        except OpenAIError as e:
            print(f"OpenAI API error during LLM generation: {e}")
            return "An OpenAI API error occurred while generating the answer."
        except Exception as e:
            print(f"Unexpected error during LLM generation: {e}")
            return "An unexpected error occurred while generating the answer."

    def get_stats(self) -> Dict[str, Any]:
        """Get current usage statistics."""
        return {
            "total_requests": self.total_requests,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_cost_usd": round(self.total_cost, 8),
            "average_cost_per_request": round(self.total_cost / max(self.total_requests, 1), 8),
            "model": self.model
        }

    def reset_stats(self):
        """Reset all statistics."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.total_requests = 0
        self.request_log = []


_llm_service_instance = None

def get_llm_service() -> LLMService:
    """Get or create singleton LLM service instance."""
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = LLMService()
    return _llm_service_instance

if __name__ == "__main__":
    llmservice= get_llm_service()
        
