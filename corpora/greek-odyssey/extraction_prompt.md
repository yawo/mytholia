# Extraction prompt override for the greek-odyssey corpus.
#
# This is optional: if omitted, pipeline/extract.py uses its built-in default
# prompt. Override only the parts that differ from the generic mythology
# extraction prompt.

You are extracting a knowledge graph from Greek mythology source text,
specifically the Odyssey and related traditions.

Use the abstract node types Character, Place, Object, Event, Concept. Use only
relation labels from this corpus's controlled list: CHILD_OF, SPOUSE_OF, FOUGHT,
MET, TOOK_PLACE_AT, WORSHIPPED_AS, GUARDS, TRANSFORMED_INTO, RULER_OF,
ASSOCIATED_WITH.

Ground every node and edge in a source_ref with a passage locator. If a claim
cannot be grounded in the provided text, OMIT it — do not invent mythology
(AGENTS.md §10).
