import argparse
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console

from . import orchestrator, render

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

console = Console(legacy_windows=False, force_terminal=True)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = _parse(argv)

    slug = _slug(args.requirement)
    workdir = Path(args.out).expanduser().resolve() / slug

    console.print(f"[dim]project goal:[/dim] {args.requirement}")
    console.print(f"[dim]workdir:[/dim] {workdir}")
    console.print()

    result = orchestrator.run(
        requirement=args.requirement,
        workdir=workdir,
        max_rounds=args.max_rounds,
        on_turn=lambda t: render.panel(console, t),
        max_usd=args.max_budget,
        resume=args.resume,
    )

    console.print()
    if result.ok:
        console.print(f"[green]built in {result.rounds} round(s)[/green]")
    else:
        console.print(f"[yellow]gave up: {result.reason}[/yellow]")

    for line in result.cost.lines():
        console.print(f"[dim]{line}[/dim]")

    console.print()
    console.print(f"output: {result.workdir}")
    console.print(f"transcript: {result.workdir / 'conversation.md'}")
    console.print(f"artifacts: {result.workdir / 'artifacts'}")
    return 0 if result.ok else 1


def _parse(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="swarm",
                                description="Multi-agent software team that builds small apps")
    sub = p.add_subparsers(dest="action", required=True)
    b = sub.add_parser("build", help="run the swarm against a requirement")
    b.add_argument("requirement", help="natural language goal, e.g. 'Snake game in vanilla HTML/JS'")
    b.add_argument("--out", default="./output", help="output directory root")
    b.add_argument("--max-rounds", type=int, default=12, dest="max_rounds")
    b.add_argument("--max-budget", type=float, default=None, dest="max_budget",
                   help="abort if cumulative cost in USD exceeds this cap")
    b.add_argument("--resume", action="store_true",
                   help="continue an existing run in <out>/<slug>/ from its saved state.json")
    return p.parse_args(argv)


def _slug(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower())
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:40] or "project"


if __name__ == "__main__":
    sys.exit(main())
