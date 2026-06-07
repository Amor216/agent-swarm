from pathlib import Path

from swarm.validator import validate


def test_clean_project_has_no_issues(tmp_path: Path):
    (tmp_path / "index.html").write_text(
        "<!doctype html><html><head><title>x</title></head><body><p>hi</p></body></html>",
        encoding="utf-8",
    )
    (tmp_path / "game.js").write_text(
        "function add(a, b) { return a + b; }\nconsole.log(add(1, 2));\n",
        encoding="utf-8",
    )
    assert validate(tmp_path) == []


def test_unclosed_html_tag_flagged(tmp_path: Path):
    (tmp_path / "index.html").write_text(
        "<html><body><div><p>oops</body></html>", encoding="utf-8",
    )
    issues = validate(tmp_path)
    assert any("unclosed" in i.message or "out-of-order" in i.message for i in issues)


def test_unbalanced_braces_in_js(tmp_path: Path):
    (tmp_path / "broken.js").write_text("function f() { return 1\n", encoding="utf-8")
    issues = validate(tmp_path)
    assert any("unbalanced" in i.message for i in issues)


def test_unterminated_string_in_js(tmp_path: Path):
    (tmp_path / "s.js").write_text('const a = "hello\n', encoding="utf-8")
    issues = validate(tmp_path)
    assert any("unterminated string" in i.message for i in issues)


def test_skip_node_modules_and_artifacts(tmp_path: Path):
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "bad.js").write_text("function f() { ", encoding="utf-8")
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts" / "bad.html").write_text("<div>", encoding="utf-8")
    assert validate(tmp_path) == []


def test_comments_and_strings_ignore_delimiters(tmp_path: Path):
    (tmp_path / "ok.js").write_text(
        "// a } close in a comment\n"
        "/* and a ( in a block */\n"
        'const s = "a } b ( c";\n'
        "function f() { return s; }\n",
        encoding="utf-8",
    )
    assert validate(tmp_path) == []
