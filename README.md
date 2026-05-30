# Amadeus-chat: Local LLM CLI Chat with Hybrid RAG & Memory Guard

> **Note:** This is a side branch of the main [Amadeus-AI](https://github.com/adityatawde9699/Amadeus-AI) project. While the main Amadeus-AI is fully autonomous, **Amadeus-chat** is designed specifically as a non-autonomous, general-use CLI chat interface for manual interactions and RAG-based document querying.

A powerful, entirely local Command-Line Interface (CLI) for running large language models (LLMs) securely on your machine. It features an advanced Retrieval-Augmented Generation (RAG) system using Reciprocal Rank Fusion (RRF), automatic memory compression, and built-in model management.

## ✨ Features

- **100% Local Privacy:** Runs locally using `llama.cpp` (via `llama-cpp-python`). No data is sent to external APIs.
- **Advanced Hybrid RAG:** 
  - Ingests PDFs, Markdown, CSVs, JSON, and text files.
  - Recursive chunking with word-aligned overlap to prevent mid-word fragmentation.
  - Combines BM25 (keyword search) and Semantic Search (Sentence Transformers) using Reciprocal Rank Fusion (RRF).
  - Cross-encoder re-ranking filters out irrelevant context.
- **Smart Memory Guard:** Automatically summarizes older conversations to stay within the LLM's token budget while preserving verbatim recent history.
- **Easy Model Management:** Configurable script to safely download `.gguf` models directly from Hugging Face into a dedicated `Models/` folder.
- **Rich Terminal UI:** Beautifully formatted markdown, tables, and progress bars using the `rich` library.

---

## 🚀 Installation

This project uses [uv](https://github.com/astral-sh/uv) as its lightning-fast package manager.

1. **Clone the repository and enter the directory:**
   ```bash
   cd path/to/llama
   ```

2. **Initialize and install dependencies:**
   The `uv` package manager handles creating the virtual environment and installing all required packages (like `torch`, `llama-cpp-python`, `sentence-transformers`, etc.).
   ```bash
   uv sync
   ```
   *(Or activate the virtual environment manually: `source .venv/bin/activate`)*

---

## 📥 Downloading a Model

Before chatting, you need a model. We use quantized `.gguf` models (like Q4_K_M) for the best balance of speed and quality.

1. Open the `.env` file and set the repository and filename of the model you want to download from Hugging Face:
   ```env
   HF_REPO_ID="bartowski/gemma-2-9b-it-GGUF"
   HF_FILENAME="gemma-2-9b-it-Q4_K_M.gguf"
   ```

2. Run the download script:
   ```bash
   uv run download_model.py
   ```
   The model will be securely downloaded into the `Models/` directory.

---

## 💬 Usage

Start the chat application by pointing it to your downloaded model:

```bash
uv run chat.py --model ./Models/gemma-2-9b-it-Q4_K_M.gguf
```

*(You can also set `--ctx 8192` to increase the context window size if your hardware supports it).*

### In-Chat Commands

Once the chat is running, you can use the following commands:

- `/help` - Show all available commands.
- `/load <path/to/file>` - Ingest a document into the RAG vector store.
- `/docs` - List all currently indexed documents.
- `/rag on|off` - Toggle whether to inject document context into the LLM prompt.
- `/rag clear` - Wipe the vector store and BM25 index.
- `/model <path/to/model.gguf>` - Hot-swap the running LLM without restarting.
- `/memory` - View the current conversation state and the rolling summary.
- `/clear` - Clear the conversation history (keeps RAG index intact).
- `/bench` - Show performance benchmarking stats (Tokens/sec, Time to First Token).
- `/save` / `/export` - Save the raw history to JSON or export it as a Markdown file.
- `/quit` - Exit gracefully and auto-save the session.

---

## ⚙️ Architecture details

- **Embedder:** `all-MiniLM-L6-v2` (Fast and lightweight)
- **Re-ranker:** `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Vector Store:** Custom pure-NumPy pre-normalized matrix for O(1) query-time normalization.
- **RAG Fusion:** Uses RRF to combine sparse (BM25) and dense (Cosine Similarity) retrieval, avoiding sensitive linear weighting hyper-parameters.
