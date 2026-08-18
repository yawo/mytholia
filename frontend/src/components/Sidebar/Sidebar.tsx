// Sidebar: bio, timeline (source_refs), and "Generate Podcast" button.
// AGENTS.md §10: Sidebar is presentational; data fetching via api/client.ts.
// Corpus-agnostic: does not assume any specific field like "spouse" exists.
// i18n: all strings from the dictionary; node-type label localized.

import { useEffect, useState } from "react";
import type { GraphNode, PodcastEngine, PodcastResponse, TTSEngineStatus } from "../../api/types";
import { fetchPodcastEngines, generatePodcast } from "../../api/client";
import { useI18n } from "../../i18n";
import type { NodeTypeKey } from "../../i18n/types";

interface SidebarProps {
  corpusId: string;
  node: GraphNode | null;
}

export function Sidebar({ corpusId, node }: SidebarProps) {
  const { t, locale } = useI18n();
  const [loading, setLoading] = useState(false);
  const [podcast, setPodcast] = useState<PodcastResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [engines, setEngines] = useState<TTSEngineStatus[]>([]);
  const [selectedEngine, setSelectedEngine] = useState<PodcastEngine>("deepgram");

  useEffect(() => {
    let active = true;
    fetchPodcastEngines(corpusId)
      .then((res) => {
        if (!active) return;
        setEngines(res.engines);
        const defaultEngine = res.engines.find((engine) => engine.default)?.engine ?? "deepgram";
        setSelectedEngine(defaultEngine);
      })
      .catch(() => {
        if (active) setEngines([]);
      });
    return () => {
      active = false;
    };
  }, [corpusId]);

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
      const res = await generatePodcast(corpusId, node.id, undefined, false, selectedEngine, locale);
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

      <label className="podcast-engine-picker">
        {t.sidebar.ttsEngine}
        <select
          value={selectedEngine}
          onChange={(event) => setSelectedEngine(event.target.value as PodcastEngine)}
          disabled={loading}
        >
          {engines.map((engine) => (
            <option key={engine.engine} value={engine.engine} disabled={!engine.configured}>
              {engine.engine}
              {engine.configured ? "" : ` (${t.sidebar.missingEnv})`}
            </option>
          ))}
        </select>
      </label>

      <button onClick={onGenerate} disabled={loading}>
        {loading ? t.sidebar.generating : t.sidebar.generatePodcast}
      </button>

      {error && <p className="error">{error}</p>}
      {podcast && (
        <section className="podcast-result">
          <h3>{t.sidebar.podcastScript}</h3>
          <p className="podcast-engine">{t.sidebar.engine}: {podcast.engine}</p>
          <pre>{podcast.script}</pre>
          {podcast.audio_url && <audio controls src={podcast.audio_url} />}
        </section>
      )}
    </aside>
  );
}
