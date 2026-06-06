from pathlib import Path

import pytest

from swarm.tools import SandboxError, build_file_tools


def _by_name(root: Path):
    return {t.name: t for t in build_file_tools(root)}


def test_write_then_read_roundtrip(tmp_path: Path):
    t = _by_name(tmp_path)
    t["write_file"].handler({"path": "a.txt", "content": "hello"})
    assert t["read_file"].handler({"path": "a.txt"}) == "hello"


def test_write_creates_parents(tmp_path: Path):
    t = _by_name(tmp_path)
    t["write_file"].handler({"path": "deep/nested/x.html", "content": "<html>"})
    assert (tmp_path / "deep" / "nested" / "x.html").exists()


def test_replace_unique(tmp_path: Path):
    (tmp_path / "f.txt").write_text("a = 1\nb = 2\n", encoding="utf-8")
    t = _by_name(tmp_path)
    msg = t["replace_in_file"].handler({"path": "f.txt", "old": "a = 1", "new": "a = 42"})
    assert "replaced" in msg
    assert (tmp_path / "f.txt").read_text() == "a = 42\nb = 2\n"


def test_replace_ambiguous(tmp_path: Path):
    (tmp_path / "f.txt").write_text("x\nx\n")
    t = _by_name(tmp_path)
    msg = t["replace_in_file"].handler({"path": "f.txt", "old": "x", "new": "y"})
    assert "matches 2 times" in msg


def test_list_dir_glob(tmp_path: Path):
    (tmp_path / "a.html").write_text("")
    (tmp_path / "b.js").write_text("")
    t = _by_name(tmp_path)
    out = t["list_dir"].handler({"path": ".", "pattern": "*.html"})
    assert "a.html" in out
    assert "b.js" not in out


def test_path_escape_blocked(tmp_path: Path):
    t = _by_name(tmp_path)
    with pytest.raises(SandboxError):
        t["read_file"].handler({"path": "../etc/passwd"})


def test_missing_file_returns_friendly(tmp_path: Path):
    t = _by_name(tmp_path)
    out = t["read_file"].handler({"path": "nope.txt"})
    assert "not found" in out
