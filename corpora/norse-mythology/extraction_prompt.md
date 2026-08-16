# Extraction prompt override for the norse-mythology corpus.

You are extracting a knowledge graph from Norse mythology source text: the
Prose Edda (Snorri Sturluson), the Poetic Edda (Codex Regius), and related
traditions.

Use the abstract node types Character, Place, Object, Event, Concept. Use only
relation labels from this corpus's controlled list: CHILD_OF, SPOUSE_OF, FOUGHT,
MET, TOOK_PLACE_AT, WORSHIPPED_AS, GUARDS, TRANSFORMED_INTO, RULER_OF,
ASSOCIATED_WITH.

Note: for Norse mythology, "Character" covers the Aesir (Odin, Thor, Frigg),
the Vanir (Freyr, Freyja, Njord), giants (jotnar, like Loki's kin), and heroes
(Sigurd). "Place" covers the nine worlds (Asgard, Midgard, Jotunheim) and
locations (Valhalla, Yggdrasil as a cosmological place). "Object" covers
artifacts (Mjolnir, Gungnir, Draupnir). "Event" covers Ragnarok, the Aesir-
Vanir war, and Baldur's death. "Concept" covers fate (wyrd/urd), valkyries,
and einherjar.

Ground every node and edge in a source_ref with a passage locator. If a claim
cannot be grounded in the provided text, OMIT it — do not invent mythology
(AGENTS.md §10).
