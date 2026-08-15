// Frontend component tests (AGENTS.md §9).
// Mounts GraphView/Sidebar with a fixture from EACH of the two corpora to
// catch accidental corpus-specific assumptions (e.g. assuming every character
// has a "spouse" field).
//
// i18n: components render in French (default locale). A separate test verifies
// that switching to English changes the node-type label.

import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { GraphView } from "../../../frontend/src/components/GraphView/GraphView";
import { Sidebar } from "../../../frontend/src/components/Sidebar/Sidebar";
import { I18nProvider } from "../../../frontend/src/i18n";
import type { GraphData, GraphNode } from "../../../frontend/src/api/types";

// Minimal fixtures — one per required corpus (AGENTS.md §9). These are
// intentionally different shapes: the greek node has a spouse relation, the
// egyptian node does not. The components must not assume either.
const greekGraph: GraphData = {
  corpus_id: "greek-odyssey",
  nodes: [
    { id: "char_odysseus", type: "Character", corpus_id: "greek-odyssey", label: "Odysseus", summary: "King of Ithaca.", source_refs: [{ text: "Odyssey", location: "book 9" }] },
    { id: "char_penelope", type: "Character", corpus_id: "greek-odyssey", label: "Penelope", summary: "Wife of Odysseus.", source_refs: [{ text: "Odyssey", location: "book 1" }] },
  ],
  edges: [
    { id: "e1", source: "char_odysseus", target: "char_penelope", relation: "SPOUSE_OF", corpus_id: "greek-odyssey", label: "Spouse Of", source_refs: [] },
  ],
};

const egyptianGraph: GraphData = {
  corpus_id: "egyptian-mythology",
  nodes: [
    { id: "char_osiris", type: "Character", corpus_id: "egyptian-mythology", label: "Osiris", summary: "God of the afterlife.", source_refs: [{ text: "Book of the Dead", location: "spell 1" }] },
    { id: "place_duat", type: "Place", corpus_id: "egyptian-mythology", label: "The Duat", summary: "The underworld.", source_refs: [{ text: "Book of the Dead", location: "spell 125" }] },
  ],
  edges: [
    { id: "e1", source: "char_osiris", target: "place_duat", relation: "RULER_OF", corpus_id: "egyptian-mythology", label: "Ruler Of", source_refs: [] },
  ],
};

const cases = [
  { name: "greek-odyssey", graph: greekGraph },
  { name: "egyptian-mythology", graph: egyptianGraph },
];

function renderWithI18n(ui: React.ReactElement) {
  return render(<I18nProvider>{ui}</I18nProvider>);
}

describe.each(cases)("GraphView ($name)", ({ graph }) => {
  it("renders all node labels without corpus-specific assumptions", () => {
    const onselect = (_n: GraphNode) => {};
    renderWithI18n(<GraphView graph={graph} selectedNodeId={null} onSelectNode={onselect} />);
    for (const node of graph.nodes) {
      expect(screen.getByText(node.label)).toBeTruthy();
    }
  });

  it("calls onSelectNode when a node is clicked", () => {
    let picked: GraphNode | null = null;
    renderWithI18n(
      <GraphView graph={graph} selectedNodeId={null} onSelectNode={(n) => (picked = n)} />
    );
    const firstNode = graph.nodes[0];
    const label = screen.getByText(firstNode.label);
    // click the parent <g> (the circle's group)
    fireEvent.click(label.parentElement!);
    expect(picked).not.toBeNull();
    expect(picked!.id).toBe(firstNode.id);
  });
});

describe.each(cases)("Sidebar ($name, fr default)", ({ graph }) => {
  it("renders localized node type, label, summary, sources heading", () => {
    const node = graph.nodes[0];
    renderWithI18n(<Sidebar corpusId={graph.corpus_id} node={node} />);
    expect(screen.getByText(node.label)).toBeTruthy();
    // Default locale is fr: Character → "Personnage"
    expect(screen.getByText("Personnage")).toBeTruthy();
    expect(screen.getByText(node.summary)).toBeTruthy();
    // fr sources heading
    expect(screen.getByText("Sources")).toBeTruthy();
    for (const ref of node.source_refs) {
      expect(screen.getByText(new RegExp(ref.text))).toBeTruthy();
    }
  });

  it("renders the localized Generate Podcast button (fr)", () => {
    const node = graph.nodes[0];
    renderWithI18n(<Sidebar corpusId={graph.corpus_id} node={node} />);
    expect(screen.getByText("Générer le balado")).toBeTruthy();
  });

  it("does not assume a spouse field exists", () => {
    // Sidebar must render for both the greek node (has spouse edge) and the
    // egyptian node (no spouse) without erroring (AGENTS.md §9).
    const node = graph.nodes[0];
    const { container } = renderWithI18n(<Sidebar corpusId={graph.corpus_id} node={node} />);
    expect(container).toBeTruthy();
  });
});

describe("Sidebar i18n: locale switching", () => {
  it("shows 'Personnage' in fr and 'Character' in en for the same node", () => {
    const node = egyptianGraph.nodes[0]; // type: Character
    // Default (fr)
    const { unmount } = renderWithI18n(<Sidebar corpusId="egyptian-mythology" node={node} />);
    expect(screen.getByText("Personnage")).toBeTruthy();
    unmount();

    // English: simulate by setting localStorage before render
    const original = window.localStorage.getItem("graphodyssee-locale");
    window.localStorage.setItem("graphodyssee-locale", "en");
    renderWithI18n(<Sidebar corpusId="egyptian-mythology" node={node} />);
    expect(screen.getByText("Character")).toBeTruthy();
    // Restore
    if (original === null) {
      window.localStorage.removeItem("graphodyssee-locale");
    } else {
      window.localStorage.setItem("graphodyssee-locale", original);
    }
  });
});

describe("Sidebar empty state", () => {
  it("renders the localized select-node prompt (fr)", () => {
    renderWithI18n(<Sidebar corpusId="greek-odyssey" node={null} />);
    expect(screen.getByText("Sélectionnez un nœud pour voir ses détails.")).toBeTruthy();
  });
});
