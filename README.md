# DHANGURU (धनगुरु)
### Autonomous Watchlist & Market Intelligence Co-Pilot for Indian Equities (NSE/BSE)

> Transforming noisy, passive ticker grids into an active, responsible market intelligence co-pilot.

**Live Demo:** https://dhanguru.onrender.com/

---

## WHY (The Problem & Philosophy)

### The Problem
Standard trading screens present a wall of 50 numbers flashing green and red every second. Retail investors suffer from cognitive overload, trying to mentally calculate percentage changes, volume spikes, and circuit band limits across dozens of stocks simultaneously. By the time an investor spots an abnormal movement, the trade has often already passed or the stock has hit an exchange freeze.

### The Philosophy
Market data should not just be displayed; it should be interpreted. Investors should not have to spend hours decoding complex charts just to answer one simple question:

> *"Which stock on my list demands my immediate attention right now, and why?"*

DhanGuru was built to act as an air-traffic controller for your watchlist, filtering out market noise and highlighting high-impact events automatically.

---

## WHAT (The Solution & Core Features)

DhanGuru is a real-time, intelligent watchlist co-pilot tailored specifically for Indian equities (NSE/BSE). It continuously monitors price velocity, volume deviations, and volatility to elevate critical movements and explain them in plain English.

* **Dynamic Urgency-Ranked Watchlist:** Unlike traditional static watchlists, cards automatically re-rank themselves in real time based on an algorithmic urgency score. Stocks approaching circuit limits or experiencing sudden volume surges bubble straight to the top.
* **"While You Were Away" AI Briefings:** An on-demand AI co-pilot synthesizes multi-stock changes into a clear executive summary, giving users an instant narrative of market context without financial jargon.
* **Circuit Breaker Radar:** Visual proximity indicators show exactly how close a stock is to its exchange-mandated upper or lower circuit limit (such as 5%, 10%, or 20% price bands), helping traders manage liquidity risk before getting trapped.
* **On-the-Fly Stock Search & Sector Filters:** Users can look up and add any NSE equity on demand, or filter their view across eight major sector baskets (Banking, IT, Auto, Pharma, Energy, FMCG, Metals, Real Estate).
* **FOMO Guard (Capital Protection):** Contextual warnings alert users when a stock is spiking on low volume or is pinned against a circuit band, advising against emotional chasing.

### Top Highlights
* **Zero-cost and self-hostable:** Supports 100% offline local AI via Ollama, as well as cloud models like Gemini and Groq.
* **Purpose-built for Indian market structure:** Full support for NSE/BSE trading sessions, circuit bands, and Nifty 50 benchmarking.
* **Production-ready:** Packaged into a single lightweight container with rate limiting and 38 passing automated tests.

---

## HOW (Architecture, Engineering Smartness & Trade-offs)

### 1. Architectural Design

* **Hybrid Market Feed:** DhanGuru recognizes Indian market hours (09:15 to 15:30 IST, Monday to Friday). During active market hours, it streams live exchange data. Outside market hours and on weekends, it automatically switches to a session replay simulator, ensuring the platform remains dynamic and testable around the clock.
* **In-Memory Central Store:** Ticks and rolling historical windows are managed in an in-memory store. Anomaly detection runs in microseconds without the latency of relational database queries.
* **Event-Driven WebSocket Broadcasts:** The backend pushes updates to the browser only when meaningful changes occur, avoiding client-side polling and reducing network overhead.
* **Flexible Multi-Tier AI Layer:** Connects to local LLMs (Ollama) for complete data privacy, cloud LLMs (Gemini, Groq) for rapid processing, or a deterministic fallback rule engine if no model is reachable.

### 2. Deliberate Trade-offs

* **In-Memory Buffers vs Heavy Database:** We selected an in-memory rolling buffer instead of writing every tick to a persistent database.
  * *Trade-off:* We do not store multi-year tick archives, but we achieve sub-millisecond anomaly evaluation and zero database write-locks during high-volume market bursts.
