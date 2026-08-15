// Type definitions for the i18n system.
//
// The app ships with English (en) and French (fr) locales. French is the
// primary/default locale per the project (GraphOdyssée). Adding a new locale
// means adding a new file in locales/ and a key here — no component changes.

export type Locale = "fr" | "en";

// Node-type display labels (AGENTS.md §4: fixed, corpus-agnostic types).
// Keys match the raw node type strings from the API.
export type NodeTypeKey = "Character" | "Place" | "Object" | "Event" | "Concept";

// The shape every locale dictionary must satisfy. This is enforced by
// `satisfies Dictionary` in each locale file so missing keys are caught at
// compile time.
export interface Dictionary {
  app: {
    title: string;
    selectCorpus: string;
    nodeCount: string; // e.g. "{count} nodes" — use {count} as placeholder
    language: string;
  };
  graph: {
    loading: string;
    empty: string;
    ariaLabel: string;
  };
  sidebar: {
    selectNode: string;
    sources: string;
    generatePodcast: string;
    generating: string;
    podcastScript: string;
  };
  nodeTypes: Record<NodeTypeKey, string>;
  errors: {
    nodeNotFound: string; // placeholders: {nodeId}, {corpusId}
    corpusNotFound: string; // placeholder: {corpusId}
  };
}
