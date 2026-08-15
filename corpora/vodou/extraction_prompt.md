# Extraction prompt override for the vodou corpus.

You are extracting a knowledge graph from Haitian Vodou tradition: the lwa
(spirits), their families (Rada, Petwo, Gede), rituals, and syncretism with
Catholic saints.

Use the abstract node types Character, Place, Object, Event, Concept. Use only
relation labels from this corpus's controlled list: CHILD_OF, SPOUSE_OF, FOUGHT,
MET, TOOK_PLACE_AT, WORSHIPPED_AS, GUARDS, TRANSFORMED_INTO, RULER_OF,
ASSOCIATED_WITH.

Note: for Vodou, "Character" covers the lwa (Papa Legba, Baron Samedi, Damballa,
Erzulie Freda, Ogou). Vodou does not have "deities" in the Greek sense — the lwa
are mediating spirit beings. "Place" covers the peristil (temple), Ginen (the
spiritual homeland), and the crossroads. "Object" covers ritual items (veve,
drums, the poto mitan). "Event" covers possession, ceremonies, and the
transatlantic passage. "Concept" covers the Rada/Petwo distinction and lwa
nanchon (spirit nations).

Note on sourcing: Vodou is an oral-tradition religion. "Primary text" does not
mean the same thing as for the Odyssey. Use scholarly ethnographic sources
(Maya Deren, Karen McCarthy Brown) and note in source_refs when a tradition
is oral rather than text-based. Do not invent traditions (AGENTS.md §10).

Ground every node and edge in a source_ref with a passage locator. If a claim
cannot be grounded in the provided text, OMIT it — do not invented mythology
(AGENTS.md §10).