* **Algorithmic Rules for Alerts vs LLMs for Every Tick:** We use deterministic mathematical formulas to detect volume spikes and circuit proximity, reserving generative AI strictly for high-level summaries when requested by the user.
  * *Trade-off:* Running an LLM on every incoming tick is cost-prohibitive, slow, and prone to hallucinations. Mathematical filters ensure instant, accurate alerts while keeping computing costs at zero.
* **Intelligent Hybrid Feed vs Expensive Institutional Feeds:** Institutional exchange feeds cost thousands of dollars a month. We engineered a combination of resilient polling, client-side interpolation, and weekend simulation replay.
  * *Trade-off:* Delivers an institutional-grade live experience for retail users and evaluators without incurring recurring enterprise data bills.

---

## EDGE CASES (And How They Are Handled)

### 1. AI & LLM Resilience
* **Missing API Key, Offline Local LLM, or Network Downtime:** Built-in `RuleEngineBriefingFallback` deterministically synthesizes human-readable market briefings from quantitative price, volume, and benchmark numbers whenever Gemini or Ollama is unavailable or unconfigured. This guarantees 100% uptime with zero UI crashes.
* **LLM Formatting & Parsing Errors (JSON Validation):** Employs a flat Pydantic schema (`AIBriefingOutput`) and native grammar-constrained decoding (`format="json"` in Ollama). If an LLM emits markdown fences, truncated output, or malformed JSON, the exception is caught and gracefully redirected to the rule fallback.
* **AI Rate-Limit & Token Quota Exhaustion (Gemini 15 RPM Free Tier):** An in-memory 20-second TTL cache (`_briefing_cache`) intercepts rapid page refreshes and multi-tab opens, returning cached briefings instantly without consuming API quota.

### 2. Real-Time Streaming & WebSockets
* **Client Network Dropouts & Disconnections:** The frontend custom hook (`useMarketStream.js`) automatically detects disconnections and attempts reconnection using a 3-second backoff loop. On the backend, `WebSocketDisconnect` cleanly removes inactive socket handles from `ConnectionManager` to prevent memory leaks or broken pipe exceptions.
* **Simulation Flooding & WebSocket Buffer Saturation:** Added a server-side 3-second cooldown on `/api/stream/simulate-anomaly` to block repeated user clicks, protecting background event queues and client-side message buffers from lag.

### 3. Market Data & Calculation Math
* **Division by Zero & Missing Historical Ticks:** Mathematical guards check that volatility baselines are greater than zero before calculating volatility ratios and check that past prices are positive before calculating percentage changes. Missing ticks fall back to previous close baselines to prevent application runtime errors.
* **Empty Watchlist Scenario:** The diff engine detects when zero symbols are tracked and produces an onboarding state with actionable instructions to add stocks, skipping unnecessary LLM inferences.
* **Circuit Limit Proximity & Risk Escalation:** The anomaly engine dynamically monitors daily volatility bands, relative volume, and circuit proximity (within 1% of the upper or lower price band). If breached, it elevates the stock to CRITICAL urgency and injects FOMO Guard risk warnings.

### 4. Storage & State Persistence
* **Session Acknowledgement Spam & Concurrent Disk Writes:** The `WatchlistStore` enforces a 5-second debounce window on `acknowledge_session()`. Rapid clicks or automated requests update in-memory timestamps without thrashing disk I/O on `.watchlist_data.json`.
* **Corrupted or Missing Watchlist File:** The store wraps JSON file reads in safe try/except blocks. If the storage file is missing, empty, or corrupted, it automatically re-seeds with a default portfolio of major Indian equities (ZOMATO, TRENT, TATAMOTORS, RELIANCE, HDFCBANK, INFY, ITC) dated two hours in the past for instant demo data.

