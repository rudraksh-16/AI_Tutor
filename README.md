# AI Tutor Platform 🎓

AI Tutor is a personalized, AI-driven learning platform designed to guide users through any topic with structured, mastery-based learning. Built on a decoupled architecture, it uses a multi-agent system to negotiate curricula, plan chapters, teach concepts iteratively, and validate learning through quizzes.

---

## 🌟 Core Features

- **Personalized Curriculum Negotiation**: Chat with a Curriculum Agent to define your learning goals, prior knowledge, and depth of study.
- **Automated Chapter Planning**: A non-interactive Planner Agent generates a logical sequence of chapters based on your finalized curriculum.
- **Mastery-Based Teaching**: Interact with a Teacher Agent that tracks your progress through a specific chapter syllabus.
- **Knowledge Validation**: Pass AI-generated quizzes to unlock the next chapter in your curriculum.
- **Deep Research Integration**: Access supplementary, high-quality documentation synthesized by a multi-agent research pipeline.
- **Real-Time Streaming**: Tokens stream directly to the UI using Server-Sent Events (SSE) for a responsive, ChatGPT-like experience.

---

## 🏗️ Technical Architecture

The platform is designed for scalability and stateful AI interactions:

- **AI Orchestration**: Built using **LangGraph** to manage complex multi-agent flows and persistent conversation states.
- **Backend API**: A high-performance, asynchronous **FastAPI** server handling authentication, database operations, and agent execution.
- **Persistence**: **SQLAlchemy 2.0** with **PostgreSQL** for storing users, topics, chapters, and full conversation histories.
- **Frontend**: A modern **React 19** application (Vite + Tailwind CSS) communicating via REST and SSE.

---

## 🛠️ Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Backend** | Python 3.x, FastAPI, Uvicorn |
| **Database** | PostgreSQL, SQLAlchemy 2.0, asyncpg |
| **AI Framework** | LangGraph, LangChain |
| **LLM Provider** | OpenAI (GPT-4o, GPT-4o-mini) |
| **Search API** | Tavily Search |
| **Frontend** | React 19, Vite, Tailwind CSS |
| **Auth** | JWT (python-jose), bcrypt |

---

## 📂 Project Structure

```text
AI_Tutor/
├── src/
│   ├── main.py              # FastAPI Entry Point
│   ├── backend/             # Core Backend Logic
│   │   ├── api/             # REST & SSE Endpoints
│   │   ├── db/              # Database Configuration & Sessions
│   │   ├── models/          # SQLAlchemy ORM Models
│   │   ├── services/        # Business Logic Orchestration
│   │   └── schemas/         # Pydantic Request/Response Models
│   └── llm/                 # Multi-Agent Intelligence
│       ├── agent_core/      # Base Agent Classes
│       ├── curriculum_agent/
│       ├── planner/
│       ├── teacher_agent/
│       ├── quiz_agent/
│       └── deep_research/   # Multi-agent synthesis pipeline
├── logs/                    # Centralized logging directory
├── tests/                   # Automated test suites
├── .env.sample              # Template for environment variables
└── requirements.txt         # Python dependencies
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL
- OpenAI API Key
- Tavily API Key (for deep research)

### Backend Setup

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd AI_Tutor
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Mac/Linux
   # or
   .venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirments.txt
   ```

4. **Configuration**:
   Copy `.env.sample` to `.env` and fill in your credentials:
   ```bash
   cp .env.sample .env
   ```

5. **Run the Server**:
   ```bash
   uvicorn src.main:app --reload
   ```
   The API will be available at `http://localhost:8000`. You can view the interactive documentation at `http://localhost:8000/docs`.

---

## 📡 API Endpoints (Highlights)

- **Auth**: `POST /api/auth/register`, `POST /api/auth/login`
- **Topics**: `POST /api/v1/topics/start`, `GET /api/v1/topics/`
- **Streaming Chat**:
  - `POST /api/v1/chat/curriculum` (SSE)
  - `POST /api/v1/chat/teacher` (SSE)
  - `POST /api/v1/chat/quiz` (SSE)

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.