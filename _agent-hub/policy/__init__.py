"""policy package — CloudTech Global Product Strategy Policy (Phase-2).

This package contains:
  - product_strategy.v1.json + .schema.json + .sha256   (SSOT)
  - strategy_policy.py        (loader + validator)
  - requirements_lifecycle.py (lifecycle registry)
  - contamination_scanner.py  (structured scanner)
  - strategy_gate.py          (gate evaluator)
  - quarantine.py             (manifest + DO_NOT_INDEX)
  - strategy_index.json       (governance registry index entry)

The SSOT files are loaded via `strategy_policy.load_strategy_policy()`.
The Python modules under this package implement the gate; they are
considered derivative of the SSOT and are updated atomically with
the JSON.
"""