# LifeOS Agent 🤖

LifeOS Agent is an intelligent Telegram Bot assistant built to seamlessly manage your personal Notion workspace (LifeOS). Powered by LangGraph, OpenAI (`gpt-5-mini`), and the Model Context Protocol (MCP), it acts as your personal executive assistant.

## ✨ Key Features

- **Conversational Task Management**: Chat with the bot on Telegram to view tasks, update statuses, or log habits naturally without opening Notion.
- **Smart Notion Integration**: Securely connects to Notion via Notion MCP. It understands strict database mappings (Area, Project, Task, Habit) and handles complex nested Relation properties automatically.
- **Persistent Long-Term Memory**: Remembers past conversations context per-user using LangGraph's native `AsyncSqliteSaver`, ensuring flowing, continual interactions.
- **Built-in Circuit Breaker**: Safely handles failed tool calls using recursion limits to prevent token-draining infinite loops from LLM hallucinations or API limits.
- **Formatted Briefings**: Delivers concise markdown Executive Summaries directly to your phone screen to start your daily planning.

## 🛠️ Architecture & Tech Stack

- **Inference Engine**: [OpenAI](https://openai.com/) (`gpt-5-mini`) via `langchain-openai`.
- **Agent Orchestration**: [LangGraph](https://langchain-ai.github.io/langgraph/) defining State Graphs and state persistence.
- **Notion Tools**: [Model Context Protocol (MCP)](https://modelcontextprotocol.github.io/) integrated through `langchain-mcp-adapters`.
- **Interface**: [python-telegram-bot](https://python-telegram-bot.org/) for asynchronous messaging.
- **Database (Agent Memory)**: `aiosqlite` for local state persistence.

## 🚀 Setup & Installation

### 1. Prerequisites
- Python 3.10+
- An OpenAI API Key.
- A Telegram Bot Token (from BotFather).
- **Notion Setup**: Duplicate this [LifeOS Notion Template](https://antique-cheque-06a.notion.site/LifeOS-Template-30f05fdbc7d081758a5eec29f23439c2?pvs=73) to your workspace.
- Notion Integration Token & Notion Database IDs (extracted from the duplicated template).

### 2. Clone and Install
```bash
git clone https://github.com/huynvq02/lifeos-agent.git
cd lifeos-agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables
Copy `.env.example` to `.env` and fill in your keys:
```env
# API Keys
OPENAI_API_KEY=sk-proj-...
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11

# Notion Configuration
NOTION_AREA_DB_ID=your_area_db_id
NOTION_PROJECT_DB_ID=your_project_db_id
NOTION_TASK_DB_ID=your_task_db_id
NOTION_HABIT_DB_ID=your_habit_db_id
NOTION_HABIT_LOG_DB_ID=your_habit_log_db_id
```

### 4. Running the Agent
Start the bot server:
```bash
# Add src to Python Path
export PYTHONPATH=$(pwd)/src

# Run the agent
python src/main.py
```

## 🧠 How the Agent Reasons

1. **Cold Start**: If you send ambiguous greetings, the agent automatically probes your "Active Projects" and "Todo Tasks" today to give you a briefing.
2. **Entity Relation Mapping**: If you ask it to create a new task for a specific project, it refuses to guess IDs. It performs a chain-of-thought: Query Project DB -> Extract `page_id` -> Create Task strictly linked to that `page_id`.
3. **Protective Mechanisms**: Anthropic/OpenAI rate limit errors (HTTP 429) or Notion Schema Validation Errors (HTTP 400) auto-trigger the circuit breaker after 15 loops.
