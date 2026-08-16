// SearchBox: search/filter nodes within a corpus.
// AGENTS.md §10: presentational; data fetching via useSearch hook in client.ts.
// Corpus-agnostic: searches whatever corpus is active.

import { useState } from "react";
import type { GraphNode } from "../../api/types";
import { useSearch } from "../../api/client";
import { useI18n, format } from "../../i18n";

interface SearchBoxProps {
  corpusId: string;
  onSelectNode: (node: GraphNode) => void;
}

export function SearchBox({ corpusId, onSelectNode }: SearchBoxProps) {
  const { t } = useI18n();
  const [query, setQuery] = useState("");
  const { data: results, loading } = useSearch(corpusId, query);

  return (
    <div className="search-box">
      <input
        type="text"
        placeholder={t.app.searchPlaceholder}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        aria-label={t.app.searchPlaceholder}
      />
      {loading && <span className="search-loading">…</span>}
      {results && results.length > 0 && (
        <ul className="search-results">
          {results.map((r) => (
            <li key={r.node.id} onClick={() => onSelectNode(r.node)}>
              <span className="search-result-label">{r.node.label}</span>
              <span className="search-result-type">{t.nodeTypes[r.node.type]}</span>
            </li>
          ))}
        </ul>
      )}
      {results && results.length === 0 && query.trim().length >= 2 && !loading && (
        <p className="search-empty">{t.app.searchNoResults}</p>
      )}
      {results && results.length > 0 && (
        <p className="search-count">
          {format(t.app.searchResults, { count: results.length })}
        </p>
      )}
    </div>
  );
}
