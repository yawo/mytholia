# Extraction prompt override for the greek-iliad corpus.

You are extracting a knowledge graph from Greek mythology source text,
specifically the Iliad and related Trojan War traditions.

Use the abstract node types Character, Place, Object, Event, Concept. Use only
relation labels from this corpus's controlled list: CHILD_OF, SPOUSE_OF, FOUGHT,
MET, TOOK_PLACE_AT, WORSHIPPED_AS, GUARDS, TRANSFORMED_INTO, RULER_OF,
ASSOCIATED_WITH.

Note: for the Iliad, "Character" covers Greek and Trojan heroes (Achilles,
Hector), gods who intervene (Zeus, Athena), and mortal figures (Priam,
Agamemnon). "Event" covers battles, duels, and the war itself.

Ground every node and edge in a source_ref with a passage locator. If a claim
cannot be grounded in the provided text, OMIT it — do not invent mythology
(AGENTS.md §10).
