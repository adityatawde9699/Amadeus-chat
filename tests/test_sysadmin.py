"""Sysadmin: target allow-list, byte formatting, dry-run safety."""
from __future__ import annotations

import types

from amadeus.core.config import Config, SysConfig
from amadeus.modules import sysadmin


def test_classify_target_allowlist():
    assert sysadmin._classify_target("/var/cache/apt/archives") == "apt-archives"
    assert sysadmin._classify_target("/var/cache/apt/archives/") == "apt-archives"
    assert sysadmin._classify_target("/tmp/amadeus") == "tmp-amadeus"
    assert sysadmin._classify_target("/var/log/journal") == "journal"
    assert sysadmin._classify_target("/home/user/important") == "unknown"


def test_bytes_human():
    assert sysadmin._bytes_human(0) == "0.0 B"
    assert sysadmin._bytes_human(1536) == "1.5 KB"
    assert sysadmin._bytes_human(1024 ** 3) == "1.0 GB"


def test_dry_run_deletes_nothing(tmp_path, monkeypatch):
    # Point the tmp-amadeus cleaner at a populated temp dir.
    target = tmp_path / "amadeus-tmp"
    target.mkdir()
    (target / "junk.bin").write_bytes(b"x" * 100)
    monkeypatch.setattr(sysadmin, "_TMP_AMADEUS_RE", str(target))
    monkeypatch.setattr(sysadmin, "_CLEANERS",
                        {"tmp-amadeus": sysadmin._clean_tmp_amadeus})
    monkeypatch.setattr(sysadmin, "_classify_target", lambda p: "tmp-amadeus")

    cfg = Config(sys=SysConfig(clean_targets=[str(target)]))
    args = types.SimpleNamespace(dry_run=True)
    assert sysadmin.cmd_clean(cfg, args) == 0
    # Nothing was deleted.
    assert (target / "junk.bin").exists()


def test_real_clean_removes_files(tmp_path, monkeypatch):
    target = tmp_path / "amadeus-tmp"
    target.mkdir()
    (target / "junk.bin").write_bytes(b"x" * 100)
    monkeypatch.setattr(sysadmin, "_TMP_AMADEUS_RE", str(target))

    freed, n = sysadmin._clean_tmp_amadeus(dry_run=False)
    assert n == 1 and freed >= 100
    assert not (target / "junk.bin").exists()
