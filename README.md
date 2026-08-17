# GraphOdyssée

An interactive mythology knowledge-graph explorer. This is a **GraphRAG** app: retrieval happens over a knowledge graph (not just vector chunks), and generation is grounded in the retrieved subgraph.

**Core loop:**

1. Pick a **corpus** (Greek Odyssey, Egyptian mythology, Vodou, Hindu mythology, Catholic saints, …).
2. Click a node and see its local subgraph — relations, events, timeline.
3. Click **"Generate Podcast"** and get narrated audio/script grounded in graph facts.

## Single Python app

GraphOdyssée is now deployable as one FastAPI application. The Python app serves both:

- JSON API routes under `/api/*`.
- The bundled web UI from `app/static/` for `/` and non-API fallback routes.

The previous React/Vite frontend remains in `frontend/` as source/reference, but Vercel deployment no longer requires a separate Node frontend build.

## Layout

```
graphodyssee/
├── app/static/       # bundled browser UI served by FastAPI
├── api/              # FastAPI app, routers, retrieval, generation, Vercel entrypoint
├── corpora/          # one manifest (+ optional prompt override) per corpus
├── pipeline/         # scrape → extract → build_graph, driven by corpus_loader.py
├── data/             # cached raw text + processed graph.json (gitignored)
├── frontend/         # legacy React/Vite source/reference
└── tests/            # fixtures for Greek AND Egyptian corpora (both required)
```

## Local setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

Open `http://localhost:8000` for the UI and `http://localhost:8000/docs` for API docs.

## Vercel deployment

The repository includes `vercel.json` and `api/index.py`, so Vercel can route every request to the single Python FastAPI app.

Required Vercel settings:

1. Set the project root to this repository.
2. Add the environment variables from `.env.example` as needed.
3. Deploy. No frontend build command is required for the unified Python app.

## V1 and V2 graph stores

- V1/default: `GRAPH_STORE_BACKEND=networkx` reads `data/processed/<corpus_id>/graph.json`.
- V2-ready: set `GRAPH_STORE_BACKEND=falkordb` or `memgraph` plus `GRAPH_DB_URI`, `GRAPH_DB_NAME`, `GRAPH_DB_USER`, and `GRAPH_DB_PASSWORD` to select the openCypher store interface.

The V2 class is wired behind the same `GraphStore` interface so API routes do not need corpus-specific or backend-specific code.

## Build a corpus from its manifest

```bash
python pipeline/corpus_loader.py --corpus greek-odyssey
python pipeline/corpus_loader.py --corpus egyptian-mythology
python pipeline/corpus_loader.py --list
```

This writes `data/processed/<corpus_id>/graph.json`.

## Podcast voice defaults

Deepgram is the default TTS engine when `DEEPGRAM_API_KEY` is configured. French podcasts (`Accept-Language: fr` or the default locale) use Deepgram Aura 2 Agathe (`aura-2-agathe-fr`) by default; English podcasts keep `aura-asteria-en`. Override these with `DEEPGRAM_TTS_MODEL_FR` and `DEEPGRAM_TTS_MODEL` when needed.

## Tests and checks

```bash
pytest tests/ -v
ruff check .
ruff format .
```

## Corpus agnosticism

The product is a **generic mythology/knowledge-graph engine**. No corpus name, entity type, deity name, or relation label should be hardcoded in pipeline, API, or UI code. Every corpus is defined by a manifest under `corpora/<corpus_id>/manifest.yaml`.

Every node and edge carries `source_refs` for traceability. If a generation step cannot ground a claim in sources, it omits the claim.
