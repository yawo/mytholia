// App: top-level component. Corpus is a route/query param — no corpus name is
// hardcoded in any component (AGENTS.md §2, §8 sprint 3).
//
// i18n: French is the default locale; a language switcher in the header toggles
// between fr and en. All user-facing strings go through the `t` dictionary.

import { useState } from "react";
import { useCorpora, useGraph } from "./api/client";
import { GraphView } from "./components/GraphView";
import { Sidebar } from "./components/Sidebar";
import { SearchBox } from "./components/Search";
import { Legend } from "./components/Legend";
import type { GraphNode } from "./api/types";
import { useI18n, format } from "./i18n";
import type { Locale } from "./i18n/types";

export default function App() {
  const { t, locale, setLocale } = useI18n();
  const { data: corpora, loading: corporaLoading, error: corporaError } = useCorpora();
  const [corpusId, setCorpusId] = useState<string | null>(null);
  const { data: graph, loading: graphLoading, error: graphError } = useGraph(corpusId);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  return (
    <div className="app">
      <header>
        <h1>{t.app.title}</h1>
        <select
          value={corpusId ?? ""}
          onChange={(e) => {
            setCorpusId(e.target.value || null);
            setSelectedNode(null);
          }}
          disabled={corporaLoading}
          aria-label={t.app.selectCorpus}
        >
          <option value="">{t.app.selectCorpus}</option>
          {(corpora ?? []).map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} ({format(t.app.nodeCount, { count: c.node_count })})
            </option>
          ))}
        </select>
        <select
          className="lang-switch"
          value={locale}
          onChange={(e) => setLocale(e.target.value as Locale)}
          aria-label={t.app.language}
        >
          <option value="fr">Français</option>
          <option value="en">English</option>
        </select>
      </header>
      {corporaError && <div className="error-banner">{t.app.errorLoading} {corporaError}</div>}
      <main>
        <div className="graph-panel">
          {corpusId && (
            <div className="graph-toolbar">
              <SearchBox corpusId={corpusId} onSelectNode={setSelectedNode} />
              <Legend />
            </div>
          )}
          {graphError && <div className="error-banner">{t.app.errorLoading}</div>}
          <GraphView
            graph={graph}
            selectedNodeId={selectedNode?.id ?? null}
            onSelectNode={setSelectedNode}
            loading={graphLoading}
          />
        </div>
        {corpusId && <Sidebar corpusId={corpusId} node={selectedNode} />}
      </main>
    </div>
  );
}
