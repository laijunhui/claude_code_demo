import json
import os
import re
from typing import TypedDict
from dotenv import load_dotenv
from pydantic import BaseModel
from langgraph.graph import StateGraph, START, END
from langchain.agents import create_agent
from langchain.tools import tool

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

# Get model from config module
model = get_model(temperature=0)

class State(TypedDict):
    question: str
    rewritten_query: str
    documents: list[str]
    answer: str

# Simple in-memory knowledge base (no embeddings needed)
KNOWLEDGE_BASE = [
    # Rosters
    "New York Liberty 2024 roster: Breanna Stewart, Sabrina Ionescu, Jonquel Jones, Courtney Vandersloot.",
    "Las Vegas Aces 2024 roster: A'ja Wilson, Kelsey Plum, Jackie Young, Chelsea Gray.",
    "Indiana Fever 2024 roster: Caitlin Clark, Aliyah Boston, Kelsey Mitchell, NaLyssa Smith.",
    # Game results
    "2024 WNBA Finals: New York Liberty defeated Minnesota Lynx 3-2 to win the championship.",
    "June 15, 2024: Indiana Fever 85, Chicago Sky 79. Caitlin Clark had 23 points and 8 assists.",
    "August 20, 2024: Las Vegas Aces 92, Phoenix Mercury 84. A'ja Wilson scored 35 points.",
    # Player stats
    "A'ja Wilson 2024 season stats: 26.9 PPG, 11.9 RPG, 2.6 BPG. Won MVP award.",
    "Caitlin Clark 2024 rookie stats: 19.2 PPG, 8.4 APG, 5.7 RPG. Won Rookie of the Year.",
    "Breanna Stewart 2024 stats: 20.4 PPG, 8.5 RPG, 3.5 APG.",
]

@tool
def get_latest_news(query: str) -> str:
    """Get the latest WNBA news and updates."""
    return "Latest: The WNBA announced expanded playoff format for 2025..."

@tool
def search_wikipedia(query: str) -> str:
    """Search the WNBA knowledge base for relevant information."""
    query_lower = query.lower()
    results = []
    for doc in KNOWLEDGE_BASE:
        # Simple keyword matching
        keywords = query_lower.split()
        if any(kw in doc.lower() for kw in keywords if len(kw) > 2):
            results.append(doc)
    if not results:
        return "No relevant information found."
    return "\n".join(results)

# Create agent with tools
agent = create_agent(
    model=model,
    tools=[get_latest_news, search_wikipedia],
)

def rewrite_query(state: State) -> dict:
    """Rewrite the user query for better retrieval."""
    system_prompt = """Rewrite this query to retrieve relevant WNBA information.
The knowledge base contains: team rosters, game results with scores, and player statistics (PPG, RPG, APG).
Focus on specific player names, team names, or stat categories mentioned.
Return your response as a JSON object with a single key "query" containing the rewritten query.
Example: {"query": "2024 WNBA championship winner"}"""

    response = model.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": state["question"]}
    ])

    # Parse JSON from response
    content = response.content
    # Try to extract JSON from the response
    match = re.search(r'\{[^}]*"query"[^}]*\}', content, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())
            return {"rewritten_query": parsed.get("query", state["question"])}
        except json.JSONDecodeError:
            pass
    # Fallback: use the original question
    return {"rewritten_query": state["question"]}

def retrieve(state: State) -> dict:
    """Retrieve documents based on the rewritten query."""
    query = state["rewritten_query"].lower()
    results = []
    for doc in KNOWLEDGE_BASE:
        keywords = query.split()
        if any(kw in doc.lower() for kw in keywords if len(kw) > 2):
            results.append(doc)
    return {"documents": results}

def call_agent(state: State) -> dict:
    """Generate answer using retrieved context."""
    context = "\n\n".join(state["documents"])
    prompt = f"Context:\n{context}\n\nQuestion: {state['question']}"
    response = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
    messages = response.get("messages", [])
    if messages:
        last_msg = messages[-1]
        if hasattr(last_msg, "content"):
            return {"answer": last_msg.content}
    return {"answer": "No answer generated."}

workflow = (
    StateGraph(State)
    .add_node("rewrite", rewrite_query)
    .add_node("retrieve", retrieve)
    .add_node("agent", call_agent)
    .add_edge(START, "rewrite")
    .add_edge("rewrite", "retrieve")
    .add_edge("retrieve", "agent")
    .add_edge("agent", END)
    .compile()
)


# ============== Main Execution ==============

if __name__ == "__main__":
    # Run with tracing
    print("=== Pipeline Execution Trace ===\n")
    for step in workflow.stream({"question": "Who won the 2024 WNBA Championship?"}):
        for node_name, node_output in step.items():
            print(f"[{node_name}]")
            if "rewritten_query" in node_output:
                print(f"  Rewritten Query: {node_output['rewritten_query']}")
            if "documents" in node_output:
                print(f"  Retrieved {len(node_output['documents'])} documents")
            if "answer" in node_output:
                print(f"  Answer: {node_output['answer'][:200]}...")
            print()
