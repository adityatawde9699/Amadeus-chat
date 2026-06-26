# Glossary

Definitions of terms used throughout the Amadeus documentation. Cross-references
point to the most relevant in-depth page.

## A

**Amadeus** — This project: a deterministic-first, fire-and-forget CLI assistant
for low-RAM machines. The console command is `amadeus`; the distribution package
is `amadeus-chat`.

**Amadeus home** — The directory `~/.amadeus/` where all configuration and data
live. See [database.md](database.md).

**Allow-list** — The fixed set of cleanup categories that `amadeus sys clean` is
permitted to touch (`apt-archives`, `apt-lists`, `tmp-amadeus`, `journal`).
Anything else is skipped. See [security.md](security.md#system-cleanup).

**Atomic write** — Writing to a temporary file and `os.replace()`-ing it over the
target, so an interrupted write can never corrupt the original. Used for
`tasks.json` and index caches. See [database.md](database.md#durability--concurrency).

**Auto-discovery (model)** — Resolving the model path from config →
`$AMADEUS_MODEL_PATH` → `~/.amadeus/models/*.gguf`. See [ai.md](ai.md#model-discovery).

## B

**BM25 / BM25L** — A ranking function for full-text search. Amadeus uses the
**BM25L** variant (via `rank-bm25`) because it avoids the small-corpus IDF quirk
of plain BM25. Deterministic and dependency-light. See [caching.md](caching.md#why-bm25l-not-embeddings).

**Boilerplate stripping** — Removing non-content HTML (`<script>`, `<nav>`,
`<footer>`, …) during research text extraction. See [ai.md](ai.md) and
[security.md](security.md#web-research-untrusted-html).

## C

**Chat API / chat template** — The model interface (`LLMWrapper.chat`) that
applies a model's built-in conversation template. Required for correct instruct-
model output; preferred over raw completion. See [ai.md](ai.md#prompt-construction).

**Conventional Commits** — A commit-message convention (`type(scope): summary`)
that Amadeus follows and can generate. See [development.md](development.md#commit-conventions).

**Cold start** — The time to launch a fresh `amadeus` process and run a
deterministic command (~0.57 s measured). See [performance.md](performance.md).

## D

**Deterministic-first** — The core design principle: most functionality is plain,
repeatable Python; the LLM is optional and used only where generation helps. See
[architecture.md](architecture.md#design-principles-recap).

**Dry-run** — A mode (`sys clean --dry-run`) that reports what *would* happen
without making changes.

## F

**Fire-and-forget** — The execution model: each command starts, does one job,
prints, and exits, with no resident process. See [README](../README.md#overview).

## G

**GGUF** — The on-disk file format for quantized models used by `llama.cpp` /
`llama-cpp-python`. Amadeus loads a `.gguf` for LLM features. See [ai.md](ai.md).

## I

**Index cache** — `~/.amadeus/indexes/notes.json`, storing per-note MD5s and
tokens so unchanged notes are not re-tokenized on search. See [caching.md](caching.md#bm25-index-cache).

**Instruct model** — A model fine-tuned to follow instructions / chat. Preferred
for Amadeus because it ships a chat template. See [ai.md](ai.md#choosing-a-model).

## L

**Lazy loading** — Loading a resource only when needed. The LLM is lazy-loaded
inside `llm_session()` and released immediately after. See [ai.md](ai.md#lifecycle-load--use--release).

**`llm_session`** — The context manager in `amadeus/utils/llm.py` that loads the
model, yields a wrapper, and unloads on exit (with `gc.collect()`).

## M

**mmap** — Memory-mapping the model file so the OS page cache can keep it warm
across runs. Set via `use_mmap=True`. See [caching.md](caching.md#llm-weight-lifetime).

## N

**`n_ctx`** — The model's context window in tokens (default 2048). Bounds prompt
plus reply size. See [configuration.md](configuration.md#model).

**`/no_think`** — A directive appended to prompts to suppress a reasoning model's
chain-of-thought, yielding terse output. See [ai.md](ai.md#reasoning-models-qwen3-class).

## P

**Porcelain** — `git status --porcelain`, the stable machine-readable status
format Amadeus parses for `git status` and commit generation. See [cli.md](cli.md#amadeus-git).

## Q

**Quantization (Q4_K_M)** — Compressing model weights to ~4-bit to shrink memory
and disk use, at a small quality cost. The recommended size for low-RAM CPU
inference. See [ai.md](ai.md#choosing-a-model).

## R

**Reasoning model** — A model that emits a `<think>…</think>` chain-of-thought
before its answer (e.g. Qwen3-class). Amadeus strips this with `strip_think`. See
[ai.md](ai.md#reasoning-models-qwen3-class).

**RSS (Resident Set Size)** — The physical RAM a process holds. Amadeus keeps
deterministic-command RSS in the tens of MB. See [performance.md](performance.md).

## S

**Slug** — A filesystem-safe, kebab-case identifier derived from a title (e.g.
"Rust Ownership" → `rust-ownership`). Used for note filenames and research
directories. See [database.md](database.md).

**`strip_think`** — The helper that removes reasoning blocks (closed, leading, or
truncated) from model output. See [ai.md](ai.md#reasoning-models-qwen3-class).

**Stateless** — No persistent state between invocations beyond the files on disk;
each command is independent.

## T

**Tokenization** — Splitting note text into search tokens (lowercased, stopwords
and very short tokens removed) for BM25L. See [caching.md](caching.md).

## U

**`uv`** — A fast Python package and project manager used as the recommended
toolchain (`uv sync`, `uv run`, `uv lock`). See [installation.md](installation.md).

## See Also

- [architecture.md](architecture.md) — how these concepts fit together.
- [README](../README.md) — project overview.
