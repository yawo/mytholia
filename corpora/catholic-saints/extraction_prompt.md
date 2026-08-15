# Extraction prompt override for the catholic-saints corpus.

You are extracting a knowledge graph from Catholic hagiography source text:
the lives of the saints, the Golden Legend, Butler's Lives of the Saints, and
related traditions.

Use the abstract node types Character, Place, Object, Event, Concept. Use only
relation labels from this corpus's controlled list: CHILD_OF, SPOUSE_OF, FOUGHT,
MET, TOOK_PLACE_AT, WORSHIPPED_AS, GUARDS, TRANSFORMED_INTO, RULER_OF,
ASSOCIATED_WITH.

Note: for Catholic saints, "Character" covers saints, apostles, martyrs, and
biblical figures. "Place" covers pilgrimage sites (Rome, Assisi, Santiago de
Compostela). "Object" covers relics and devotional items. "Event" covers
martyrdoms, miracles, and councils. "Concept" covers theological ideas
(grace, sainthood, canonization).

Ground every node and edge in a source_ref with a passage locator. If a claim
cannot be grounded in the provided text, OMIT it — do not invent hagiography
(AGENTS.md §10).
