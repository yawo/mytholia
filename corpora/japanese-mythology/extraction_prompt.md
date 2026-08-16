# Extraction prompt override for the japanese-mythology corpus.

You are extracting a knowledge graph from Japanese mythology source text: the
Kojiki (712 CE) and the Nihon Shoki (720 CE), the primary sources for Shinto
mythology.

Use the abstract node types Character, Place, Object, Event, Concept. Use only
relation labels from this corpus's controlled list: CHILD_OF, SPOUSE_OF, FOUGHT,
MET, TOOK_PLACE_AT, WORSHIPPED_AS, GUARDS, TRANSFORMED_INTO, RULER_OF,
ASSOCIATED_WITH.

Note: for Japanese mythology, "Character" covers the kami (Amaterasu, Susanoo,
Tsukuyomi, Izanagi, Izanami, Inari, Raijin). Kami are spirits/deities, not
"gods" in the Greek sense. "Place" covers Takamagahara (Plain of High Heaven),
Yomi (the underworld), and Onogoro Island. "Object" covers divine items (the
Ame-no-nuhoko jeweled spear, the Kusanagi no Tsurugi sword, the Yasakani no
Magatama jewel). "Event" covers the creation of the Japanese archipelago
(Kuniumi), the birth of the kami (Kamiumi), Amaterasu's retreat into the cave,
and Susanoo's slaying of Orochi. "Concept" covers musubi (spiritual power of
growth and harmony), kotodama (spirit of words), and kannagara (way of the
kami).

Ground every node and edge in a source_ref with a passage locator. If a claim
cannot be grounded in the provided text, OMIT it — do not invent mythology
(AGENTS.md §10).
