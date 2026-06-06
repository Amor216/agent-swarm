import fnmatch
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

MAX_READ_BYTES = 200_000


class SandboxError(RuntimeError):
    pass


def _safe(root: Path, raw: str) -> Path:
    p = (root / raw).resolve()
    try:
        p.relative_to(root.resolve())
    except ValueError:
        raise SandboxError(f"path escapes sandbox: {raw}") from None
    return p


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    handler: Callable[[dict], str]

    def schema(self) -> dict:
        return {"name": self.name, "description": self.description, "input_schema": self.input_schema}


def build_file_tools(root: Path) -> list[Tool]:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)

    def read_file(args: dict) -> str:
        p = _safe(root, args["path"])
        if not p.exists():
            return f"not found: {args['path']}"
        if not p.is_file():
            return f"not a file: {args['path']}"
        data = p.read_bytes()[:MAX_READ_BYTES]
        return data.decode("utf-8", errors="replace")

    def write_file(args: dict) -> str:
        p = _safe(root, args["path"])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(args["content"], encoding="utf-8")
        return f"wrote {args['path']} ({len(args['content'])} bytes)"

    def replace_in_file(args: dict) -> str:
        p = _safe(root, args["path"])
        if not p.exists():
            return f"not found: {args['path']}"
        text = p.read_text(encoding="utf-8")
        old, new = args["old"], args["new"]
        n = text.count(old)
        if n == 0:
            return f"no match for old in {args['path']}"
        if n > 1:
            return f"old matches {n} times, refine it"
        p.write_text(text.replace(old, new), encoding="utf-8")
        return f"replaced 1 occurrence in {args['path']}"

    def list_dir(args: dict) -> str:
        p = _safe(root, args.get("path") or ".")
        if not p.is_dir():
            return f"not a directory: {args.get('path')}"
        pat = args.get("pattern")
        out = []
        for e in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if pat and not fnmatch.fnmatch(e.name, pat):
                continue
            out.append(("d " if e.is_dir() else "f ") + e.name)
        return "\n".join(out) or "(empty)"

    return [
        Tool("read_file", "Read a text file under the project root.",
             {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
             read_file),
        Tool("write_file", "Write a file under the project root, creating parents.",
             {"type": "object",
              "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
              "required": ["path", "content"]},
             write_file),
        Tool("replace_in_file",
             "Replace exactly one occurrence of `old` with `new`. Fails on 0 or >1 matches.",
             {"type": "object",
              "properties": {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}},
              "required": ["path", "old", "new"]},
             replace_in_file),
        Tool("list_dir", "List entries under a directory, optional glob.",
             {"type": "object",
              "properties": {"path": {"type": "string"}, "pattern": {"type": "string"}}},
             list_dir),
    ]
