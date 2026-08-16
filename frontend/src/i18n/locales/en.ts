// English dictionary.
import type { Dictionary } from "../types";

const en: Dictionary = {
  app: {
    title: "GraphOdyssée",
    tagline: "GraphRAG Mythology Explorer",
    selectCorpus: "Select a corpus…",
    nodeCount: "{count} nodes",
    language: "Language",
    theme: "Theme",
    darkTheme: "Dark",
    lightTheme: "Light",
    switchToDarkTheme: "Switch to dark theme",
    switchToLightTheme: "Switch to light theme",
    searchPlaceholder: "Search nodes…",
    searchResults: "{count} results",
    searchNoResults: "No results.",
    errorLoading: "Error loading data.",
    legend: "Legend",
  },
  graph: {
    loading: "Loading graph…",
    empty: "No graph data. Select a corpus.",
    ariaLabel: "Knowledge graph",
  },
  sidebar: {
    selectNode: "Select a node to see its details.",
    sources: "Sources",
    generatePodcast: "Generate Podcast",
    generating: "Generating…",
    podcastScript: "Podcast script",
  },
  nodeTypes: {
    Character: "Character",
    Place: "Place",
    Object: "Object",
    Event: "Event",
    Concept: "Concept",
  },
  errors: {
    nodeNotFound: "node {nodeId} not found in corpus {corpusId}",
    corpusNotFound: "corpus {corpusId} not found",
  },
};

export default en;
