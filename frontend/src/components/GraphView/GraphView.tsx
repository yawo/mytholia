// GraphView: presentational component rendering a corpus's graph.
// AGENTS.md §10: GraphView is presentational; data fetching lives in api/client.ts.
// Corpus-agnostic: renders whatever nodes/edges it receives — no corpus names.
// i18n: loading/empty/aria strings from the dictionary.

import { useMemo } from "react";
import type { GraphData, GraphNode } from "../../api/types";
import { useI18n } from "../../i18n";

interface GraphViewProps {
  graph: GraphData | null;
  selectedNodeId: string | null;
  onSelectNode: (node: GraphNode) => void;
  loading?: boolean;
}

// Node colors are keyed by the fixed, corpus-agnostic node type set (AGENTS.md §4).
const TYPE_COLORS: Record<string, string> = {
  Character: "#e07b39",
  Place: "#4a90d9",
  Object: "#7b9b3a",
  Event: "#b85c8a",
  Concept: "#8a6dd9",
};

export function GraphView({ graph, selectedNodeId, onSelectNode, loading }: GraphViewProps) {
  const { t } = useI18n();
  const nodes = graph?.nodes ?? [];
  const edges = graph?.edges ?? [];

  // Simple deterministic circular layout (no graph-viz dependency needed for the skeleton).
  const positions = useMemo(() => {
    const pos: Record<string, { x: number; y: number }> = {};
    const cx = 250;
    const cy = 250;
    const r = 180;
    const n = nodes.length;
    nodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / Math.max(n, 1) - Math.PI / 2;
      pos[node.id] = { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
    });
    return pos;
  }, [nodes]);

  if (loading) {
    return <div className="graph-loading">{t.graph.loading}</div>;
  }
  if (nodes.length === 0) {
    return <div className="graph-empty">{t.graph.empty}</div>;
  }

  return (
    <svg width="500" height="500" className="graph-view" role="img" aria-label={t.graph.ariaLabel}>
      {/* edges */}
      {edges.map((e) => {
        const s = positions[e.source];
        const tPos = positions[e.target];
        if (!s || !tPos) return null;
        return (
          <line
            key={e.id}
            x1={s.x}
            y1={s.y}
            x2={tPos.x}
            y2={tPos.y}
            className="graph-edge"
            strokeWidth={1.5}
            markerEnd="url(#arrow)"
          />
        );
      })}
      <defs>
        <marker id="arrow" markerWidth="8" markerHeight="8" refX="12" refY="3" orient="auto">
          <path className="graph-arrow" d="M0,0 L6,3 L0,6 Z" />
        </marker>
      </defs>
      {/* nodes */}
      {nodes.map((node) => {
        const p = positions[node.id];
        const isSelected = node.id === selectedNodeId;
        return (
          <g className="graph-node" key={node.id} transform={`translate(${p.x}, ${p.y})`} onClick={() => onSelectNode(node)}>
            <circle
              r={isSelected ? 16 : 12}
              fill={TYPE_COLORS[node.type] ?? "#999"}
              stroke={isSelected ? "#222" : "#fff"}
              strokeWidth={isSelected ? 3 : 1.5}
              style={{ cursor: "pointer" }}
            />
            <text
              textAnchor="middle"
              y={26}
              fontSize={10}
              style={{ pointerEvents: "none", userSelect: "none" }}
            >
              {node.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
