# Compression rules and limitations

The deterministic engine makes no inference calls. It supports four independently
enabled rules: explicit leading ChatGPT greeting removal, approved leading request
wrappers, an explicit redundant introduction, and repeated ASCII spaces. Prefixes
are removed only when the remainder begins with an approved action or another
approved wrapper. Case and task punctuation remain unchanged. Metadata offsets are
relative to the candidate immediately before each transformation; they are not all
offsets into the original string. Exact repeated sentences are reported and never
automatically deleted. Repetition permissions remain future policy work.

All messages except role `user` bypass compression. Messages containing recognized
quotes, backticks, brackets, structured punctuation, newlines, commands, paths,
URLs, numbers, explicit constraints, negations, security instructions, formatting
instructions or transformation tasks bypass as a whole. This sacrifices coverage
and savings to reduce risk. Natural-language classification is heuristic: this
policy cannot recognize every possible implicit constraint or exact-match task.
Do not enable it for workloads requiring guaranteed semantic preservation.

Validation replays approved rules and compares the exact candidate and metadata.
It checks role/order/non-content fields, eligibility, tokenizer reduction and
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
