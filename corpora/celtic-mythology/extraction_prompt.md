# Extraction prompt override for the celtic-mythology corpus.

You are extracting a knowledge graph from Celtic mythology source text: the
Irish Mythological Cycle (Lebor Gabala Erenn, Cath Maige Tuired), the Ulster
Cycle (Tain Bo Cuailnge), the Welsh Mabinogion, and related traditions.

Use the abstract node types Character, Place, Object, Event, Concept. Use only
relation labels from this corpus's controlled list: CHILD_OF, SPOUSE_OF, FOUGHT,
MET, TOOK_PLACE_AT, WORSHIPPED_AS, GUARDS, TRANSFORMED_INTO, RULER_OF,
ASSOCIATED_WITH.

Note: for Celtic mythology, "Character" covers the Tuatha De Danann (the Dagda,
Lugh, Brigid, the Morrigan, Nuada, Manannan mac Lir), the Fomorians (Balor,
Bres), and heroes (Cuchulainn, Finn mac Cumhaill). The Tuatha De Danann are
deities euhemerised as former kings of Ireland by Christian scribes. "Place"
covers the sidhe (fairy mounds), Tara, Mag Tuired, and the Otherworld (Tir na
nOg). "Object" covers the four treasures of the Tuatha De Danann (the Stone of
Fal, the Spear of Lugh, the Sword of Nuada, the Cauldron of the Dagda) and
Cuchulainn's spear (the Gae Bolga). "Event" covers the Battle of Mag Tuired
(both first and second), the Tain (Cattle Raid of Cooley), and the Children of
Lir. "Concept" covers geis (sacred taboos), the bardic order, and the
Otherworld.

Ground every node and edge in a source_ref with a passage locator. If a claim
cannot be grounded in the provided text, OMIT it — do not invent mythology
(AGENTS.md §10).
