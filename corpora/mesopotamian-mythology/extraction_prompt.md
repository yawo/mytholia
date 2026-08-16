# Extraction prompt override for the mesopotamian-mythology corpus.

You are extracting a knowledge graph from Mesopotamian mythology source text:
the Enuma Elish, the Epic of Gilgamesh, the Descent of Ishtar/Inanna, and
related Sumerian, Akkadian, and Babylonian traditions.

Use the abstract node types Character, Place, Object, Event, Concept. Use only
relation labels from this corpus's controlled list: CHILD_OF, SPOUSE_OF, FOUGHT,
MET, TOOK_PLACE_AT, WORSHIPPED_AS, GUARDS, TRANSFORMED_INTO, RULER_OF,
ASSOCIATED_WITH.

Note: for Mesopotamian mythology, "Character" covers the gods (Marduk, Tiamat,
Anu, Enlil, Enki/Ea, Ishtar/Inanna, Shamash, Adad, Ninurta), heroes
(Gilgamesh, Enkidu, Utnapishtim), and monsters (Humbaba, the Bull of Heaven).
"Place" covers Uruk, the Cedar Forest, the Abzu (primeval sea), and the
underworld (Kur/Irkalla). "Object" covers the Tablet of Destinies, Marduk's
bow, and the Cedar Forest trees. "Event" covers Marduk's battle with Tiamat,
Gilgamesh and Enkidu's journeys, and the Great Flood. "Concept" covers me
(divine decrees/laws), kingship, and the pantheon's hierarchical order.

Note on deities: Sumerian Inanna and Akkadian Ishtar are the same deity under
different names; note both names in the summary. Enki and Ea are likewise the
same god.

Ground every node and edge in a source_ref with a passage locator. If a claim
cannot be grounded in the provided text, OMIT it — do not invent mythology
(AGENTS.md §10).
