import { describe, expect, it } from "vitest";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const repoRoot = resolve(__dirname, "../..");
const corporaDir = resolve(repoRoot, "corpora");
const processedDir = resolve(repoRoot, "data/processed");

type GraphJson = {
  corpus_id: string;
  locale?: string;
  source_locale?: string;
  nodes: Array<{ id: string; corpus_id: string; source_refs: unknown[] }>;
  edges: Array<{ id: string; source: string; target: string; corpus_id: string; source_refs: unknown[] }>;
};

const corpusIds = readdirSync(corporaDir).filter((entry) =>
  existsSync(resolve(corporaDir, entry, "manifest.yaml")),
);

describe("processed corpus data", () => {
  it("ships a graph.json for every manifest-backed corpus", () => {
    expect(corpusIds.length).toBeGreaterThan(0);

    for (const corpusId of corpusIds) {
      const graphPath = resolve(processedDir, corpusId, "graph.json");
      expect(existsSync(graphPath), `${corpusId} graph.json`).toBe(true);

      const graph = JSON.parse(readFileSync(graphPath, "utf8")) as GraphJson;
      expect(graph.corpus_id).toBe(corpusId);
      expect(graph.nodes.length, `${corpusId} node count`).toBeGreaterThan(0);
      expect(graph.edges.length, `${corpusId} edge count`).toBeGreaterThan(0);
    }
  });

  it("ships a fully materialized French graph for every manifest-backed corpus", () => {
    for (const corpusId of corpusIds) {
      const englishGraphPath = resolve(processedDir, corpusId, "graph.json");
      const frenchGraphPath = resolve(processedDir, corpusId, "graph.fr.json");
      expect(existsSync(frenchGraphPath), `${corpusId} graph.fr.json`).toBe(true);

      const englishGraph = JSON.parse(readFileSync(englishGraphPath, "utf8")) as GraphJson;
      const frenchGraph = JSON.parse(readFileSync(frenchGraphPath, "utf8")) as GraphJson;

      expect(frenchGraph.corpus_id).toBe(corpusId);
      expect(frenchGraph.locale).toBe("fr");
      expect(frenchGraph.source_locale).toBe("en");
      expect(frenchGraph.nodes.length).toBe(englishGraph.nodes.length);
      expect(frenchGraph.edges.length).toBe(englishGraph.edges.length);

      for (const node of frenchGraph.nodes) {
        expect(node.corpus_id).toBe(corpusId);
        expect(node.source_refs.length, `${corpusId}/${node.id} French source refs`).toBeGreaterThan(0);
      }

      for (const edge of frenchGraph.edges) {
        expect(edge.corpus_id).toBe(corpusId);
        expect(edge.source_refs.length, `${corpusId}/${edge.id} French source refs`).toBeGreaterThan(0);
      }
    }
  });

  it("keeps every processed fact corpus-scoped, connected, and sourced", () => {
    for (const corpusId of corpusIds) {
      const graphPath = resolve(processedDir, corpusId, "graph.json");
      const graph = JSON.parse(readFileSync(graphPath, "utf8")) as GraphJson;
      const nodeIds = new Set(graph.nodes.map((node) => node.id));

      for (const node of graph.nodes) {
        expect(node.corpus_id).toBe(corpusId);
        expect(node.source_refs.length, `${corpusId}/${node.id} source refs`).toBeGreaterThan(0);
      }

      for (const edge of graph.edges) {
        expect(edge.corpus_id).toBe(corpusId);
        expect(nodeIds.has(edge.source), `${corpusId}/${edge.id} source`).toBe(true);
        expect(nodeIds.has(edge.target), `${corpusId}/${edge.id} target`).toBe(true);
        expect(edge.source_refs.length, `${corpusId}/${edge.id} source refs`).toBeGreaterThan(0);
      }
    }
  });
});
