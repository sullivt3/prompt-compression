# Compression rules and limitations

The deterministic engine makes no inference calls. Eleven independently enabled rules
cover explicit ChatGPT greetings, approved conversational request wrappers, redundant
introductions, indirect requests, test-purpose introductions, and repeated ASCII
spaces. The additional phrase rules shorten leading “provide an explanation of…”
to “Explain…” and “in order to” to “to” inside affirmative instruction sentences.
The purpose-clause rule skips metalinguistic sentences about words, phrases or grammar.
Prefix rules run at message starts and sentence boundaries marked by a
period, question mark or exclamation mark followed by spaces. Prefixes are not
removed from arbitrary positions inside a sentence.

Request wrappers are removed only when followed by an approved action or another
request wrapper. Indirect requests include “I was wondering if you could…”, “Would
you be able to…” and “I would appreciate it if you could…”. Test-purpose wrappers
such as “This is just a test to see how…” and “The purpose of this test is to check
whether…” become “This tests how…” / “This tests whether…”. These transformations
retain the objective rather than deleting whole explanatory sentences. Other uses
of “just”, “test”, or “see” are not blanket-deleted. Spelling is not corrected.

For example, with gpt-4.1-mini tokenization:

> Paste a prompt below. This is just a test to see how many filler words can be removed form the input.

becomes:

> Paste a prompt below. This tests how many filler words can be removed form the input.

The measured text-token counts are 23 → 18 (5 saved, 21.7%). Results depend on the
selected tokenizer and tenant savings thresholds. This does not establish response
quality equivalence.

Task punctuation and text outside matched wrappers remain unchanged. Metadata
offsets refer to the candidate immediately before each transformation; they are not
all offsets into the original string. Validation replays the transformations.
Exact repeated sentences are reported and never automatically deleted. Repetition
permissions remain future policy work.

All messages except role `user` bypass compression. A message is partitioned into
complete fenced blocks, independently delimited prose paragraphs, and unchanged
separators. Rules operate only inside eligible plain-prose paragraphs, never across
boundaries. Fences (backticks or tildes), structured JSON/YAML/XML blocks, quoted
paragraphs, inline-code paragraphs, commands, URLs, numeric values, constraints and
formatting requirements remain byte-for-byte unchanged. This does not attempt
within-sentence rewriting around a quoted string or code span.

Unclosed fences/quotes/code delimiters, malformed standalone JSON/XML, XML entities
or declarations, and explicit exact-text/transformation tasks cause whole-message
bypass. Indented or unclassified multiline paragraphs stay unchanged. Exact-task
markers such as “preserve”, “verbatim”, “rewrite” and “proofread” outside fences
conservatively protect the whole message, including otherwise ordinary instructions.
A heading like “following text” is likewise protected. Balanced fences do not cause
their contents to be interpreted as instructions or transformation-task markers.

Natural-language classification remains heuristic and does not recognize every
implicit constraint or task-material convention. The checks do not establish semantic
equivalence. The system never deletes repeated instructions or negations and never
uses a global stopword-removal pass.

Validation replays approved rules and compares the exact candidate and metadata.
It checks role/order/non-content fields, eligibility, identical protected regions
and separators in the partition, tokenizer reduction and
configurable token/percentage thresholds. This is not proof of semantic equivalence.
The original request is retained on validation failure, unsupported tokenizer,
compression exceptions or nonpositive net savings when prices are configured.
Unknown-tokenizer requests still proxy unchanged and currently record zero token
estimates; consult skip reasons rather than interpreting zero as actual usage.

Policies default to two saved tokens and one percent saved per message, with size
classes below 500, 500–2000, and above 2000 tokens. These are hypotheses. Size classes
only mark future semantic eligibility; they do not trigger model calls. The direct
router accepts `CompressionPolicy`; tenant CLI config controls savings thresholds.
`off` and `algorithmic` work. `semantic` and `hybrid` return 422 in preview. If an
unsupported mode is found in persisted tenant configuration, chat passes through
with an explicit stored skip reason.

Cost estimates use administrator-supplied dated prices per million tokens and
optional local compute cost per second. No live prices are bundled. The cheaper
available input/cached-input price is used conservatively because future cache hits
are unknown. Provider-reported tokens are separate; confirmed billing is unavailable.
Missing price configuration permits eligible local compression but yields no cost
claim. A zero local compute rate means compute cost is unmodeled, not actually free.

Only models mapped by tiktoken to o200k_base or cl100k_base are registered. Other
encodings are explicitly rejected rather than downloaded on the serving path.
A transformation budget bypasses deeply nested request wrappers as a whole.


Try **Prose + code** in the playground for an example. Measured with gpt-4.1-mini,
the example goes from 39 to 28 text tokens (11 saved, 28.2%) with the code block
unchanged. Some eligible rewrites still fail minimum savings and pass through.


Greeting and courtesy handling recognizes message/sentence-leading “Hi”, “Hello”,
“Hey” (optionally addressed to ChatGPT, assistant or “there”), and “Good morning /
afternoon / evening” when followed by an approved instruction. Separate thanks
prefixes and a standalone closing “Thanks” / “Thank you” are eligible. Courtesy
apologies include “Sorry,” and “Sorry to bother you” immediately before an approved
instruction. Closing thanks requires an earlier affirmative instruction in the same
eligible paragraph. A standalone greeting or thanks without a task is preserved;
separate paragraphs containing only courtesies are currently preserved too.

No blanket emotional/affection vocabulary deletion occurs. Explicit tone, dialogue,
emotion, gratitude and apology tasks are excluded from courtesy removal. Context
such as “I am sad”, requested affectionate writing, factual apologies (“Sorry for the
data loss”), and substantive “Thanks for clarifying networking” content stays intact.
Quotes, code, roles and exact-text safeguards continue to apply. Rules are separately
enabled as greeting_removal, gratitude_removal, gratitude_closing and apology_removal.
The router still enforces minimum tokenizer savings; a one-token change may be rejected.
Try **Greetings & thanks** in the playground: its measured gpt-4.1-mini counts are
16 → 4 tokens, without invoking any model.
