"""
Configuration loader for Amadeus.

Reads ``~/.amadeus/config.toml`` (creating a sensible default on first run)
and exposes a typed :class:`Config` object to the rest of the package.

The config file is intentionally minimal — Amadeus is *deterministic-first*,
so most behaviour is hard-coded and the config only stores user-tunable
preferences (project paths, model path, git auto-stage, etc.).
"""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


DEFAULT_AMADEUS_HOME = Path.home() / ".amadeus"
DEFAULT_CONFIG_PATH = DEFAULT_AMADEUS_HOME / "config.toml"


# The default config TOML written on first run.  Keep it human-readable —
# users will edit this file by hand.
DEFAULT_CONFIG_TOML = """\
# ── Amadeus configuration ──────────────────────────────────────────────
# Edit this file by hand; Amadeus will not overwrite it once it exists.

[user]
name = "Amadeus User"

[paths]
# Project roots that `amadeus start` will scan for git repositories.
projects = []

[model]
# Path to a .gguf model used by the lazy LLM wrapper (utils.llm).
# Leave empty to disable LLM features (git commit / research summarise).
path = ""
# llama-cpp-python kwargs — kept minimal for 4GB-RAM machines.
n_ctx = 2048
n_threads = 0   # 0 = auto-detect physical cores
n_batch = 256
max_tokens = 384
temperature = 0.4

[git]
# If true, `amadeus git commit` will run `git add -A` before committing.
auto_stage = true
# Conventional-commit type used when the LLM is unavailable.
default_type = "chore"

[research]
# Maximum web pages to fetch per `amadeus research` invocation.
max_pages = 5
# Per-page fetch timeout (seconds).
fetch_timeout = 15
# User-Agent sent to remote servers.
user_agent = "Mozilla/5.0 (compatible; Amadeus-Research/1.0)"

[sys]
# Below this many MB of free RAM, `amadeus start` will print a yellow warning.
ram_warn_mb = 800
# Below this many GB of free disk, `amadeus start` will print a yellow warning.
disk_warn_gb = 5
# Paths cleaned by `amadeus sys clean` (must be safe to delete — see sysadmin.py).
clean_targets = [
    "/var/cache/apt/archives",
    "/tmp/amadeus",
]
"""


@dataclass
class ModelConfig:
    path: str = ""
    n_ctx: int = 2048
    n_threads: int = 0
    n_batch: int = 256
    max_tokens: int = 384
    temperature: float = 0.4


@dataclass
class GitConfig:
    auto_stage: bool = True
    default_type: str = "chore"


@dataclass
class ResearchConfig:
    max_pages: int = 5
    fetch_timeout: int = 15
    user_agent: str = "Mozilla/5.0 (compatible; Amadeus-Research/1.0)"


@dataclass
class SysConfig:
    ram_warn_mb: int = 800
    disk_warn_gb: int = 5
    clean_targets: list[str] = field(
        default_factory=lambda: [
            "/var/cache/apt/archives",
            "/tmp/amadeus",
        ]
    )


@dataclass
class Config:
    amadeus_home: Path = DEFAULT_AMADEUS_HOME
    user_name: str = "Amadeus User"
    project_paths: list[str] = field(default_factory=list)
    model: ModelConfig = field(default_factory=ModelConfig)
    git: GitConfig = field(default_factory=GitConfig)
    research: ResearchConfig = field(default_factory=ResearchConfig)
    sys: SysConfig = field(default_factory=SysConfig)

    # ── derived paths ──────────────────────────────────────────────
    @property
    def config_path(self) -> Path:
        return self.amadeus_home / "config.toml"

    @property
    def tasks_path(self) -> Path:
        return self.amadeus_home / "tasks.json"

    @property
    def knowledge_base_dir(self) -> Path:
        return self.amadeus_home / "knowledge_base"

    @property
    def research_dir(self) -> Path:
        return self.amadeus_home / "research"

    @property
    def indexes_dir(self) -> Path:
        return self.amadeus_home / "indexes"


# ── loading / writing ──────────────────────────────────────────────────

