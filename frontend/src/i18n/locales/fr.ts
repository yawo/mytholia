// French dictionary — the primary locale for GraphOdyssée.
import type { Dictionary } from "../types";

const fr: Dictionary = {
  app: {
    title: "GraphOdyssée",
    tagline: "Explorateur mythologique GraphRAG",
    selectCorpus: "Choisir un corpus…",
    nodeCount: "{count} nœuds",
    language: "Langue",
    theme: "Thème",
    darkTheme: "Sombre",
    lightTheme: "Clair",
    switchToDarkTheme: "Passer au thème sombre",
    switchToLightTheme: "Passer au thème clair",
    searchPlaceholder: "Rechercher un nœud…",
    searchResults: "{count} résultats",
    searchNoResults: "Aucun résultat.",
    errorLoading: "Erreur lors du chargement.",
    legend: "Légende",
  },
  graph: {
    loading: "Chargement du graphe…",
    empty: "Aucune donnée. Choisissez un corpus.",
    ariaLabel: "Graphe de connaissances",
  },
  sidebar: {
    selectNode: "Sélectionnez un nœud pour voir ses détails.",
    sources: "Sources",
    generatePodcast: "Générer le balado",
    generating: "Génération…",
    podcastScript: "Script du balado",
  },
  nodeTypes: {
    Character: "Personnage",
    Place: "Lieu",
    Object: "Objet",
    Event: "Événement",
    Concept: "Concept",
  },
  errors: {
    nodeNotFound: "nœud « {nodeId} » introuvable dans le corpus « {corpusId} »",
    corpusNotFound: "corpus « {corpusId} » introuvable",
  },
};

export default fr;
