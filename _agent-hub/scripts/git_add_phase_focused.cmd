@echo off
REM git_add_phase_focused.cmd — 只 add 我关心的 Phase F + 自助修复文件
cd /d D:\AIOS

git add _agent-hub/scripts/
git add _agent-hub/memory/2026-10-08.md
git add _agent-hub/memory/codex_supervisor_goal.json
git add _agent-hub/reports/aios_vnext_phase_a_done_20261008-122600.md
git add _agent-hub/reports/aios_vnext_phase_b_done_20261008-125500.md
git add _agent-hub/reports/aios_vnext_phase_c_done_20261008-132000.md
git add _agent-hub/reports/aios_vnext_phase_d_done_20261008-134000.md
git add _agent-hub/reports/aios_vnext_phase_e_done_20261008.md
git add _agent-hub/reports/aios_vnext_phase_f_done_20261008.md
git add _agent-hub/reports/aios_vnext_phase_f_acceptance_spec_v0.1_20261008-231300.md
git add _agent-hub/reports/aios_vnext_final_report_20261008.md
git add _agent-hub/reports/aios_vnext_phase0_spec_vs_reality_20261008-112000.md
git add _agent-hub/reports/aios_vnext_phase_a_acceptance_spec_v0.1_20261008-112200.md
git add _agent-hub/reports/aios_vnext_phase_b_acceptance_spec_v0.1_20261008-123000.md
git add _agent-hub/reports/aios_vnext_phase_c_acceptance_spec_v0.1_20261008-130000.md
git add _agent-hub/reports/aios_vnext_phase_d_acceptance_spec_v0.1_20261008-133000.md
git add _agent-hub/reports/aios_vnext_phase_e_acceptance_spec_v0.1_20261008-140000.md
git add _agent-hub/reports/p0_audit_aios_communication_spine_20261008.md
git add _agent-hub/reports/git_push_guide_20261008.md
git add _agent-hub/reports/t0036_phase_a_100task_closed_loop_20261008-035842.md
git add _agent-hub/reports/t0005_r176_r153_ssot_design_20261008-120300.md
git add _agent-hub/v2/src/message_queue.py
git add _agent-hub/v2/src/goal_guard_hook.py
git add _agent-hub/v2/src/v2_consumer.py
git add _agent-hub/v2/tests/test_goal_guard_hook.py
git add _agent-hub/AGENTS.md
git add _agent-hub/AGENTS.md.bak-pre-current-bootstrap-20260930
git add AGENTS.md
git add aios_tasks/aios_vnext/cards/F000_phase_f_acceptance_spec.md
git add aios_tasks/aios_vnext/cards/F001_goal_contract_12_fields.md
git add aios_tasks/aios_vnext/cards/F002_intent_parser.md
git add aios_tasks/aios_vnext/cards/F003_decision_audit_log.md
git add aios_tasks/aios_vnext/cards/F004_failure_pattern_merger.md
git add aios_tasks/aios_vnext/cards/F005_goal_guard_hook.md
git add aios_tasks/aios_vnext/INDEX.md
git add "aios_tasks/aios_vnext/evidence/F000_"*.md
git add "aios_tasks/aios_vnext/evidence/F001_"*.md
git add "aios_tasks/aios_vnext/evidence/F002_"*.md
git add "aios_tasks/aios_vnext/evidence/F003_"*.md
git add "aios_tasks/aios_vnext/evidence/F004_"*.md
git add "aios_tasks/aios_vnext/evidence/F005_"*.md
git add aios_tasks/aios_vnext/preflight_check.py
git add aios_tasks/aios_vnext/_cc_workflow.md
git add aios_tasks/aios_vnext/handoff.md

git add kernel/src/aios_kernel/domain/goal.py
git add kernel/src/aios_kernel/domain/decision.py
git add kernel/src/aios_kernel/domain/services/decision_service.py
git add kernel/src/aios_kernel/domain/services/repository.py
git add kernel/src/aios_kernel/domain/services/__init__.py
git add kernel/src/aios_kernel/persistence/models.py
git add kernel/src/aios_kernel/persistence/repository.py
git add kernel/src/aios_kernel/intent/__init__.py
git add kernel/src/aios_kernel/intent/parser.py
git add kernel/src/aios_kernel/intent/rules.py
git add kernel/src/aios_kernel/intent/classifier.py
git add kernel/src/aios_kernel/intent/llm_adapter.py
git add kernel/src/aios_kernel/governance/__init__.py
git add kernel/src/aios_kernel/governance/goal_guard.py
git add kernel/src/aios_kernel/learning/clustering.py
git add kernel/src/aios_kernel/learning/merger.py
git add kernel/scripts/persistence/migrations/versions/002_decision_audit.py
git add kernel/scripts/persistence/migrations/versions/003_goal_contract_12_fields.py

git add kernel/tests/unit/test_goal_schema.py
git add kernel/tests/unit/test_goal_contract_12_fields.py
git add kernel/tests/unit/test_intent_parser.py
git add kernel/tests/unit/test_decision_audit.py
git add kernel/tests/unit/test_failure_pattern_merger.py
git add kernel/tests/unit/test_goal_guard.py
git add kernel/tests/unit/test_plan_versioning.py
git add kernel/tests/unit/conftest.py
git add kernel/tests/integration/test_failure_merger_integration.py
git add kernel/tests/unit/__init__.py

git status --short | find /v /c ""
echo --- post-add dirty count above ---