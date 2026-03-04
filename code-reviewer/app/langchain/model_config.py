"""
Model configuration module for MiniMax (OpenAI-compatible interface).
"""

import os
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()


def get_model(
    model: str = None,
    temperature: int = 0,
    max_tokens: int = 2048,
    **kwargs
) -> ChatOpenAI:
    """Create a ChatOpenAI model configured for MiniMax.

    Args:
        model: Model name (defaults to MINIMAX_MODEL env var)
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        **kwargs: Additional arguments passed to ChatOpenAI

    Returns:
        Configured ChatOpenAI instance
    """
    return ChatOpenAI(
        model=model or os.getenv("MINIMAX_MODEL", "MiniMax-M2.1"),
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=os.getenv("MINIMAX_API_KEY"),
        base_url=os.getenv("MINIMAX_BASE_URL", "https://api.minimaxi.com/v1"),
        **kwargs
    )


# Default model instance
model = get_model()
