"""populate_agent_knowledge.py — 把真实 failure events 灌入 5 Agent knowledge."""
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

# Real failure events harvested from recent baseline runs (2026-10-08/09)
real_failures = [
    FailureTrace(
        id=f'rt-{i}',
        error_message=msg,
        error_type=etype,
        context={'source': 'pytest baseline 2026-10-08/09', 'run': 'p5_v7_post_summit'},
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    for i, (msg, etype) in enumerate([
        # pytest baseline pre-existing failures
        ('PlanStep cannot depend on itself ValidationError', 'ValidationError'),
        ('Dependency cannot have from_step_id == to_step_id', 'ValidationError'),
        ('test_link_to_goal_fk_constraint PendingRollbackError teardown', 'OperationalError'),
        ('test_full_artifact_evidence_trace_chain signed_at.tzinfo is None', 'OperationalError'),
        # v2 consumer tests
        ('sqlite3.IntegrityError FOREIGN KEY constraint failed decision_audit', 'IntegrityError'),
        ('PermissionError reading .aios_v2_consumer.lock file', 'PermissionError'),
        # queue.py shadow
        ('ImportError attempted relative import with no known parent package', 'ImportError'),
        # Strategy Gate
        ('strategy_gate_policy_load_failed fail closed', 'OperationalError'),
        # Kernel schema
        ('aiosqlite.core from queue Empty Queue SimpleQueue shadow stdlib', 'ImportError'),
        # ModuleNotFoundError
        ('No module named src.message_queue', 'ModuleNotFoundError'),
        # NUL file
        ('error: short read while indexing NUL NUL: failed to insert into database', 'OSError'),
    ])
]

merger = FailurePatternMerger()
clusters = merger.merge(real_failures)
print(f'clustered {len(real_failures)} failures into {len(clusters)} clusters')
print(f'merge_rate: {merge_rate(len(real_failures), clusters):.2%}')
for c in clusters:
    print(f'  - [{c.root_cause}] {c.error_type} (occurs {c.occurrence_count}x) hash={c.cluster_id[:8]}')

# Save to all 5 agents
service = CrossAgentKnowledgeService()
for agent in AgentName:
    knowledge = service.load(agent)
    for c in clusters:
        knowledge.add_failure_cluster(c)
    # Add 1 capability entry
    knowledge.add_capability(CapabilityIndex(
        skill_id=f'{agent.value}_inbound_failure_handler',
        use_cases=['resolve_phase_G_failure_patterns', f'handle_{agent.value}_workspace'],
        confidence=0.85,
    ))
    p = service.save(knowledge)
    print(f'  saved {agent.value}: {p.name} ({len(knowledge.failure_clusters)} clusters)')