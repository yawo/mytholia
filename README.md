# GraphOdyssée

An interactive mythology knowledge-graph explorer. This is a **GraphRAG** app: retrieval happens over a knowledge graph (not just vector chunks), and generation is grounded in the retrieved subgraph.

**Core loop:**

1. Pick a **corpus** (Greek Odyssey, Egyptian mythology, Vodou, Hindu mythology, Catholic saints, …).
2. Click a node (e.g. a character) and see its local subgraph — relations, events, timeline.
3. Click **"Generate Podcast"** and get ~3 minutes of narrated audio summarizing that entity's story from graph facts.

## The one rule that matters: corpus agnosticism

The product is a **generic mythology/knowledge-graph engine** that ships with Greek mythology as the first seeded corpus. Egyptian mythology, Vodou, Hindu mythology, and the Catholic saints are equally first-class corpora.

- **No corpus name, entity type, deity name, or relation label is ever hardcoded** in pipeline, API, or frontend code.
- Every corpus is defined by a **manifest** (`corpora/<corpus_id>/manifest.yaml`), not a bespoke script.
- Adding a corpus = write a manifest + maybe a prompt override. It never means forking the pipeline.

See [`AGENTS.md`](./AGENTS.md) for the full specification.

## Layout

```
graphodyssee/
├── corpora/          # one manifest (+ optional prompt override) per corpus
├── pipeline/         # scrape → extract → build_graph, driven by corpus_loader.py
├── api/              # FastAPI backend (routers, retrieval, generation)
├── frontend/         # React + TypeScript app
├── data/             # cached raw text + processed graph.json (gitignored)
└── tests/            # fixtures for Greek AND Egyptian corpora (both required)
```

## Setup & commands

### Backend

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

### Build a corpus from its manifest

```bash
python pipeline/corpus_loader.py --corpus greek-odyssey
python pipeline/corpus_loader.py --corpus egyptian-mythology
python pipeline/corpus_loader.py --list    # list available corpora
```

This writes `data/processed/<corpus_id>/graph.json`.

### Tests

```bash
pytest tests/ -v
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Lint / format

```bash
ruff check . && ruff format .
cd frontend && npm run lint
```

## Data model

Nodes use a fixed, corpus-agnostic type set: `Character`, `Place`, `Object`, `Event`, `Concept` — chosen to cover a god, a pharaoh, a loa, or a saint without modification.

Relations use an open vocabulary with a controlled list per corpus manifest (`CHILD_OF`, `SPOUSE_OF`, `FOUGHT`, …).

Every node and edge carries a `source_refs` entry — **mandatory traceability** to a source passage. No invented mythology: if a generation step can't ground a claim in `source_refs`, it omits the claim.

## Tech stack

| Layer | Choice |
|---|---|
| Scraping | crawl4AI, Scrapling (optional in Sprint 0) |
| Search augmentation | Tavily, Perplexity Sonar (optional) |
| Extraction | Claude structured JSON (deterministic offline fallback in Sprint 0) |
| Graph store (V1) | NetworkX + `graph.json` (ships first, zero infra) |
| Graph store (V2) | FalkorDB (default) or Memgraph — openCypher |
| Vector store | Qdrant (later sprint) |
| Backend | Python, FastAPI |
| Frontend | React + TypeScript |
| TTS | ElevenLabs (primary) or Qwen TTS (local fallback) |

## Environment

Copy `.env.example` to `.env` and fill in keys as needed. Sprint 0 runs fully offline without any API keys.
