# agent-swarm

A small team of LLM agents that builds a single-page web app from a one-line goal. Five roles, written against the Anthropic SDK directly with no agent framework in between.

| Agent | Model | Role |
|---|---|---|
| PM | Opus | Plans the work, picks who speaks next via a `choose_next` tool call |
| Designer | Sonnet | ASCII wireframe + a few UX bullets |
| Engineer | Sonnet | Reads/writes/edits files in a sandboxed project folder |
| QA | Sonnet (Vision) | Takes a screenshot of the running page and judges if it works |
| Critic | Opus | Reads the code, looks at the screenshot summary, decides APPROVE or REQUEST_FIX |

The orchestrator runs in rounds: each non-PM agent speaks, then the PM picks the next speaker. The loop ends when the Critic approves or after `--max-rounds` rounds.

## Run

```bash
uv sync
uv run playwright install chromium
cp .env.example .env  # add ANTHROPIC_API_KEY

uv run swarm build "Snake game in vanilla HTML/JS"
```

The output lands under `./output/<slug>/`:

```
output/snake-game-in-vanilla-html-js/
  index.html
  game.js
  conversation.md       # full transcript
  artifacts/qa-001.png  # screenshots from QA rounds
  artifacts/qa-002.png
```

You open `index.html` in a browser to see the result.

## Architecture

```
swarm build "<goal>"
   |
   v
Orchestrator  ── round loop, max 8 rounds, terminate on APPROVE
   |
   ├── Channel ── shared message history every agent reads
   |
   ├── PM       ── choose_next: Designer | Engineer | QA | Critic | DONE
   ├── Designer ── ASCII wireframe
   ├── Engineer ── read_file, write_file, replace_in_file, list_dir
   ├── QA       ── http.server + Playwright + Vision verdict
   └── Critic   ── read_file + decide: APPROVE | REQUEST_FIX
```

Two pieces that I want to call out:

**PM uses a tool, not free text, to pick the next speaker.** The `choose_next` schema has `next: enum["Designer","Engineer","QA","Critic","DONE"]` and a `reason`. The orchestrator never parses prose; it reads `next` directly off the tool call. Cuts a whole category of bugs.

**QA is a Vision turn, not a text turn.** After the Engineer writes files, the orchestrator starts a local `http.server` against the workdir, points headless Chromium at it, takes a screenshot, and feeds the PNG to Sonnet with the goal as context. The verdict comes back as `works | partial | broken`. The Critic then looks at the verdict, reads the code, and decides whether to accept or send the Engineer back.

## Sandboxing

Every file tool resolves paths under the project folder and refuses anything that escapes. The static server only serves the project folder. The headless browser only opens `http://127.0.0.1:<random-port>/`. There is no shell tool: the Engineer cannot run arbitrary commands.

## Layout

```
src/swarm/
  cli.py           argparse entry
  orchestrator.py  round loop, agent wiring
  channel.py       shared message history
  render.py        rich panels per agent turn
  costs.py         multi-model token tracking
  tools.py         sandboxed read/write/replace/list
  browser.py       Playwright in a worker thread
  server.py        tiny local static server
  agents/
    base.py
    pm.py        choose_next tool
    designer.py
    engineer.py  file tool loop
    qa.py        vision over screenshots
    critic.py    decide tool
```

## Why no LangGraph or CrewAI

Those frameworks ship the exact pattern this repo implements. Writing it from scratch is ~700 lines of Python, every part is direct, and you get to see how a swarm actually wires up. If you swap in a framework later, you'll know what it's doing under the hood.

## Limits

- Goal has to be a single-page static web app. The Engineer's tools can write anything but the QA loop assumes `index.html` exists at the project root.
- The Critic does not verify behavior, only that the screenshot looks reasonable and the code is sane. Logic bugs that don't surface in a screenshot can survive.
- Rate of progress depends entirely on Opus picking sensible next speakers. Bad picks waste rounds.

## License

MIT.