def ensure_amadeus_home(path: Path | None = None) -> Path:
    """Create the ``~/.amadeus`` directory tree if it does not exist.

    Returns the path to the home directory.  Idempotent.
    """
    home = path or DEFAULT_AMADEUS_HOME
    home.mkdir(parents=True, exist_ok=True)
    (home / "knowledge_base").mkdir(exist_ok=True)
    (home / "research").mkdir(exist_ok=True)
    (home / "indexes").mkdir(exist_ok=True)
    if not (home / "config.toml").exists():
        (home / "config.toml").write_text(DEFAULT_CONFIG_TOML, encoding="utf-8")
    if not (home / "tasks.json").exists():
        (home / "tasks.json").write_text('{"tasks": []}', encoding="utf-8")
    return home


def _discover_model(explicit: str, home: Path) -> str:
    """Resolve the GGUF model path.

    Resolution order (first hit wins):
      1. An explicit ``path`` set in config.toml.
      2. The ``$AMADEUS_MODEL_PATH`` environment variable.
      3. The first ``*.gguf`` found in ``<home>/models/``.

    Returns the explicit value unchanged when nothing is auto-discovered, so a
    "file missing" warning is still surfaced downstream.  Keeps the code
    portable: no absolute paths are hard-coded.
    """
    if explicit and os.path.isfile(explicit):
        return explicit

    env = os.environ.get("AMADEUS_MODEL_PATH", "").strip()
    if env and os.path.isfile(env):
        return env

    models_dir = home / "models"
    if models_dir.is_dir():
        ggufs = sorted(models_dir.glob("*.gguf"))
        if ggufs:
            return str(ggufs[0])

    return explicit


def _coerce_model(d: dict[str, Any]) -> ModelConfig:
    return ModelConfig(
        path=str(d.get("path", "")),
        n_ctx=int(d.get("n_ctx", 2048)),
        n_threads=int(d.get("n_threads", 0)),
        n_batch=int(d.get("n_batch", 256)),
        max_tokens=int(d.get("max_tokens", 384)),
        temperature=float(d.get("temperature", 0.4)),
    )


def _coerce_git(d: dict[str, Any]) -> GitConfig:
    return GitConfig(
        auto_stage=bool(d.get("auto_stage", True)),
        default_type=str(d.get("default_type", "chore")),
    )


def _coerce_research(d: dict[str, Any]) -> ResearchConfig:
    return ResearchConfig(
        max_pages=int(d.get("max_pages", 5)),
        fetch_timeout=int(d.get("fetch_timeout", 15)),
        user_agent=str(d.get("user_agent", ResearchConfig().user_agent)),
    )


def _coerce_sys(d: dict[str, Any]) -> SysConfig:
    return SysConfig(
        ram_warn_mb=int(d.get("ram_warn_mb", 800)),
        disk_warn_gb=int(d.get("disk_warn_gb", 5)),
        clean_targets=list(d.get("clean_targets", SysConfig().clean_targets)),
    )


def load_config(path: Path | None = None) -> Config:
    """Load the Amadeus config, creating defaults if absent."""
    home = ensure_amadeus_home(path)
    cfg_path = home / "config.toml"
    with cfg_path.open("rb") as fh:
        raw = tomllib.load(fh)

    user = raw.get("user", {})
    paths = raw.get("paths", {})
    model = _coerce_model(raw.get("model", {}))
    model.path = _discover_model(model.path, home)
    git = _coerce_git(raw.get("git", {}))
    research = _coerce_research(raw.get("research", {}))
    sys_c = _coerce_sys(raw.get("sys", {}))

    return Config(
        amadeus_home=home,
        user_name=str(user.get("name", "Amadeus User")),
        project_paths=list(paths.get("projects", [])),
        model=model,
        git=git,
        research=research,
        sys=sys_c,
    )


def config_to_dict(cfg: Config) -> dict[str, Any]:
    """Serialise a Config back to a TOML-friendly dict (for `/config` view)."""
    return {
        "user": {"name": cfg.user_name},
        "paths": {"projects": cfg.project_paths},
        "model": asdict(cfg.model),
        "git": asdict(cfg.git),
        "research": asdict(cfg.research),
        "sys": asdict(cfg.sys),
    }


__all__ = [
    "Config",
    "ModelConfig",
    "GitConfig",
    "ResearchConfig",
    "SysConfig",
    "DEFAULT_AMADEUS_HOME",
    "DEFAULT_CONFIG_PATH",
    "ensure_amadeus_home",
    "load_config",
    "config_to_dict",
]
