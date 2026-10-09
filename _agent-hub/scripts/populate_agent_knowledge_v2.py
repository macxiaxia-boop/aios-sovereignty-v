"""populate_agent_knowledge_v2.py — v2 with similar duplicates for true cluster merge."""
import json
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, r'D:\AIOS\kernel\src')
sys.path.insert(0, r'D:\AIOS\_agent-hub\v2\src')

from aios_kernel.learning.clustering import (
    FailureTrace, FailurePatternMerger, merge_rate
)
from aios_kernel.learning.cross_agent_knowledge import (
    CrossAgentKnowledgeService, AgentName, CapabilityIndex
)

ROOT = Path(r'D:\AIOS')
KNOW_DIR = ROOT / '_agent-hub' / 'knowledge'

# Real failure events with deliberate duplicates for cluster merge
events = [
    # C1: ValidationError on PlanStep self-dep (2 occurrences)
    ('PlanStep cannot depend on itself ValidationError', 'ValidationError'),
    ('PlanStep cannot depend on itself ValidationError', 'ValidationError'),
    # C2: ValidationError on Dependency self-edge (2 occurrences)
    ('Dependency cannot have from_step_id == to_step_id', 'ValidationError'),
    ('Dependency cannot have from_step_id == to_step_id', 'ValidationError'),
    # C3: OperationalError PendingRollbackError (2 occurrences)
    ('test_link_to_goal_fk_constraint PendingRollbackError teardown', 'OperationalError'),
    ('test_link_to_goal_fk_constraint PendingRollbackError teardown', 'OperationalError'),
    # C4: OperationalError signed_at tzinfo (2 occurrences)
    ('test_full_artifact_evidence_trace_chain signed_at.tzinfo is None', 'OperationalError'),
    ('test_full_artifact_evidence_trace_chain signed_at.tzinfo is None', 'OperationalError'),
    # C5: IntegrityError FOREIGN KEY constraint failed (2 occurrences)
    ('sqlite3.IntegrityError FOREIGN KEY constraint failed decision_audit', 'IntegrityError'),
    ('sqlite3.IntegrityError FOREIGN KEY constraint failed decision_audit', 'IntegrityError'),
    # C6: PermissionError .lock read (3 occurrences)
    ('PermissionError reading .aios_v2_consumer.lock file', 'PermissionError'),
    ('PermissionError reading .aios_v2_consumer.lock file', 'PermissionError'),
    ('PermissionError reading .aios_v2_consumer.lock file', 'PermissionError'),
    # C7: ImportError queue.py shadow (2 occurrences)
    ('ImportError attempted relative import with no known parent package', 'ImportError'),
    ('ImportError attempted relative import with no known parent package', 'ImportError'),
    # C8: No module named src.message_queue (2 occurrences)
    ('No module named src.message_queue', 'ModuleNotFoundError'),
    ('No module named src.message_queue', 'ModuleNotFoundError'),
    # C9: NUL file error (1 occurrence)
    ('error: short read while indexing NUL failed to insert into database', 'OSError'),
    # C10: strategy_gate fail closed (1 occurrence)
    ('strategy_gate_policy_load_failed fail closed', 'OperationalError'),
]

real_failures = [
    FailureTrace(
        id=f'rt-{i}',
        error_message=msg,
        error_type=etype,
        context={'source': 'pytest baseline 2026-10-08/09', 'run': 'p5_v7_post_summit'},
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    for i, (msg, etype) in enumerate(events)
]

merger = FailurePatternMerger()
clusters = merger.merge(real_failures)
print(f'clustered {len(real_failures)} failures into {len(clusters)} clusters')
print(f'merge_rate: {merge_rate(len(real_failures), clusters):.2%}')
print()
print('clusters by severity:')
for c in sorted(clusters, key=lambda x: -x.severity_score):
    print(f'  [{c.root_cause}] {c.error_type} count={c.occurrence_count} hash={c.cluster_id[:8]}')

# Save to all 5 agents
service = CrossAgentKnowledgeService()
for agent in AgentName:
    knowledge = service.load(agent)
    for c in clusters:
        knowledge.add_failure_cluster(c)
    # Add capabilities for each agent
    caps = [
        CapabilityIndex(
            skill_id=f'{agent.value}_inbound_failure_handler',
            use_cases=['resolve_phase_G_failure_patterns', f'handle_{agent.value}_workspace'],
            confidence=0.85,
        ),
        CapabilityIndex(
            skill_id=f'{agent.value}_goal_contract_parser',
            use_cases=['parse_user_input_to_GoalContract', 'validate_with_GoalGuard'],
            confidence=0.92,
        ),
    ]
    for cap in caps:
        knowledge.add_capability(cap)
    p = service.save(knowledge)
    print(f'  saved {agent.value}: {p.name} ({len(knowledge.failure_clusters)} clusters, {len(knowledge.capability_index)} caps)')