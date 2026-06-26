"""Config creation, reload, model discovery, malformed TOML."""
from __future__ import annotations

import pytest

from amadeus.core import config


def test_default_config_created(tmp_path):
    home = tmp_path / ".amadeus"
    cfg = config.load_config(home)
    assert (home / "config.toml").exists()
    assert (home / "tasks.json").exists()
    assert (home / "knowledge_base").is_dir()
    assert cfg.user_name == "Amadeus User"
    assert cfg.git.default_type == "chore"
    assert cfg.model.n_ctx == 2048


def test_config_to_dict_roundtrip_shape(tmp_path):
    cfg = config.load_config(tmp_path / ".amadeus")
    d = config.config_to_dict(cfg)
    assert set(d) == {"user", "paths", "model", "git", "research", "sys"}
    assert d["model"]["n_ctx"] == 2048


def test_malformed_toml_raises(tmp_path):
    home = config.ensure_amadeus_home(tmp_path / ".amadeus")
    (home / "config.toml").write_text("this is = = not valid toml", encoding="utf-8")
    with pytest.raises(Exception):
        config.load_config(home)


def test_discover_model_prefers_explicit(tmp_path):
    home = tmp_path / ".amadeus"
    home.mkdir()
    real = tmp_path / "explicit.gguf"
    real.write_bytes(b"x")
    assert config._discover_model(str(real), home) == str(real)


def test_discover_model_from_models_dir(tmp_path):
    home = tmp_path / ".amadeus"
    (home / "models").mkdir(parents=True)
    gguf = home / "models" / "a-model.gguf"
    gguf.write_bytes(b"x")
    assert config._discover_model("", home) == str(gguf)


def test_discover_model_env_var(tmp_path, monkeypatch):
    home = tmp_path / ".amadeus"
    home.mkdir()
    env_model = tmp_path / "env.gguf"
    env_model.write_bytes(b"x")
    monkeypatch.setenv("AMADEUS_MODEL_PATH", str(env_model))
    assert config._discover_model("", home) == str(env_model)


def test_discover_model_none_found(tmp_path, monkeypatch):
    monkeypatch.delenv("AMADEUS_MODEL_PATH", raising=False)
    home = tmp_path / ".amadeus"
    home.mkdir()
    assert config._discover_model("", home) == ""
