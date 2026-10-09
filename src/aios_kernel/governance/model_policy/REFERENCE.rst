====================================
AIOS Governance Model Policy
====================================

.. module:: aios_kernel.authority.model_policy

Overview
========

The ``model_policy`` package enforces the AIOS-SOVEREIGNTY-V model governance
contract across 4 adapter surfaces (Codex, Claude Code, OpenClaw, Hermes).
It enforces that only canonical models (currently the MiniMax family) are
permitted, while denylisted models (deepseek, qwen, etc.) are reverted
automatically with fail-closed semantics.

.. contents::
   :local:
   :depth: 2

Quickstart
==========

.. code-block:: python

    from aios_kernel.governance.model_policy import (
        load_policy, sign_yaml, reconcile,
    )
    from pathlib import Path

    # 1. Sign your policy
    sign_yaml(
        Path("etc/sovereignty/model-policy.v1.yaml"),
        Path("etc/sovereignty/codex_supervisor.ed25519.key"),
    )

    # 2. Run the reconciler (any mode)
    policy = load_policy(
        Path("etc/sovereignty/model-policy.v1.yaml"),
        Path("etc/sovereignty/codex_supervisor.ed25519.pub"),
    )
    reports = reconcile(policy, dry_run=False)

    for r in reports:
        print(f"{r.adapter_name}: severity={r.severity} action={r.recommended_action}")

Components
==========

.. autosummary::
    :toctree: generated

    snapshot
    adapter_base
    codex_adapter
    claude_code_adapter
    openclaw_adapter
    hermes_adapter
    reconciler

snapshot module
===============

.. automodule:: aios_kernel.governance.model_policy.snapshot
   :members:
   :undoc-members:
   :show-inheritance:

adapter_base module
===================

.. automodule:: aios_kernel.governance.model_policy.adapter_base
   :members:
   :undoc-members:
   :show-inheritance:

codex_adapter module
====================

.. automodule:: aios_kernel.governance.model_policy.codex_adapter
   :members:
   :undoc-members:
   :show-inheritance:

claude_code_adapter module
===========================

.. automodule:: aios_kernel.governance.model_policy.claude_code_adapter
   :members:
   :undoc-members:
   :show-inheritance:

openclaw_adapter module
=======================

.. automodule:: aios_kernel.governance.model_policy.openclaw_adapter
   :members:
   :undoc-members:
   :show-inheritance:

hermes_adapter module
=====================

.. automodule:: aios_kernel.governance.model_policy.hermes_adapter
   :members:
   :undoc-members:
   :show-inheritance:

reconciler module
=================

.. automodule:: aios_kernel.governance.model_policy.reconciler
   :members:
   :undoc-members:
   :show-inheritance:

Operating Modes
===============

The reconciler supports three operating modes:

* ``scheduled`` (one-shot) — invoked by AIOS_Sovereignty_Reconcile_5min Task Scheduler
* ``onstart`` (one-shot) — invoked by PowerShell profile hook
* ``daemon`` (loop) — invoked by WinSW service aios-sovereignty-reconciler

.. code-block:: bash

    python -m aios_kernel.governance.model_policy.reconciler \\
        --mode daemon \\
        --interval 30 \\
        --json

Severity Escalation
-------------------

DriftReport.severity follows this order:

    ok  <  warn  <  fail_closed

* ``ok`` — no drift detected
* ``warn`` — drift detected but not auto-reverted (settings.json frozen, profile drift, env missing, etc.)
* ``fail_closed`` — drift is auto-reverted (cc-switch common_config_claude, openclaw policy_allowlist, etc.)

Aggregate severity (from ``reconcile.reconcile()``) is the highest of all adapter severities.

Tests
=====

The package ships with 50+ tests:

* ``tests/unit/test_model_policy.py`` (14 unit)
* ``tests/integration/test_model_policy_integration.py`` (4 integration)
* ``tests/integration/test_model_policy_e2e.py`` (4 end-to-end)
* ``tests/integration/test_model_policy_compat.py`` (4 compatibility)
* ``tests/integration/test_model_policy_advanced.py`` (10 edge cases)

Run all sovereignty-v tests:

.. code-block:: bash

    python -m pytest tests/unit/test_model_policy.py tests/integration/test_model_policy_*.py

CI Gate
=======

.. code-block:: bash

    python scripts/ci_verify_sovereignty.py [--strict]

Production Deployment
=====================

+-----------------+--------------------+
| Component        | Status              |
+================+====================+
| Scheduled Task   | Ready (5min cycle)  |
+-----------------+--------------------+
| WinSW daemon     | Running (30s loop)  |
+-----------------+--------------------+
| PowerShell hook  | Active on shell start |
+-----------------+--------------------+
| GitHub repo      | macxiaxia-boop/aios-sovereignty-v |
+-----------------+--------------------+

Schema
------

ModelPolicy v1 YAML schema (see ``model-policy.v1.yaml`` for the canonical
example):

.. code-block:: yaml

    policy_id: mp-YYYY-MM-DD-NNNN-draft
    schema_version: "1.0.0"
    created_at: ISO_DATETIME
    created_by: codex-supervisor
    authorizer: user-YYYY-MM-DDTHH-MM
    status: DRAFT | SIGNED
    signature:
      alg: ed25519
      value: BASE64_SIGNATURE
      public_key_path: PATH_TO_PUB

    allowlist:
      providers:
        - id: PROVIDER_ID
          models:
            - id: MODEL_ID
            - id: MODEL_ID
      denylist:
        - { id: DENIED_MODEL_ID }
      optional:
        - { id: OPTIONAL_MODEL_ID }

    enforcement:
      cc_switch:
        common_config_claude:
          ANTHROPIC_DEFAULT_OPUS_MODEL: "MODEL_ID"
        common_config_codex:
          model_reasoning_effort: "high"
      codex_config_toml:
        profiles_legacy_cleanup: [list]
      openclaw: {}
      hermes:
        cli_config_provider_first: [list]
        cli_config_provider_denylist: [list]

    credential_sync:
      ssot: PATH
      mirrors: [PATHS]
      rotation_protocol: STR

    governance:
      owner: codex-supervisor
      required_signers: [ed25519_KEY_IDS]
      quorum: INT
      mutation_window:
        min_interval_seconds: INT
        max_changes_per_day: INT
      audit:
        log_table: TABLE
        boundary_check: PYTHON_PATH

Versioning
==========

AIOS-SOVEREIGNTY-V uses semantic-style versioning:

* **Major version** (v1, v2): incompatible schema changes
* **Minor version** (.0, .1, .2): new allow/deny items
* **Patch version** (1.0.0 → 1.0.1): corrections only

Current: **v1.0.0** (R2026-10-09)

License
=======

Internal AIOS · proprietary

See also
========

* ``docs/architecture.md`` — overall AIOS architecture
* ``docs/acceptance_criteria.md`` — sovereignty-V acceptance criteria
* ``etc/sovereignty/README.md`` — operational runbook
