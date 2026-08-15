# AGENTS.md

Instructions for AI coding agents (Claude Code and others) working in this repository.

## 1. Project Overview

**GraphOdyssée** (working name) is an interactive mythology knowledge-graph explorer.

Core loop:
1. User picks a **corpus** (Odyssey, Iliad, Egyptian mythology, Vodou, Hindu mythology, Catholic saints, ...).
2. User clicks a node (e.g. "Odysseus") and sees its local subgraph — relations, events, timeline.
3. User clicks **"Generate Podcast"** and gets ~3 minutes of narrated audio, in a cloned voice, summarizing that entity's story from graph facts.

This is a **GraphRAG** app: retrieval happens over a knowledge graph (not just vector chunks), and generation is grounded in the retrieved subgraph.

## 2. The One Rule That Matters: Corpus Agnosticism

The product is not "an Odyssey app." It is a **generic mythology/knowledge-graph engine** that ships with Greek mythology as the first seeded corpus. Egyptian mythology, Vodou, Hindu mythology, and the Catholic saints are equally first-class corpora, not a "v2 stretch goal."

Concretely, this means:

- **No corpus name, entity type, deity name, or relation label is ever hardcoded** in pipeline, API, or frontend code. If you catch yourself writing `if character == "Zeus"` or a Greek-only enum, stop — that belongs in a corpus config, not code.
- Every corpus is defined by a **manifest** (see §5), not by a bespoke script. Adding a corpus should mean "write a manifest + maybe a prompt override," never "fork the pipeline."
- The extraction schema (node/edge types, §4) is deliberately abstract (`Character`, `Place`, `Object`, `Event`, `Concept`) so it covers a god, a pharaoh, a loa, or a saint without modification.
- **Definition of done for any pipeline/API change**: it must be validated against **at least two corpora** (Greek + one other, e.g. Egyptian) before being considered complete. A change that only has Greek test fixtures is not done — see §9.

If a requirement forces a Greek-only special case, raise it explicitly instead of quietly hardcoding it.

## 3. Repository Layout

```
graphodyssee/
├── AGENTS.md
├── README.md
├── corpora/                     # one manifest + prompt overrides per corpus
│   ├── greek-odyssey/
│   │   ├── manifest.yaml
│   │   └── extraction_prompt.md      # optional override of the default prompt
│   ├── greek-iliad/
│   ├── egyptian-mythology/
│   └── catholic-saints/
├── pipeline/                     # scrape -> extract -> graph.json (or graph DB load)
│   ├── scrape.py
│   ├── extract.py
│   ├── build_graph.py
│   └── corpus_loader.py          # reads a manifest, drives the above generically
├── api/                           # FastAPI backend
│   ├── main.py
│   ├── routers/
│   │   ├── graph.py               # /corpora, /graph, /character/{id}
│   │   └── podcast.py             # /podcast
│   ├── retrieval/
│   │   ├── graph_store.py         # NetworkX (V1) or FalkorDB/Memgraph (V2) — same interface
│   │   └── hybrid_search.py       # vector + graph fusion, local reranker
│   ├── generation/
│   │   ├── narrative.py           # subgraph -> podcast-style script (Claude)
│   │   └── tts.py                 # script -> audio (ElevenLabs / Qwen TTS)
│   └── models.py                  # pydantic schemas shared with tests
├── frontend/                      # React app
│   └── src/
│       ├── components/GraphView/  # react-force-graph or Cytoscape.js
│       ├── components/Sidebar/    # bio, timeline, "Generate Podcast"
│       └── api/client.ts
├── data/
│   ├── raw/                       # cached scraped text, gitignored except .gitkeep
│   └── processed/{corpus_id}/graph.json
└── tests/
    ├── fixtures/greek/            # small known-good subgraph
    ├── fixtures/egyptian/         # second corpus fixture — required, see §9
    ├── test_pipeline.py
    ├── test_api.py
    └── test_frontend/
```

## 4. Data Model (Graph Schema)

**Node types** (fixed, corpus-agnostic):

| Type | Examples |
|---|---|
| `Character` | Odysseus, Anubis, Ganesh, a loa, a saint |
| `Place` | Ithaca, the Duat, a temple |
| `Object` | The bow of Odysseus, the Ankh |
| `Event` | The Trojan War, the weighing of the heart |
| `Concept` | Xenia (guest-friendship), Ma'at (cosmic order) |

**Relation types** (open vocabulary, but keep to a controlled list per corpus manifest so the frontend can render consistent legends): `CHILD_OF`, `SPOUSE_OF`, `FOUGHT`, `MET`, `TOOK_PLACE_AT`, `WORSHIPPED_AS`, `GUARDS`, `TRANSFORMED_INTO`, etc.

