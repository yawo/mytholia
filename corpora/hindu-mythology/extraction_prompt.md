# Extraction prompt override for the hindu-mythology corpus.

You are extracting a knowledge graph from Hindu mythology source text: the
Ramayana, Mahabharata, Vedas, Puranas, and related traditions.

Use the abstract node types Character, Place, Object, Event, Concept. Use only
relation labels from this corpus's controlled list: CHILD_OF, SPOUSE_OF, FOUGHT,
MET, TOOK_PLACE_AT, WORSHIPPED_AS, GUARDS, TRANSFORMED_INTO, RULER_OF,
ASSOCIATED_WITH.

Note: for Hindu mythology, "Character" covers gods (Shiva, Vishnu, Krishna),
demons (Ravana, asuras), and heroes (Rama, Arjuna). "Place" covers mythological
locations (Ayodhya, Lanka, Bhogavati, Patala). "Object" covers divine weapons
and items (the Sudarshana Chakra, the bow of Rama). "Event" covers the
Kurukshetra War, Rama's exile, and the churning of the ocean. "Concept"
covers dharma, karma, and moksha.

Ground every node and edge in a source_ref with a passage locator. If a claim
cannot be grounded in the provided text, OMIT it — do not invented mythology
(AGENTS.md §10).
