// Sidebar: bio, timeline (source_refs), and "Generate Podcast" button.
// AGENTS.md §10: Sidebar is presentational; data fetching via api/client.ts.
// Corpus-agnostic: does not assume any specific field like "spouse" exists.
// i18n: all strings from the dictionary; node-type label localized.

import { useState } from "react";
import type { GraphNode, PodcastResponse } from "../../api/types";
import { generatePodcast } from "../../api/client";
import { useI18n } from "../../i18n";
import type { NodeTypeKey } from "../../i18n/types";

interface SidebarProps {
  corpusId: string;
  node: GraphNode | null;
}

export function Sidebar({ corpusId, node }: SidebarProps) {
  const { t } = useI18n();
  const [loading, setLoading] = useState(false);
  const [podcast, setPodcast] = useState<PodcastResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!node) {
    return (
      <aside className="sidebar">
        <p>{t.sidebar.selectNode}</p>
      </aside>
    );
  }

  // Localized node type; falls back to the raw type for unknown values.
  const typeLabel = t.nodeTypes[node.type as NodeTypeKey] ?? node.type;

  const onGenerate = async () => {
    setLoading(true);
    setError(null);
    setPodcast(null);
    try {
      const res = await generatePodcast(corpusId, node.id);
      setPodcast(res);
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <aside className="sidebar">
      <h2>{node.label}</h2>
      <p className="node-type">{typeLabel}</p>
      <p className="node-summary">{node.summary}</p>

      {node.source_refs.length > 0 && (
        <section>
          <h3>{t.sidebar.sources}</h3>
          <ul className="source-refs">
            {node.source_refs.map((ref, i) => (
              <li key={i}>
                {ref.text}
                {ref.location ? ` (${ref.location})` : ""}
              </li>
            ))}
          </ul>
        </section>
      )}

      <button onClick={onGenerate} disabled={loading}>
        {loading ? t.sidebar.generating : t.sidebar.generatePodcast}
      </button>

      {error && <p className="error">{error}</p>}
      {podcast && (
        <section className="podcast-result">
          <h3>{t.sidebar.podcastScript}</h3>
          <pre>{podcast.script}</pre>
          {podcast.audio_url && <audio controls src={podcast.audio_url} />}
        </section>
      )}
    </aside>
  );
}
