# J.A.Y. — Just Assists You

> A complete personal AI operating system. Talks naturally, thinks critically, remembers everything, controls your computer, builds software, analyzes markets, researches the web, and never stops working.

---

## Architecture Overview

```
jay/
├── backend/                   # Python FastAPI backend
│   └── app/
│       ├── main.py            # Entry point
│       ├── core/              # Config, database, security, event bus
│       ├── providers/         # AI: Ollama, OpenAI, Gemini, OpenRouter
│       ├── agents/            # 8 specialized agents + coordinator
│       ├── tools/             # Desktop, file, terminal, web tools
│       ├── memory/            # ChromaDB vector memory
│       ├── voice/             # STT (Whisper), TTS (Edge TTS), wake word
│       ├── trading/           # Market data, indicators, paper trading
│       ├── api/               # REST endpoints + WebSocket
│       └── models/            # SQLAlchemy DB models
│
├── frontend/                  # Next.js + TypeScript UI
│   └── src/
│       ├── app/               # Next.js app router
│       ├── components/
│       │   ├── hud/           # Orb, visualizer, particles, metrics
│       │   ├── panels/        # All 10 workspace panels
│       │   └── ui/            # Layout, sidebar, modals
│       ├── store/             # Zustand global state
│       ├── lib/               # API client, WebSocket client
│       └── types/             # TypeScript types
│
├── src-tauri/                 # Tauri desktop shell (Rust)
│   └── src/main.rs            # Tray, shortcuts, window management
│
└── scripts/
    ├── start.sh               # Linux/macOS startup
    └── start.ps1              # Windows startup
```

---

## Quick Start

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.10+ | Backend |
| Node.js | 18+ | Frontend |
| Ollama | latest | Local AI (recommended) |
| Rust | 1.70+ | Tauri desktop build |

### 1. Install Ollama (Free Local AI)
```bash
# Linux/macOS
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3

# Windows: Download from https://ollama.ai/download
```

### 2. Clone & Configure
```bash
git clone <repo>
cd jay

# Configure backend
cp backend/.env.example backend/.env
# Edit backend/.env (Ollama works out of the box, no API key needed)
```

### 3. Start J.A.Y.

**Linux/macOS:**
```bash
chmod +x scripts/start.sh
./scripts/start.sh
```

**Windows:**
```powershell
.\scripts\start.ps1
```

**Manual start:**
```bash
# Terminal 1 — Backend
cd backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000** in your browser.

### 4. Build Desktop App (Tauri)
```bash
cd frontend
npm install
npm run tauri build
# Installer at: src-tauri/target/release/bundle/
```

---

## AI Providers

J.A.Y. works with **any** of these providers. Ollama is recommended for full local/private operation:

| Provider | Cost | Privacy | Setup |
|----------|------|---------|-------|
| **Ollama** | Free | 100% Local | `ollama pull llama3` |
| OpenAI | Paid | Cloud | Set `OPENAI_API_KEY` in `.env` |
| Google Gemini | Free tier | Cloud | Set `GOOGLE_API_KEY` in `.env` |
| OpenRouter | Free tier | Cloud | Set `OPENROUTER_API_KEY` in `.env` |

Automatic fallback: if your primary provider fails, J.A.Y. falls back to the next available one.

---

## Voice System

| Feature | Technology | Key Needed? |
|---------|-----------|-------------|
| Speech-to-Text | faster-whisper (local) | No |
| Text-to-Speech | Edge TTS (Microsoft) | No |
| Wake Word | Porcupine / Whisper fallback | Optional |

**Wake words:** "Hey J.A.Y." · "Wake up J.A.Y." · "J.A.Y."

**Global shortcut:** `Ctrl+Shift+V` opens voice mode

---

## Agent System

| Agent | Role |
|-------|------|
| **Coordinator** | Routes requests, orchestrates agents, direct conversation |
| **Planner** | Breaks complex tasks into execution plans |
| **Research** | Web search, documentation, fact-finding |
| **Coding** | Builds software, debugs, reviews code, manages Git |
| **Market** | Trading analysis, technical indicators, market data |
| **Creative** | Image generation, UI concepts, marketing materials |
| **Memory** | Stores and retrieves long-term knowledge |
| **Reviewer** | Quality checks for code, plans, and outputs |

---

## Tool Framework

| Category | Tools |
|----------|-------|
| Desktop | Open apps, list running processes, screenshot, system info |
| Files | Read, write, create, move, delete, search, scan projects |
| Terminal | Execute commands, Git operations, npm/pip |
| Web | DuckDuckGo search, fetch URLs, news feeds |

**Security levels:** Safe (auto) → Moderate (once) → Dangerous (always confirm) → Critical (typed confirmation)

---

## Trading Workspace

- **Markets:** NSE, BSE, Forex, Crypto (CCXT), US Stocks
- **Indicators:** RSI, MACD, EMA, SMA, Bollinger Bands, VWAP, ATR
- **Strategies:** RSI Reversal, EMA Crossover, MACD Crossover
- **Paper Trading:** Virtual ₹1,00,000 capital, real prices
- **Backtesting:** Test any strategy on 1–5 years of historical data

⚠️ J.A.Y. never guarantees profits. All signals are probabilistic.

---

## Memory System

J.A.Y. uses **ChromaDB** with **sentence-transformers** for semantic vector memory.

```
Namespaces: general, conversations, projects, trading, research, code
Categories: fact, preference, habit, project, lesson, research, contact, task
```

Example:
```
User: "My favorite framework is FastAPI"
→ Stored automatically

3 months later:
User: "What framework should I use for this API?"
→ J.A.Y. recalls your preference
```

---

## UI Panels

| Panel | Features |
|-------|---------|
| **Chat** | Streaming conversation, markdown rendering, voice input |
| **Voice** | Wake word, live waveform, TTS testing |
| **Dashboard** | System metrics, agent status, activity feed |
| **Trading** | Live quotes, indicators, watchlist, portfolio, backtest |
| **Memory** | Semantic search, add/delete memories, namespace view |
| **Projects** | Project management, tasks, project scanner |
| **Terminal** | Full shell with built-in commands |
| **Research** | Web search, URL fetcher |
| **Notifications** | Real-time alerts and approvals |
| **Settings** | Provider selection, voice config, security |

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+J` | Toggle J.A.Y. window |
| `Ctrl+Shift+V` | Open voice mode |
| `Enter` | Send message |
| `Shift+Enter` | New line in chat |
| `↑↓` | Terminal history navigation |

---

## API Documentation

With backend running: **http://localhost:8000/docs**

Key endpoints:
- `POST /api/chat/message` — Send message (supports streaming)
- `GET /ws` — WebSocket for real-time events
- `GET /api/trading/quote/{symbol}` — Live market quote
- `POST /api/voice/speak` — Text to speech
- `POST /api/memory/search` — Semantic memory search
- `POST /api/tools/execute` — Execute any tool

---

## Development

```bash
# Run tests
cd backend
pytest tests/ -v

# Format code
black app/
ruff app/

# Database migrations
alembic upgrade head
```

---

## License

MIT — Build freely, use freely.

---

*J.A.Y. is cooperative, not obedient. Trust is earned through competence and accuracy.*