### 5. Security, DoS & Deployment Routing
* **API Flooding & DoS Attacks:** Built-in `InMemoryRateLimiterMiddleware` enforces a strict 120 req/min sliding window per client IP. Malicious bursts receive an immediate HTTP 429 Too Many Requests response, while streaming WebSockets (`/ws/`), health checks (`/health`), and static assets are exempt for speed.
* **Single-Page Application (SPA) 404s on Refresh:** The production Docker container serves both backend and frontend from a single port. FastAPI includes an SPA fallback handler that serves `dist/index.html` for browser route refreshes (such as `/watchlist` or `/analytics`), while correctly preserving 404 errors for invalid `/api/*` endpoints.
* **Dynamic Host Port Assignment (Railway / Render):** The unified container uses dynamic shell evaluation (`--port ${PORT:-8000}`) to bind automatically to any port assigned by cloud platforms without port conflict errors.

---

## Instructions to Run

### Option 1: Docker (Single Container, Production Ready)

```powershell
docker build -t dhanguru .
docker run -p 8000:8000 dhanguru
```
Open `http://localhost:8000` in your browser.

---

### Option 2: Local Development Setup

#### Step 1: Clone the repository
```bash
git clone https://github.com/DishaGarg-16/dhanguru.git
cd dhanguru
```

#### Step 2: Configure Environment Variables
```bash
copy .env.example .env
```
*(Optional: Add your `GEMINI_API_KEY` in `.env` if you wish to use Google Gemini. If omitted, DhanGuru automatically falls back to local Ollama or the built-in deterministic rule engine).*

#### Step 3: Start the Backend (FastAPI + WebSockets)
```powershell
uv sync
uv run uvicorn backend.app.main:app --reload
```
The backend API and WebSocket stream will run on `http://127.0.0.1:8000`.

#### Step 4: Start the Frontend (React + Vite)
In a separate terminal window:
```powershell
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

#### Step 5: (Optional) Run Offline Local AI with Ollama
If you want completely free, 100% private offline AI briefings:
```bash
ollama run llama3.2
```

---

## Evaluator / Demo Walkthrough

Judges and evaluators testing outside Indian trading hours (9:15 AM to 3:30 PM IST) can test all real-time features using the built-in simulator:

1. **Verify AI Briefing:**
   * Check the **"Since You Checked"** card at the top.
   * Notice the macro summary and key takeaways generated by the AI co-pilot (or rule fallback).
2. **Trigger Simulated Anomalies:**
   * Click the **"Simulate Anomaly"** dropdown in the top navigation bar.
   * Click **"Push TRENT to Upper Circuit"**: Notice the circuit limit meter glow, the urgency score jump into the CRITICAL tier (elevated to 78 or 88 based on proximity), and the Capital Protection Notice appear.
   * Click **"Surge ZOMATO (3.4x volume)"**: Notice the Relative Volume badge jump to 3.4x with volume surge tags.
3. **Test Time-Travel Scrubbing:**
   * Click **"Past 15m"**, **"Past 1h"**, or **"Past 3h"** on the delta bar to see the briefing dynamically re-evaluate past time windows.
4. **1-Click Checkpoint Acknowledge:**
   * Click **"Acknowledge & Mark All Caught Up"**.
   * Notice the timer immediately reset to `0s` ("All caught up. Monitoring in real time").
5. **Dynamic Stock Discovery & Sector Filters:**
   * Click **"+ Add Stock"** to open the discovery modal.
   * Click sector chips like **"Automobile"**, **"Banking & Finance"**, or **"IT & Tech"** to browse curated equities.
   * Type in the search box (e.g. `zom` or `tata`) to see live search suggestions across 2,000+ Indian equities.
   * Click **"+ Add"** on any stock to observe it register directly into the live ticker stream without restarting the server.

---

## Tech Stack Summary

| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python 3.12, FastAPI, Uvicorn, WebSockets, Pydantic v2 |
| **Data Engine** | In-memory rolling store, statistical volatility & volume baselines |
| **AI Layer** | Local Ollama (`llama3.2`), Cloud Gemini / Groq, Deterministic Rule Fallback |
| **Frontend** | React 18, Vite, Obsidian Dark Glassmorphism, Lucide Icons |
| **Styling** | Pure Vanilla CSS Design System |
| **Containerization** | Unified Multi-stage Dockerfile (Node build + FastAPI serve) |
| **Quality & Tests** | Pytest (38 passing unit & integration tests) |
