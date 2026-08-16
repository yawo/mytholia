// Legend: maps node-type colors to localized labels.
// Shows the fixed, corpus-agnostic node type set (AGENTS.md §4).

import type { NodeTypeKey } from "../../i18n/types";
import { useI18n } from "../../i18n";

const TYPE_COLORS: Record<string, string> = {
  Character: "#e07b39",
  Place: "#4a90d9",
  Object: "#7b9b3a",
  Event: "#b85c8a",
  Concept: "#8a6dd9",
};

const TYPE_ORDER: NodeTypeKey[] = ["Character", "Place", "Object", "Event", "Concept"];

export function Legend() {
  const { t } = useI18n();
  return (
    <div className="legend">
      <span className="legend-title">{t.app.legend}</span>
      <div className="legend-items">
        {TYPE_ORDER.map((type) => (
          <div key={type} className="legend-item">
            <span
              className="legend-swatch"
              style={{ backgroundColor: TYPE_COLORS[type] ?? "#999" }}
            />
            <span>{t.nodeTypes[type]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
