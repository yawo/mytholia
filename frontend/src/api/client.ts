// API client + hooks (AGENTS.md §10: data fetching lives here, not in components).
// The corpus is always a param — nothing about "Greek" or "Odyssey" is hardcoded.

import { useEffect, useState } from "react";
import type {
  CorpusDetail,
  CorpusSummary,
  GraphData,
  GraphNode,
  GraphStats,
  PodcastEngine,
  PodcastResponse,
  TTSEnginesResponse,
  SearchResult,
} from "./types";

const API_BASE = "/api";

async function getJSON<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      url.searchParams.set(k, v);
    }
  }
  const res = await fetch(url.toString());
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status}: ${detail}`);
  }
  return (await res.json()) as T;
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status}: ${detail}`);
  }
  return (await res.json()) as T;
}

export function useCorpora(): { data: CorpusSummary[] | null; error: string | null; loading: boolean } {
  const [data, setData] = useState<CorpusSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    getJSON<CorpusSummary[]>("/corpora")
      .then((d) => {
        if (active) {
          setData(d);
          setError(null);
        }
      })
      .catch((e: unknown) => {
        if (active) setError(String(e));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);
  return { data, error, loading };
}

export function useGraph(corpusId: string | null): {
  data: GraphData | null;
  error: string | null;
  loading: boolean;
} {
  const [data, setData] = useState<GraphData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!corpusId) {
      setData(null);
      return;
    }
    let active = true;
    setLoading(true);
    getJSON<GraphData>("/graph", { corpus_id: corpusId })
      .then((d) => {
        if (active) {
          setData(d);
          setError(null);
        }
      })
      .catch((e: unknown) => {
        if (active) setError(String(e));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [corpusId]);
  return { data, error, loading };
}

export function useSubgraph(
  corpusId: string | null,
  nodeId: string | null,
  radius = 1
): { data: GraphData | null; error: string | null; loading: boolean } {
  const [data, setData] = useState<GraphData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!corpusId || !nodeId) {
      setData(null);
      return;
    }
    let active = true;
    setLoading(true);
    getJSON<GraphData>("/subgraph", { corpus_id: corpusId, node_id: nodeId, radius: String(radius) })
      .then((d) => {
        if (active) {
          setData(d);
          setError(null);
        }
      })
      .catch((e: unknown) => {
        if (active) setError(String(e));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [corpusId, nodeId, radius]);
  return { data, error, loading };
}

export function useSearch(
  corpusId: string | null,
  query: string,
  limit = 10
): { data: SearchResult[] | null; loading: boolean } {
  const [data, setData] = useState<SearchResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!corpusId || query.trim().length < 2) {
      setData(null);
      return;
    }
    let active = true;
    setLoading(true);
    // Debounce: wait 300ms after the user stops typing before searching.
    const timer = setTimeout(() => {
      getJSON<SearchResult[]>("/search", {
        corpus_id: corpusId,
        q: query.trim(),
        limit: String(limit),
      })
        .then((d) => {
          if (active) setData(d);
        })
        .catch(() => {
          if (active) setData(null);
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    }, 300);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [corpusId, query, limit]);
  return { data, loading };
}

export async function fetchCorpusDetail(corpusId: string): Promise<CorpusDetail> {
  return getJSON<CorpusDetail>(`/corpora/${corpusId}`);
}

export async function fetchGraphStats(corpusId: string): Promise<GraphStats> {
  return getJSON<GraphStats>("/graph/stats", { corpus_id: corpusId });
}

export async function fetchNode(corpusId: string, nodeId: string): Promise<GraphNode> {
  return getJSON<GraphNode>(`/character/${nodeId}`, { corpus_id: corpusId });
}

export async function generatePodcast(
  corpusId: string,
  entityId: string,
  lengthSeconds?: number,
  force = false,
  engine?: PodcastEngine
): Promise<PodcastResponse> {
  return postJSON<PodcastResponse>("/podcast", {
    corpus_id: corpusId,
    entity_id: entityId,
    length_seconds: lengthSeconds ?? null,
    force,
    engine: engine ?? null,
  });
}

export async function fetchPodcastEngines(corpusId: string): Promise<TTSEnginesResponse> {
  return getJSON<TTSEnginesResponse>("/podcast/engines", { corpus_id: corpusId });
}
