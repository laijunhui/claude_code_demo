"""
LangChain Agent Demo
Demonstrates how to create an agent with tools, middleware, and structured output.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

from langchain.agents import create_agent
from langchain.tools import tool, ToolRuntime
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.structured_output import ToolStrategy
from langchain.agents.middleware import FilesystemFileSearchMiddleware

from .model_config import get_model

# Load environment variables
load_dotenv()
# Configure LangSmith tracing (optional)
if os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true":
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "langchain-agent-demo")
    if os.getenv("LANGSMITH_API_KEY"):
        os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
    if os.getenv("LANGCHAIN_ENDPOINT"):
        os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGCHAIN_ENDPOINT")
    print("LangSmith tracing enabled")

# ============== Data Classes ==============

@dataclass
class Context:
    """Custom runtime context schema."""
    user_id: str


@dataclass
class ResponseFormat:
    """Response schema for the agent."""
    punny_response: str
    weather_conditions: str | None = None


# ============== Tools ==============

@tool
def get_weather_for_location(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"


@tool
def get_user_location(runtime: ToolRuntime[Context]) -> str:
    """Retrieve user information based on user ID."""
    user_id = runtime.context.user_id
    return "Florida" if user_id == "1" else "SF"


# ============== Agent Factory ==============

SYSTEM_PROMPT = """You are an expert weather forecaster, who speaks in puns.

You have access to two tools:

- get_weather_for_location: use this to get the weather for a specific location
- get_user_location: use this to get the user's location

If a user asks you for the weather, make sure you know the location. If you can tell from the question that they mean wherever they are, use the get_user_location tool to find their location."""


def create_weather_agent(local_debug: bool = False):
    """Create and configure the weather agent.

    Args:
        local_debug: If True, use InMemorySaver for checkpointing.
    """
    # Get model from config module
    model = get_model(temperature=0, max_tokens=2048)

    # Create agent
    agent = create_agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[get_user_location, get_weather_for_location],
        context_schema=Context,
        response_format=ToolStrategy(ResponseFormat),
        checkpointer=InMemorySaver() if local_debug else None,
    )
    

    return agent


def create_file_search_agent():
    """Create an agent with filesystem search middleware."""
    # Get model from config module
    model = get_model(temperature=0, max_tokens=2048)

    # Create agent with filesystem middleware
    agent = create_agent(
        model=model,
        context_schema=Context,
        middleware=[
            FilesystemFileSearchMiddleware(
                root_path=os.path.expanduser("~/Workplace"),
                use_ripgrep=True,
                max_file_size_mb=10,
            ),
        ],
    )

    return agent


# Export for LangGraph Cloud (without checkpointer - LangGraph Cloud handles persistence)
weather_agent = create_weather_agent(False)


# ============== Main Execution ==============

if __name__ == "__main__":

    # Example 1: Weather Agent with tracing
    print("=" * 50)
    print("Example 1: Weather Agent with Tracing")
    print("=" * 50)

    agent = create_weather_agent(True)
    config = {"configurable": {"thread_id": "1"}}

    print("\n--- User: 'what is the weather outside?' ---\n")
    for step in agent.stream(
        {"messages": [{"role": "user", "content": "what is the weather outside?"}]},
        config=config,
        context=Context(user_id="1")
    ):
        for node_name, node_output in step.items():
            print(f"[{node_name}]")
            if "messages" in node_output:
                for msg in node_output["messages"]:
                    content = msg.content if hasattr(msg, "content") else str(msg)
                    print(f"  Message: {content[:200]}...")
            if "structured_response" in node_output:
                print(f"  Structured Response: {node_output['structured_response']}")
            print()

    print("=== Final Output ===")
    response = agent.get_state(config)
    print(response.values.get("structured_response"))

    # Continue conversation
    print("\n--- User: 'thank you!' ---\n")
    response = agent.invoke(
        {"messages": [{"role": "user", "content": "thank you!"}]},
        config=config,
        context=Context(user_id="1")
    )
    print(response)


    # Example 2: File Search Agent
    # print("\n" + "=" * 50)
    # print("Example 2: File Search Agent")
    # print("=" * 50)

    # file_agent = create_file_search_agent()
    # config2 = {"configurable": {"thread_id": "2"}}

    # result = file_agent.invoke(
    #     {"messages": [{"role": "user", "content": "Find all Python files containing 'async def'"}]},
    #     config=config2,
    #     context=Context(user_id="1")
    # )

    # messages = result.get("messages", [])
    # if messages:
    #     last_msg = messages[-1]
    #     content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
    #     print(f"\nResult: {content[:500]}...")