Every node and edge carries:
```json
{
  "id": "char_odysseus",
  "type": "Character",
  "corpus_id": "greek-odyssey",
  "label": "Odysseus",
  "summary": "...",
  "source_refs": [{"text": "Odyssey", "book": 9, "line_range": "105-115"}]
}
```
`corpus_id` and `source_refs` are **mandatory**, not optional — every extracted fact must be traceable back to a passage. Claude should never emit a node/edge without a `source_refs` entry (see §10, "no invented mythology").

## 5. Corpus Configuration System

A new corpus is added by dropping a folder under `corpora/<corpus_id>/manifest.yaml`:

```yaml
id: egyptian-mythology
name: "Egyptian Mythology"
language: en
sources:
  - type: web_scrape
    tool: crawl4ai            # or scrapling
    seed_urls: ["https://..."]
  - type: search_augmented
    tool: tavily               # or perplexity_sonar
    queries: ["Osiris myth primary sources", "..."]
license_note: "Cite source per-passage; respect site ToS and robots.txt."
extraction:
  prompt_override: extraction_prompt.md   # optional; falls back to pipeline default
  node_type_hints: ["Character", "Place", "Object", "Event", "Concept"]
narrative_style:
  tone: "reverent, mythic narrator, not academic"
  length_seconds: 180
voice:
  provider: elevenlabs
  voice_id: "${GRAPHODYSSEE_DEFAULT_VOICE_ID}"
```

