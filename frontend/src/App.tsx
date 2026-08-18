// App: top-level component. Corpus is a route/query param — no corpus name is
// hardcoded in any component (AGENTS.md §2, §8 sprint 3).
//
// i18n: French is the default locale; a language switcher in the header toggles
// between fr and en. All user-facing strings go through the `t` dictionary.

import { useEffect, useState } from "react";
import { useCorpora, useGraph } from "./api/client";
import { GraphView } from "./components/GraphView";
import { Sidebar } from "./components/Sidebar";
import { SearchBox } from "./components/Search";
import { Legend } from "./components/Legend";
import type { GraphNode } from "./api/types";
import { useI18n, format } from "./i18n";
import type { Locale } from "./i18n/types";

type Theme = "dark" | "light";

const THEME_STORAGE_KEY = "graphodyssee-theme";

function getInitialTheme(): Theme {
  if (typeof window === "undefined") return "dark";
  const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
  if (storedTheme === "dark" || storedTheme === "light") return storedTheme;
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

export default function App() {
  const { t, locale, setLocale } = useI18n();
  const { data: corpora, loading: corporaLoading, error: corporaError } = useCorpora();
  const [corpusId, setCorpusId] = useState<string | null>(null);
  const { data: graph, loading: graphLoading, error: graphError } = useGraph(corpusId, locale);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [theme, setTheme] = useState<Theme>(getInitialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  useEffect(() => {
    if (!selectedNode || !graph) return;
    const localizedNode = graph.nodes.find((node) => node.id === selectedNode.id);
    if (localizedNode) setSelectedNode(localizedNode);
  }, [graph, selectedNode]);

  const toggleTheme = () => setTheme((currentTheme) => (currentTheme === "dark" ? "light" : "dark"));

  return (
    <div className="app">
      <div className="app-glow app-glow-one" />
      <div className="app-glow app-glow-two" />
      <header className="app-header">
        <div className="brand-lockup">
          <span className="brand-mark" aria-hidden="true">✦</span>
          <div>
            <p className="eyebrow">{t.app.tagline}</p>
            <h1>{t.app.title}</h1>
          </div>
        </div>
        <div className="header-controls">
          <select
            className="control-select corpus-select"
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
            className="control-select lang-switch"
            value={locale}
            onChange={(e) => setLocale(e.target.value as Locale)}
            aria-label={t.app.language}
          >
            <option value="fr">Français</option>
            <option value="en">English</option>
          </select>
          <button
            className="theme-switch"
            type="button"
            onClick={toggleTheme}
            aria-label={theme === "dark" ? t.app.switchToLightTheme : t.app.switchToDarkTheme}
            aria-pressed={theme === "light"}
          >
            <span className="theme-switch-track">
              <span className="theme-switch-thumb">{theme === "dark" ? "☾" : "☀"}</span>
            </span>
            <span className="theme-switch-label">{theme === "dark" ? t.app.darkTheme : t.app.lightTheme}</span>
          </button>
        </div>
      </header>
      {corporaError && <div className="error-banner">{t.app.errorLoading} {corporaError}</div>}
      <main>
        <div className="graph-panel glass-card">
          {corpusId && (
            <div className="graph-toolbar">
              <SearchBox corpusId={corpusId} onSelectNode={setSelectedNode} />
              <Legend />
            </div>
          )}
          {graphError && <div className="error-banner inline-error">{t.app.errorLoading}</div>}
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
