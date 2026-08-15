// App: top-level component. Corpus is a route/query param — no corpus name is
// hardcoded in any component (AGENTS.md §2, §8 sprint 3).

import { useState } from "react";
import { useCorpora, useGraph } from "./api/client";
import { GraphView } from "./components/GraphView";
import { Sidebar } from "./components/Sidebar";
import type { GraphNode } from "./api/types";

export default function App() {
  const { data: corpora, loading: corporaLoading } = useCorpora();
  const [corpusId, setCorpusId] = useState<string | null>(null);
  const { data: graph, loading: graphLoading } = useGraph(corpusId);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  return (
    <div className="app">
      <header>
        <h1>GraphOdyssée</h1>
        <select
          value={corpusId ?? ""}
          onChange={(e) => {
            setCorpusId(e.target.value || null);
            setSelectedNode(null);
          }}
          disabled={corporaLoading}
        >
          <option value="">Select a corpus…</option>
          {(corpora ?? []).map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} ({c.node_count} nodes)
            </option>
          ))}
        </select>
      </header>
      <main>
        <GraphView
          graph={graph}
          selectedNodeId={selectedNode?.id ?? null}
          onSelectNode={setSelectedNode}
          loading={graphLoading}
        />
        {corpusId && <Sidebar corpusId={corpusId} node={selectedNode} />}
      </main>
    </div>
  );
}
