# Helper: writes eval_builder.py
dst = r"D:\AIOS\kernel\src\aios_kernel\learning\eval_builder.py"

lines = []
def L(s): lines.append(s)

L("""eval_builder.py - C004 Eval Dataset Builder.

Builds evaluation datasets for the kernel learning loop.

Design contract (C004 card \\xa7Scope):

  - `EvalCase` is the *unit* of the dataset (Pydantic, inherits Envelope):
        id, query, expected_output, source, difficulty, evidence_id
    `source` is "real" (extracted from a Trace) or "synthetic" (generated).
    `difficulty` is one of: easy, medium, hard.
    `evidence_id` is the originating trace id (for `real`) or a stable
    synthetic-case id like `synth-0007` (for `synthetic`).

  - `EvalDatasetBuilder.from_real(traces, n=100)` extracts up to `n`
    evaluation cases from a sequence of TraceORM (or duck-typed)
    traces. Only *successful* traces are eligible
    (event_type in {"task.complete", "verify.pass"}). The query is
    pulled from `payload["query"]` or `payload["input"]` (first that
    exists, in that order); the expected_output is pulled from
    `payload["output"]` or `payload["result"]`. Traces missing either
    field are skipped. If fewer than `n` traces produce a case, the
    returned list is shorter (callers MUST top-up with `synthetic`).

  - `EvalDatasetBuilder.synthetic(n=100)` programmatically generates
    `n` synthetic cases covering:
        * common-mode queries (greetings, factual lookups, arithmetic)
        * edge cases (unicode, very long input, single char, nested quotes)
        * difficulty spread (~40% easy, ~40% medium, ~20% hard)

  - `EvalDatasetBuilder.merge(real, synth)` merges the two lists and
    deduplicates by the (query, expected_output) pair. Real cases first;
    synth appended only when its fingerprint is unseen. Merge is
    deterministic for a given (real, synth) pair.

  - `EvalDatasetBuilder.format(case)` renders a one-line
    human-readable summary.

Mix invariant (C004 card \\xa7Evidence, \\xa7Forbidden):
    The merged dataset MUST contain >= 50% real cases AND >= 50%
    synthetic cases of the total. `merge()` raises ValueError otherwise
    (the card forbids "eval all-synthetic" at runtime).

In-process, no I/O. Deterministic, no LLM calls.
""")
