"""Model pricing configuration- Update this file if pricing of model changes"""

# Prices Per 1 million tokens in USD


MODEL_PRICING_PER_1M_TOKENS = {
    "gpt-4.1-mini": {
        "input": 0.15,
        "output": 0.60,
        "description": "Fast, cheap, good for RAG"
    },
    "gpt-4o-mini": {
        "input": 0.15,
        "output": 0.60,
        "description": "Latest mini model"
    },
    "gpt-3.5-turbo": {
        "input": 0.50,
        "output": 1.50,
        "description": "Legacy, still works"
    },
    "gpt-4o": {
        "input": 2.50,
        "output": 10.00,
        "description": "High quality, expensive"
    }
}

DEFAULT_MODEL = "gpt-4o-mini"

UNKNOWN_MODEL_PRICING = {
    "input": 1.00,
    "output": 2.00
}

def get_model_pricing(model_name: str) -> dict:
    """
    Get the pricing for a given model. If the model is not found, return default unknown pricing.
    
    Args:
        model_name: Name of the model to get pricing for.
    Returns:
        A dictionary with 'input' and 'output' pricing per 1 million tokens.
    """
    return MODEL_PRICING_PER_1M_TOKENS.get(model_name, UNKNOWN_MODEL_PRICING)


def calculate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calculate the cost of a request based on the model and token usage.
    
    Args:
        model_name: Name of the model used for the request.
        input_tokens: Number of input tokens used.
        output_tokens: Number of output tokens generated.
    Returns:
        Total cost in USD for the request.
    """

    prcing = get_model_pricing(model_name)
    input_cost = (input_tokens / 1_000_000) * prcing["input"]
    output_cost = (output_tokens / 1_000_000) * prcing["output"]
    return round(input_cost + output_cost, 10)
