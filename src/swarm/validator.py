from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}


@dataclass(frozen=True)
class Issue:
    file: str
    message: str


def validate(workdir: Path) -> list[Issue]:
    issues: list[Issue] = []
    for path in sorted(workdir.rglob("*.html")):
        if _is_ignored(path):
            continue
        issues.extend(_check_html(path))
    for path in sorted(workdir.rglob("*.js")):
        if _is_ignored(path):
            continue
        issues.extend(_check_js(path))
    return issues


def _is_ignored(path: Path) -> bool:
    return any(part in {"node_modules", ".git", "artifacts"} for part in path.parts)


def _check_html(path: Path) -> list[Issue]:
    text = _read(path)
    if text is None:
        return [Issue(str(path.name), "could not read as utf-8")]
    parser = _TagBalanceParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception as exc:
        return [Issue(str(path.name), f"html parse error: {exc}")]
    issues = [Issue(str(path.name), msg) for msg in parser.errors]
    if parser.stack:
        issues.append(Issue(str(path.name), f"unclosed tags: {', '.join(parser.stack)}"))
    return issues


def _check_js(path: Path) -> list[Issue]:
    text = _read(path)
    if text is None:
        return [Issue(str(path.name), "could not read as utf-8")]
    issues: list[Issue] = []
    line_no, parens, braces, brackets = 1, 0, 0, 0
    in_string: str | None = None
    in_line_comment = False
    in_block_comment = False
    i = 0
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if ch == "\n":
            line_no += 1
            in_line_comment = False
            i += 1
            continue
        if in_line_comment:
            i += 1
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue
        if in_string:
            if ch == "\\":
                i += 2
                continue
            if ch == in_string:
                in_string = None
            i += 1
            continue
        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue
        if ch in ("'", '"', "`"):
            in_string = ch
            i += 1
            continue
        if ch == "(": parens += 1
        elif ch == ")": parens -= 1
        elif ch == "{": braces += 1
        elif ch == "}": braces -= 1
        elif ch == "[": brackets += 1
        elif ch == "]": brackets -= 1
        if parens < 0 or braces < 0 or brackets < 0:
            issues.append(Issue(path.name, f"unmatched closer near line {line_no}"))
            return issues
        i += 1
    if in_string:
        issues.append(Issue(path.name, f"unterminated string ({in_string})"))
    if in_block_comment:
        issues.append(Issue(path.name, "unterminated block comment"))
    if parens or braces or brackets:
        issues.append(Issue(
            path.name,
            f"unbalanced delimiters: parens={parens}, braces={braces}, brackets={brackets}",
        ))
    return issues


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


class _TagBalanceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in VOID_TAGS:
            return
        self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID_TAGS:
            return
        if tag in self.stack:
            while self.stack and self.stack[-1] != tag:
                self.errors.append(f"out-of-order close: </{tag}>, expected </{self.stack[-1]}>")
                self.stack.pop()
            if self.stack:
                self.stack.pop()
        else:
            self.errors.append(f"close without open: </{tag}>")
