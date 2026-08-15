# Extraction prompt override for the egyptian-mythology corpus.

You are extracting a knowledge graph from Egyptian mythology source text:
Osiris, Isis, Set, Horus, Anubis, Ma'at, the Duat, the weighing of the heart,
and related traditions.

Use the abstract node types Character, Place, Object, Event, Concept. Use only
relation labels from this corpus's controlled list: CHILD_OF, SPOUSE_OF, FOUGHT,
MET, TOOK_PLACE_AT, WORSHIPPED_AS, GUARDS, TRANSFORMED_INTO, RULER_OF,
ASSOCIATED_WITH.

Note: for Egyptian sources, "Character" covers gods (Osiris), pharaohs, and
personified concepts when treated as agents. "Concept" covers abstracts like
Ma'at (cosmic order) when treated as ideas rather than agents.

Ground every node and edge in a source_ref with a passage locator. If a claim
cannot be grounded in the provided text, OMIT it — do not invent mythology
(AGENTS.md §10).
