// Shared TypeScript types mirroring the backend pydantic models (api/models.py).
// Corpus-agnostic: no corpus name, entity type, or relation label is hardcoded
// here (AGENTS.md §2).

export type NodeType = "Character" | "Place" | "Object" | "Event" | "Concept";

export interface SourceRef {
  text: string;
  location?: string | null;
}

export interface GraphNode {
  id: string;
  type: NodeType;
  corpus_id: string;
  label: string;
  summary: string;
  source_refs: SourceRef[];
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  corpus_id: string;
  label: string;
  source_refs: SourceRef[];
  summary?: string;
}

export interface GraphData {
  corpus_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface CorpusSummary {
  id: string;
  name: string;
  language: string;
  node_count: number;
  edge_count: number;
  license_note?: string | null;
}

export interface CorpusDetail {
  id: string;
  name: string;
  language: string;
  node_count: number;
  edge_count: number;
  relation_types: string[];
  narrative_tone: string;
  narrative_length_seconds: number;
  voice_provider: string;
  license_note?: string | null;
}

export interface GraphStats {
  corpus_id: string;
  total_nodes: number;
  total_edges: number;
  node_type_counts: Record<string, number>;
  relation_type_counts: Record<string, number>;
}

export interface SearchResult {
  node: GraphNode;
  score: number;
}

export interface PodcastResponse {
  corpus_id: string;
  entity_id: string;
  script: string;
  audio_url: string | null;
  length_seconds: number;
}
