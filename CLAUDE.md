# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **multi-agent code review tool** built with FastAPI that automatically reviews Python code through parallel agent execution:
- **SyntaxAgent**: Uses pylint for Python syntax checking
- **SecurityAgent**: Uses bandit for security vulnerability scanning
- **StyleAgent**: Uses MiniMax AI API for code style/best practices

## Common Commands

```bash
# Navigate to project directory
cd code-reviewer

# Install dependencies
pip install -r requirements.txt

# Install code checking tools
pip install pylint bandit

# Development server (with auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or use Python module
python -m app.main

# Docker build and run
docker build -t code-reviewer .
docker run -d -p 8000:8000 -e MINIMAX_API_KEY=your_key code-reviewer
```

## API Endpoints

- `POST /api/review` - Trigger code review
- `GET /api/review/{review_id}` - Get review results
- `GET /api/health` - Health check
- `POST /webhook/github` - GitHub webhook handler
- `GET /` - Root (HTML frontend)

## Architecture

```
app/
├── main.py           # FastAPI application entry point
├── config.py         # Settings (Pydantic BaseSettings)
├── logger.py         # Logging configuration
├── middleware.py     # Custom middleware
├── api/
│   ├── routes.py     # REST API endpoints
│   └── webhooks.py   # GitHub webhook handler
└── agents/
    ├── base.py       # BaseAgent abstract class, Issue, AgentResult, CodeFile
    ├── manager.py    # AgentManager - orchestrates multiple agents
    ├── syntax.py     # SyntaxAgent (pylint)
    ├── security.py   # SecurityAgent (bandit)
    └── style.py      # StyleAgent (MiniMax AI)
```

### Agent System

The agent system uses a plugin architecture:
1. `BaseAgent` (abstract) defines the interface
2. `AgentManager` runs all agents in parallel and aggregates results
3. Each agent inherits from `BaseAgent` and implements `review()` method

### Data Flow

1. Code submitted via REST API or GitHub Webhook
2. Files parsed into `CodeFile` dataclass
3. `AgentManager.review()` runs all agents in parallel via `asyncio.gather()`
4. Results aggregated into `AgentResult` with categorized issues by severity

## Environment Variables

Create `.env` from `.env.example`:

| Variable | Description |
|----------|-------------|
| `MINIMAX_API_KEY` | MiniMax API key for AI code review |
| `MINIMAX_MODEL` | Model name (default: MiniMax-M2.1) |
| `API_TOKEN` | API authentication token |
| `GITHUB_TOKEN` | GitHub API token for PR file access |
| `GITHUB_WEBHOOK_SECRET` | Webhook signature secret |
| `HOST`, `PORT` | Server configuration |
| `LOG_LEVEL`, `LOG_DIR` | Logging configuration |

## Development Notes

- Uses Python 3.11+ with asyncio for concurrent agent execution
- Experimental LangChain/LangGraph integration in `app/langchain/` directory
- No test framework currently configured
- Linting: `pylint app/` for Python syntax
- Security scanning: `bandit -r app/`
