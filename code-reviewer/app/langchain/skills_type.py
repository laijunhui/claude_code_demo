"""
Skills-based Agent Demo
Demonstrates how to create an agent with skill middleware.
"""

import uuid
from typing import Callable
from dotenv import load_dotenv

from langchain.tools import tool
from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, ModelResponse, AgentMiddleware
from langchain.messages import SystemMessage
from langgraph.checkpoint.memory import InMemorySaver

# Use app logger
from app.logger import logger

# Load environment variables
load_dotenv()

# Import skills
from app.langchain.skills import SKILLS
import os

# Configure LangSmith tracing (optional)
if os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true":
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "langchain-agent-demo")
    if os.getenv("LANGSMITH_API_KEY"):
        os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
    if os.getenv("LANGCHAIN_ENDPOINT"):
        os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGCHAIN_ENDPOINT")
    print("LangSmith tracing enabled")

# ============== Tools ==============

@tool
def load_skill(skill_name: str) -> str:
    """Load the full content of a skill into the agent's context.

    Use this when you need detailed information about how to handle a specific
    type of request. This will provide you with comprehensive instructions,
    policies, and guidelines for the skill area.

    Args:
        skill_name: The name of the skill to load (e.g., "sales_analytics", "inventory_management")
    """
    logger.info(f"Loading skill: {skill_name}")

    # Find and return the requested skill
    for skill in SKILLS:
        if skill["name"] == skill_name:
            logger.info(f"Successfully loaded skill: {skill_name}")
            return f"Loaded skill: {skill_name}\n\n{skill['content']}"

    # Skill not found
    available = ", ".join(s["name"] for s in SKILLS)
    logger.warning(f"Skill not found: {skill_name}")
    return f"Skill '{skill_name}' not found. Available skills: {available}"


# ============== Middleware ==============

class SkillMiddleware(AgentMiddleware):
    """Middleware that injects skill descriptions into the system prompt."""

    # Register the load_skill tool as a class variable
    tools = [load_skill]

    def __init__(self):
        """Initialize and generate the skills prompt from SKILLS."""
        logger.info("Initializing SkillMiddleware")

        # Build skills prompt from the SKILLS list
        skills_list = []
        for skill in SKILLS:
            skills_list.append(
                f"- **{skill['name']}**: {skill['description']}"
            )
        self.skills_prompt = "\n".join(skills_list)
        logger.info(f"Loaded {len(SKILLS)} skills into middleware")

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Sync: Inject skill descriptions into system prompt."""
        logger.info("Wrapping model call with skill middleware")

        # Build the skills addendum
        skills_addendum = (
            f"\n\n## Available Skills\n\n{self.skills_prompt}\n\n"
            "Use the load_skill tool when you need detailed information "
            "about handling a specific type of request."
        )

        # Append to system message content blocks
        new_content = list(request.system_message.content_blocks) + [
            {"type": "text", "text": skills_addendum}
        ]
        new_system_message = SystemMessage(content=new_content)
        modified_request = request.override(system_message=new_system_message)

        logger.info("Skill middleware - request modified successfully")
        return handler(modified_request)


# ============== Agent Factory ==============

def create_skill_agent():
    """Create an agent with skill middleware."""
    from app.langchain.model_config import get_model

    logger.info("Creating skill agent")

    # Get model
    model = get_model(temperature=0, max_tokens=2048)
    logger.info(f"Using model: {model.model_name}")

    # Create agent with skill middleware
    agent = create_agent(
        model=model,
        system_prompt=(
            "You are a SQL query assistant that helps users "
            "write queries against business databases."
        ),
        middleware=[SkillMiddleware()],
        checkpointer=InMemorySaver(),
    )

    logger.info("Skill agent created successfully")
    return agent


# ============== Main Execution ==============

if __name__ == "__main__":
    logger.info("Starting Skills Agent Demo")

    # Create agent
    agent = create_skill_agent()

    # Configuration for this conversation thread
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    logger.info(f"Using thread_id: {thread_id}")

    # Ask for a SQL query
    user_query = (
        "Write a SQL query to find all customers "
        "who made orders over $1000 in the last month"
    )
    logger.info(f"User query: {user_query}")

    result = agent.invoke(
        {"messages": [{"role": "user", "content": user_query}]},
        config
    )

    # Print the conversation
    logger.info("=== Agent Response ===")
    for message in result["messages"]:
        if hasattr(message, "pretty_print"):
            message.pretty_print()
        else:
            print(f"{message.type}: {message.content}")

    logger.info("Skills Agent Demo completed")