`corpus_loader.py` reads this and drives scrape → extract → build_graph without corpus-specific code paths. If a corpus genuinely needs different logic (e.g. oral-tradition sourcing for Vodou, where "primary text" doesn't mean the same thing as for the Odyssey), that logic lives behind an interface (`SourceStrategy`), and the manifest selects which implementation to use — it does not fork the pipeline file.

## 6. Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Scraping | crawl4AI, Scrapling | Perseus Digital Library (CC-licensed) as first source |
| Search augmentation | Tavily, Perplexity Sonar API | for corpora without a clean primary-text source |
| Extraction | Claude, structured JSON output | one prompt template + per-corpus overrides |
| Graph store (V1) | NetworkX + `graph.json` | ships first, zero infra |
| Graph store (V2) | FalkorDB (default) or Memgraph | both speak openCypher — no Neo4j dependency needed |
| Vector store | Qdrant | for hybrid search |
| Reranking | local cross-encoder (e.g. bge-reranker-v2-m3) | avoid a paid rerank API in the hot path |
| Backend | Python, FastAPI | |
| Frontend | React + TypeScript, react-force-graph (2D/3D) or Cytoscape.js | |
| TTS | ElevenLabs API (primary) or Qwen TTS (local/cheaper fallback) | both support the cloned-voice use case; pick one as default per §12 open decision |
| LLM (narrative generation) | Claude | same model family as extraction, different prompt |

**Note on the source brief:** the original notes mention both "FalkorDB or Memgraph" and, separately, "Neo4j Cypher." These aren't actually in conflict — FalkorDB and Memgraph both implement openCypher, so the retrieval code can be written once against Cypher-style queries and target either backend. There's no need for an actual Neo4j dependency. Defaulting to **FalkorDB** for consistency with other projects in this stack.

## 7. Setup & Commands

```bash
# Backend
cd api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev

# Pipeline — build a corpus from its manifest
python pipeline/corpus_loader.py --corpus greek-odyssey

# Tests
pytest tests/ -v
cd frontend && npm test

# Lint / format
ruff check . && ruff format .
cd frontend && npm run lint
```

## 8. Development Roadmap (Sprints)

| Sprint | Goal | Definition of done |
|---|---|---|
| 0 | Scaffolding | Repo layout above exists; one corpus manifest (`greek-odyssey`) committed; empty pipeline stages runnable end-to-end on a tiny fixture |
| 1 | Data pipeline | `corpus_loader.py --corpus greek-odyssey` produces `data/processed/greek-odyssey/graph.json` with ≥20 characters, sourced via manifest, **no hardcoded filenames or entity names in pipeline code** |
| 2 | API | FastAPI serves `/corpora`, `/graph?corpus_id=...`, `/character/{id}?corpus_id=...`; loads whichever store (`NetworkX` or `FalkorDB`) is configured via one interface |
| 3 | Frontend | React app lists corpora, renders the graph, click-to-fetch sidebar, calls the API — nothing about "Greek" or "Odyssey" is hardcoded in components (corpus is a route/query param) |
| 4 | Podcast | `/podcast` endpoint: subgraph → Claude narrative (respecting `narrative_style` from manifest) → TTS provider from manifest → returns audio URL/blob; loading state shown in UI |
| 5 | Genericity proof | Add a **second corpus** (Egyptian mythology recommended — best-documented alternative) end-to-end using only a new manifest + optional prompt override. If this requires touching pipeline/API/frontend code, sprint 1–4 broke the corpus-agnosticism rule and needs fixing before this sprint is called done |

## 9. Testing Instructions

- Backend: `pytest`, using `tests/fixtures/greek/` and `tests/fixtures/egyptian/` — **both fixtures are required**, not optional extras. Any PR touching `pipeline/` or `api/retrieval/` must pass tests against both.
- Frontend: component tests should mount `GraphView`/`Sidebar` with a fixture from each of the two corpora to catch accidental Greek-only assumptions (e.g. assuming every character has a "spouse" field).
- Add a regression test whenever a bug is fixed — don't just patch and move on.
- Run the full suite (`pytest && npm test`) before considering a sprint task complete.

## 10. Coding Conventions

- **Python**: type-hinted, `pydantic` models for all API request/response and graph node/edge shapes, formatted with `ruff format`, linted with `ruff check`.
- **TypeScript/React**: functional components, typed props, no `any`. Keep `GraphView` presentational; data fetching lives in `api/client.ts` hooks.
- **Naming**: corpus identifiers are always `kebab-case` (`greek-odyssey`, `egyptian-mythology`); node/edge `type` fields are always `PascalCase`/`SCREAMING_SNAKE_CASE` per §4.
- **No invented mythology**: any generation step (extraction or narrative) that can't ground a claim in `source_refs` should omit the claim rather than fill the gap. This is a correctness requirement, not a style preference — mythology corpora are exactly the domain where hallucinated "facts" are hard for a user to catch.
- **Commits**: small, one sprint-task per commit where practical; message states which corpus was used to validate the change.

## 11. Environment Variables

```
ANTHROPIC_API_KEY=
TAVILY_API_KEY=
PERPLEXITY_API_KEY=
ELEVENLABS_API_KEY=
QWEN_TTS_API_KEY=
QDRANT_URL=
GRAPH_DB_URI=            # FalkorDB/Memgraph connection string (V2 only)
GRAPHODYSSEE_DEFAULT_VOICE_ID=
```

Never commit real values. `.env.example` should list all of the above with empty values.

## 12. Scraping, Licensing & Voice-Cloning Considerations

- Respect `robots.txt` and rate-limit all scraping (crawl4AI/Scrapling configs, not ad-hoc sleeps). Cache raw scraped text under `data/raw/` so a corpus is never re-scraped unnecessarily.
- Perseus Digital Library content is CC-licensed — keep the `source_refs`/attribution fields populated so this holds for every corpus, not just the first one. Corpora with less clear licensing (e.g. some saints datasets) need a `license_note` in the manifest and a visible attribution in the UI.
- Voice cloning: the cloned voice used for narration needs documented consent/rights from whoever the voice belongs to. Store that separately from code (not in the repo), and treat `GRAPHODYSSEE_DEFAULT_VOICE_ID` as pointing to an already-authorized voice, not something to generate ad hoc.

## 13. Agent-Specific Instructions (Claude Code)

- Before writing pipeline, API, or frontend code, check whether the change would work unmodified for a second corpus. If not, redesign before implementing — don't ship the Greek-only version "for now."
- When adding a new corpus, touch only `corpora/<new>/` (manifest + optional prompt override) and its test fixture. If that's not sufficient, the abstraction in §5 needs fixing, not the new corpus special-cased.
- Cost control: ElevenLabs, Perplexity Sonar, and Tavily calls cost money per call. Don't call them in a loop while iterating/debugging — use cached fixtures or mocked responses in `tests/`, and confirm before running a real scrape/podcast-generation pass over a full corpus.
- Work in the sprint order in §8; don't start frontend work against an API contract that isn't implemented yet — stub the endpoint first if parallelizing.
- Run `pytest` and `npm test` (§9) before marking any task in a sprint as complete.

## 14. Open Decisions

These are flagged, not resolved — pick when you have a preference:

- **FalkorDB vs. Memgraph** for the V2 graph store (both fit; FalkorDB used elsewhere in this stack, so default to it unless there's a reason not to).
- **2D vs. 3D** force-graph rendering for the frontend.
- **ElevenLabs vs. Qwen TTS** as the shipped default (ElevenLabs: higher quality, paid, easiest voice cloning; Qwen TTS: cheaper/local, more setup).
- Whether `NetworkX` (V1) is retired once FalkorDB (V2) is stood up, or kept as a lightweight local-dev mode.
