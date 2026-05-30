# Amadeus-chat: Local LLM CLI with Hybrid RAG, Tool Execution & System Awareness

> **Note:** This is a side branch of the main [Amadeus-AI](https://github.com/adityatawde9699/Amadeus-AI) project. While the main Amadeus-AI is fully autonomous, **Amadeus-chat** is designed as a non-autonomous, local CLI chat interface for manual interactions, RAG-based document querying, and safe system tool execution.

A powerful, entirely local Command-Line Interface (CLI) for running quantized LLMs securely on your machine. Amadeus features advanced Hybrid RAG (BM25 + Semantic + RRF fusion), smart memory compression, live system awareness via `psutil`, and a safe whitelisted shell tool execution pipeline — all within a single Python file.

---

## ✨ Features

### 🔒 100% Local & Private
Runs entirely on-device using `llama-cpp-python`. No data is ever sent to external APIs.

### 🔍 Advanced Hybrid RAG
- Ingests **PDF, Markdown, CSV, JSON, HTML, TXT, RST, and Python** files.
- **Recursive chunking** with word-aligned overlap to prevent mid-word fragment corruption.
- **BM25 (keyword)** + **Semantic (Sentence Transformers)** search combined via **Reciprocal Rank Fusion (RRF)** — no fragile linear weighting needed.
- **Cross-encoder re-ranking** filters out irrelevant context before injecting into the prompt.
- **Duplicate detection** via MD5 hash prevents double-indexing the same file.
- **Persistent index** save/load via `/index save|load <path>`.

### 🧠 Smart Memory Management
- **Sliding window** retains the most recent turns verbatim.
- **LLM-powered summarization** compresses older turns to a rolling summary, staying within token budget.
- **Token budget guard** warns at 80% and hard-blocks at 95% of the context window.

### 🛠️ Safe Tool Execution
Amadeus can call tools to interact with your system:
- **Shell Tool** — Runs whitelisted commands (e.g., `ls`, `find`, `git`, `python3`). Blocked patterns prevent destructive operations (`rm -rf`, `sudo`, `mkfs`, etc.). Use `/approve` to force-run a blocked command.
- **Sysinfo Tool** — Reads CPU %, RAM, disk usage, battery status, and top processes via `psutil`.

### 🧹 Chain-of-Thought Filtering
A streaming `ThinkFilter` strips `<think>...</think>` blocks in real time, ensuring the model never leaks internal reasoning to the user.

### ⚙️ Runtime Configuration
Change any config value live with `/set <key> <value>` — no restart required.

### 📊 Rich Terminal UI
Beautifully formatted output using the `rich` library: markdown rendering, tables, progress bars, and inline benchmark stats after every turn.

---

## 🚀 Installation

This project uses [uv](https://github.com/astral-sh/uv) as its package manager.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/adityatawde9699/Amadeus-chat.git
   cd Amadeus-chat
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```
   *(Or activate manually: `source .venv/bin/activate`)*

3. **Optional PDF support:**
   ```bash
   uv pip install pypdf
   ```

---

## 📥 Downloading a Model

Before chatting you need a quantized `.gguf` model. The project ships configured for **Qwen3.5-2B Q4_K_M**.

1. Edit `.env` to point at any model on Hugging Face:
   ```env
   HF_REPO_ID="Jackrong/Qwen3.5-2B-Claude-4.6-Opus-Reasoning-Distilled-GGUF"
   HF_FILENAME="Qwen3.5-2B.Q4_K_M.gguf"
   ```

2. Run the download script:
   ```bash
   uv run download_model.py
   ```
   The model is saved into the `Models/` directory.

---

## 💬 Usage

Start with the default model (set in `Config`):
```bash
uv run chat.py
```

Or override any parameter via CLI flags:
```bash
uv run chat.py --model ./Models/my-model.Q4_K_M.gguf --ctx 8192 --gpu-layers 35
```

Pre-load a document into RAG at startup:
```bash
uv run chat.py --load ./notes.pdf --load ./README.md
```

Override the system prompt:
```bash
uv run chat.py --system "You are a Python expert. Be terse."
```

---

## 🖥️ CLI Flags

| Flag | Default | Description |
|---|---|---|
| `--model` | `Models/Qwen3.5-2B.Q4_K_M.gguf` | Path to `.gguf` model file |
| `--ctx` | `8192` | Context window size (tokens) |
| `--max-tokens` | `4096` | Max tokens per response |
| `--temperature` | `0.78` | Sampling temperature |
| `--gpu-layers` | `0` | Layers to offload to GPU |
| `--threads` | `4` | CPU inference threads |
| `--embed-model` | `all-MiniLM-L6-v2` | SentenceTransformer for embeddings |
| `--rerank-model` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | CrossEncoder for re-ranking |
| `--alpha` | `0.55` | Hybrid weight (ignored when using RRF) |
| `--no-rrf` | `False` | Use linear hybrid instead of RRF |
| `--memory-turns` | `12` | Turns before memory compression triggers |
| `--score-threshold` | `-5.0` | Min cross-encoder score to include a chunk |
| `--load` | — | Pre-load a file into RAG (repeatable) |
| `--load-index` | — | Pre-load a saved RAG index directory |
| `--system` | — | Override the default system prompt |
| `--no-auto-save` | `False` | Disable auto-save on exit |
| `--log-level` | `WARNING` | Logging verbosity (`DEBUG`/`INFO`/`WARNING`/`ERROR`) |

---

## ⌨️ In-Chat Commands

| Command | Description |
|---|---|
| `/help` | Show all available commands |
| `/load <file>` | Index a document into RAG (PDF/MD/TXT/PY/JSON/CSV/HTML) |
| `/docs` | List all currently indexed documents |
| `/rag on\|off` | Toggle RAG context injection |
| `/rag clear` | Wipe the vector store and BM25 index |
| `/index save <path>` | Save the RAG index to disk |
| `/index load <path>` | Load a previously saved RAG index |
| `/model <path>` | Hot-swap the LLM without restarting |
| `/memory` | Show conversation state and rolling summary |
| `/clear` | Clear conversation history (keeps RAG index) |
| `/history` | Print the full conversation |
| `/run <command>` | Execute a shell command (safety-checked) |
| `/sysinfo` | Show CPU, RAM, disk, and battery usage |
| `/approve` | Force-run the last blocked shell command |
| `/set <key> <value>` | Change any config value at runtime |
| `/config` | Show current configuration |
| `/bench` | Show per-turn benchmark stats |
| `/save` | Save chat history to `chat_history.json` |
| `/export` | Export conversation to `chat_export.md` |
| `/quit` | Exit gracefully and auto-save |

---

## ⚙️ Architecture

| Component | Detail |
|---|---|
| **LLM Backend** | `llama-cpp-python` — 4-bit GGUF quantization |
| **Embedder** | `all-MiniLM-L6-v2` (fast, lightweight) |
| **Re-ranker** | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| **RAG Fusion** | Reciprocal Rank Fusion (BM25 + cosine similarity) |
| **Vector Store** | Pure NumPy, pre-normalized matrix — O(1) query-time normalization |
| **BM25 Index** | Deferred rebuild — O(N) incremental adds |
| **Chunker** | 3-level recursive (paragraph → sentence → word), word-aligned overlap |
| **Memory** | Sliding window + LLM summarization + token budget guard |
| **Tools** | Whitelisted shell executor + psutil sysinfo |
| **CoT Filter** | Streaming `ThinkFilter` strips `<think>...</think>` in real time |
| **System Info** | `psutil` — CPU, RAM, disk, battery, top processes |
